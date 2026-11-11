"""Defense layers D1-D3 and module M1, assembled from a Config.

`Defenses.from_config(config)` returns None for plain D0 with no modules, so the baseline code path is untouched.
Hooks into the existing code: `prompt()` (build time), `begin_request`/`check_input`/`clean_history` (before the model),
`dispatcher_parts()` (tool execution) and `check_output`/`regenerate_note` (after the model).
"""
from .d1_prompt import harden_prompt, wrap_tool_result
from .d2_policy import PolicyGate, parse_args_or_block
from .d3_output import LEAK_NOTE, OutputGuard
from .m1_detector import HeuristicDetector
from .policy import Policy


class Defenses:
    def __init__(self, config, canaries=(), grounding_fn=None, detector=None):
        self.config = config
        self.policy = Policy.from_config(config)
        self.d1, self.d2, self.d3 = (config.enabled(x) for x in ("D1", "D2", "D3"))
        self.m1 = config.enabled("M1")
        self.detector = detector or HeuristicDetector()
        self.gate = PolicyGate(self.policy) if self.d2 else None
        self.guard = OutputGuard(self.policy, canaries, grounding_fn) if self.d3 else None
        self.build_events: list[dict] = []  # decisions made when the prompt was built (M1 on documents)
        self.events: list[dict] = []  # per-request decisions made outside the dispatcher

    @classmethod
    def from_config(cls, config, **kw):
        if config.level() == 0 and not config.modules:
            return None
        return cls(config, **kw)

    # ---- build time ---------------------------------------------------------------------------------
    def prompt(self, system_prompt: str) -> str:
        if self.m1:
            system_prompt = self._m1_documents(system_prompt)
        return harden_prompt(system_prompt) if self.d1 else system_prompt

    def _m1_documents(self, prompt):
        """Redact suspected injected instructions in the person's summary and profile text only."""
        a, b = prompt.find("Here are the details of the person"), prompt.find("# Rules")
        if a == -1 or b == -1 or b < a:
            return prompt
        doc, n = self.detector.redact(prompt[a:b])
        if n:
            self.build_events.append({"decision": "modify", "reason": "M1_DOCUMENT_REDACTED", "count": n})
        return prompt[:a] + doc + prompt[b:]

    # ---- request lifecycle ---------------------------------------------------------------------------
    def begin_request(self, message, history):
        self.events = []
        if self.gate:
            self.gate.begin_request(message, history)

    def check_input(self, message):
        if self.gate:
            ok, reason = self.gate.check_input(message)
            if not ok:
                self.events.append({"decision": "block", "reason": reason})
                return False, self.policy.safe_reply
        return True, None

    def clean_history(self, history):
        return self.gate.clean_history(history) if self.gate else history

    @property
    def max_iterations(self):
        return self.policy.max_iterations if self.d2 else None

    def dispatcher_parts(self):
        """(hooks, arg_filters, result_wrapper, guard_parse) for the Dispatcher."""
        hooks = [self.gate.hook] if self.gate else []
        filters = [self.gate.filter_args] if self.gate else []
        wrapper = None
        if self.d1 and self.policy.wrap_tool_results or self.m1:
            def wrapper(tool, result):  # noqa: E306
                text = str(result)
                if self.m1:
                    text, n = self.detector.redact(text)
                    if n:
                        self.events.append({"tool": tool, "decision": "modify", "reason": "M1_TOOL_RESULT_REDACTED"})
                return wrap_tool_result(tool, text) if self.d1 and self.policy.wrap_tool_results else text
        return hooks, filters, wrapper, bool(self.d2)

    def drain_events(self):
        return list(self.build_events) + list(self.events) + (list(self.gate.log) if self.gate else [])

    # ---- reply ---------------------------------------------------------------------------------------
    def check_output(self, reply, base_prompt):
        if not self.guard:
            return reply, [], False
        return self.guard.check(reply, base_prompt)

    def final_block(self, reason):
        return self.guard.final_block(reason)

    regenerate_note = LEAK_NOTE


__all__ = ["Defenses", "Policy", "HeuristicDetector", "parse_args_or_block"]
