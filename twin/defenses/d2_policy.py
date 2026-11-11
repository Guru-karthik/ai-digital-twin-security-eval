"""D2: policy gate between the model's tool call and its execution, plus input and history limits.

Rules are plain code with reason codes; none depends on the model's cooperation.
"""
import json
import re

from tools import tools as TOOL_SCHEMAS

from .policy import Policy
from .text import collapse_controls, strip_links

EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
AFFIRM_RE = re.compile(r"\b(yes|yep|confirm(ed)?|correct|that'?s right|that is right|ok(ay)?)\b", re.I)
BLOCK_NOTE = " Do not retry this call. Tell the visitor briefly that you could not do it."


def _schemas():
    return {t["function"]["name"]: t["function"]["parameters"] for t in TOOL_SCHEMAS}


class PolicyGate:
    """Stateful per Defenses instance. `visitor_texts` is the list of visitor messages of the current request
    (history plus current). Session state (call totals, pending confirmations) lives as long as the instance."""

    def __init__(self, policy: Policy):
        self.p = policy
        self.schemas = _schemas()
        self.visitor_texts: list[str] = []
        self.request_calls = 0
        self.request_lead_calls = 0
        self.session_calls = 0
        self.pending_email: str | None = None
        self.confirmed: set[str] = set()
        self.log: list[dict] = []  # sanitisation events for the current request

    # ---- request lifecycle -------------------------------------------------------------------------
    def begin_request(self, message: str, history: list):
        self.visitor_texts = [m["content"] for m in history
                              if m.get("role") == "user" and isinstance(m.get("content"), str)] + [message]
        self.request_calls = self.request_lead_calls = 0
        self.log = []
        if self.pending_email and AFFIRM_RE.search(message):
            self.confirmed.add(self.pending_email)
            self.pending_email = None

    def check_input(self, message: str):
        if len(message) > self.p.max_input_chars:
            return False, "INPUT_TOO_LONG"
        return True, None

    def clean_history(self, history: list) -> list:
        """Keep only user/assistant turns with string content, the last N messages, each capped in length."""
        kept = [{"role": m["role"], "content": m["content"][: self.p.history_max_chars]}
                for m in history if isinstance(m, dict) and m.get("role") in ("user", "assistant")
                and isinstance(m.get("content"), str)]
        return kept[-self.p.history_max_messages:]

    # ---- pre-execution hook (blocks) ---------------------------------------------------------------
    def hook(self, tool, args):
        if tool not in self.schemas:
            return ("UNKNOWN_TOOL", f"Blocked by policy: unknown tool.{BLOCK_NOTE}")
        schema = self.schemas[tool]
        props = schema["properties"]
        if not isinstance(args, dict):
            return ("BAD_ARGUMENTS", f"Blocked by policy: arguments must be an object.{BLOCK_NOTE}")
        extra = set(args) - set(props)
        missing = [r for r in schema.get("required", []) if r not in args]
        if extra or missing:
            return ("SCHEMA", f"Blocked by policy: arguments do not match the tool schema.{BLOCK_NOTE}")
        for k, v in args.items():
            if not isinstance(v, str):
                return ("SCHEMA", f"Blocked by policy: argument {k} must be text.{BLOCK_NOTE}")
            if len(v) > self.p.max_arg_len:
                return ("ARG_TOO_LONG", f"Blocked by policy: argument {k} is too long.{BLOCK_NOTE}")
        if self.request_calls >= self.p.max_calls_per_request or self.session_calls >= self.p.max_calls_per_session:
            return ("RATE_LIMIT", f"Blocked by policy: too many tool calls.{BLOCK_NOTE}")
        if tool == "record_user_details":
            email = args["email"].strip()
            if not EMAIL_RE.match(email):
                return ("EMAIL_FORMAT", "Blocked by policy: that is not a valid email address. "
                                        "Ask the visitor for a valid address.")
            if self.request_lead_calls >= self.p.max_lead_calls_per_request:
                return ("RATE_LIMIT", f"Blocked by policy: one contact per request.{BLOCK_NOTE}")
            if self.p.taint and email.lower() not in " ".join(self.visitor_texts).lower():
                return ("EMAIL_PROVENANCE", "Blocked by policy: that address was not given by the visitor.")
            if self.p.confirm_leads and email.lower() not in self.confirmed:
                self.pending_email = email.lower()
                return ("CONFIRM_REQUIRED", f"Blocked by policy: ask the visitor to confirm {email} "
                                            "by replying yes before it is recorded.")
            self.request_lead_calls += 1
        self.request_calls += 1
        self.session_calls += 1
        return None

    # ---- argument rewriting (sanitiser) ------------------------------------------------------------
    def filter_args(self, tool, args):
        if not self.p.sanitise_args:
            return args
        out, changed = {}, False
        for k, v in args.items():
            if k == "email":
                out[k] = v.strip()
                continue
            clean, n = strip_links(collapse_controls(v), self.p.allow_hosts)
            if clean != v:
                changed = True
            out[k] = clean
        if changed:
            self.log.append({"tool": tool, "decision": "modify", "reason": "ARGS_SANITISED"})
        return out


def parse_args_or_block(raw):
    """JSON-decode tool arguments; (None, reason) if the model produced invalid JSON."""
    try:
        return json.loads(raw), None
    except ValueError:
        return None, "BAD_ARGUMENTS_JSON"
