"""Single choke point between a model tool call and its execution.

In D0 this is a pass-through that matches the v0 behaviour exactly. Later defenses
register pre-execution hooks here; a hook returns None to allow or a (reason_code,
message) tuple to block.
"""
import json


class Dispatcher:
    def __init__(self, backend, config, hooks=None, arg_filters=None, result_wrapper=None, guard_parse=False):
        self.backend = backend
        self.config = config
        self.hooks = list(hooks or [])
        self.arg_filters = list(arg_filters or [])  # (tool, args) -> args; rewrite arguments before execution
        self.result_wrapper = result_wrapper  # (tool, result) -> text; label tool output before the model sees it
        self.guard_parse = guard_parse  # False (D0): invalid argument JSON raises, exactly as in v0
        self.decisions: list[dict] = []  # defense decisions for the current request
        self.tool_calls: list[dict] = []  # executed or attempted calls for the current request

    @classmethod
    def with_defenses(cls, backend, config, defenses):
        """Dispatcher wired to a Defenses object; plain D0 (defenses is None) gives the v0 pass-through."""
        if defenses is None:
            return cls(backend, config)
        hooks, filters, wrapper, guard = defenses.dispatcher_parts()
        return cls(backend, config, hooks=hooks, arg_filters=filters, result_wrapper=wrapper, guard_parse=guard)

    def reset(self):
        self.decisions, self.tool_calls = [], []

    def dispatch(self, tool_calls):
        results = []
        tool_map = self.backend.tool_map()
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            if self.guard_parse:
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except ValueError:
                    self.tool_calls.append({"tool": tool_name, "arguments": {"_raw": str(tool_call.function.arguments)[:200]}})
                    self.decisions.append({"tool": tool_name, "decision": "block", "reason": "BAD_ARGUMENTS_JSON"})
                    results.append({"role": "tool", "content": json.dumps(
                        "Blocked by policy: invalid arguments. Do not retry this call."), "tool_call_id": tool_call.id})
                    continue
            else:
                arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            self.tool_calls.append({"tool": tool_name, "arguments": arguments})
            blocked = None
            for hook in self.hooks:
                verdict = hook(tool_name, arguments)
                if verdict is not None:
                    blocked = verdict
                    self.decisions.append({"tool": tool_name, "decision": "block", "reason": verdict[0]})
                    break
            if blocked is not None:
                result = blocked[1]
            else:
                for f in self.arg_filters:
                    arguments = f(tool_name, arguments)
                tool = tool_map.get(tool_name)
                result = tool(**arguments) if tool else "Unknown tool: " + tool_name
                if self.result_wrapper:
                    result = self.result_wrapper(tool_name, result)
            results.append({"role": "tool", "content": json.dumps(result), "tool_call_id": tool_call.id})
        return results
