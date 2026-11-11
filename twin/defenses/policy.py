"""Defense policy: every threshold in one place so ablations change data, not code.

Defaults are mirrored in policy.yaml (a test keeps them identical). Override per run with
Config.extra["policy"] = {...}; the override is part of the config hash.
"""
from dataclasses import asdict, dataclass, fields


@dataclass(frozen=True)
class Policy:
    # D2 limits
    max_calls_per_request: int = 3
    max_lead_calls_per_request: int = 1
    max_calls_per_session: int = 8
    max_iterations: int = 5
    max_arg_len: int = 300
    max_input_chars: int = 6000
    history_max_messages: int = 20
    history_max_chars: int = 4000
    # D2 rules (flags for ablation)
    taint: bool = True  # lead email must appear in a visitor message (argument provenance)
    confirm_leads: bool = False  # code-generated confirmation before a lead is recorded (costs utility; ablation)
    sanitise_args: bool = True  # strip links/markup/domains from tool arguments before the notification
    # D1
    wrap_tool_results: bool = True
    # D3
    max_reply_chars: int = 4000
    overlap_words: int = 8  # shared consecutive words with the instruction text that count as a leak
    regenerate_once: bool = True
    allow_hosts: tuple = ("github.com", "linkedin.com")
    safe_reply: str = "I can't share that, but I'm happy to talk about my career, skills and experience."

    @classmethod
    def from_config(cls, config):
        over = dict((getattr(config, "extra", None) or {}).get("policy", {}))
        names = {f.name for f in fields(cls)}
        unknown = set(over) - names
        if unknown:
            raise ValueError(f"unknown policy keys {sorted(unknown)}")
        if "allow_hosts" in over:
            over["allow_hosts"] = tuple(over["allow_hosts"])
        return cls(**over)

    def as_dict(self):
        return asdict(self)
