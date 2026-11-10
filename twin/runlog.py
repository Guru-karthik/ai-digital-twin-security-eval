"""Structured JSONL logging, one record per request. Secrets are redacted before writing."""
import json
import os
import re
import time
import uuid

_SECRET_ENV = ("OPENAI_API_KEY", "PUSHOVER_TOKEN", "PUSHOVER_USER", "ANTHROPIC_API_KEY")
_PATTERNS = [re.compile(r"sk-[A-Za-z0-9_\-]{16,}")]


def redact(text: str) -> str:
    for name in _SECRET_ENV:
        value = os.getenv(name)
        if value and len(value) >= 6:
            text = text.replace(value, "[REDACTED]")
    for p in _PATTERNS:
        text = p.sub("[REDACTED]", text)
    return text


class RunLogger:
    def __init__(self, path=None, run_id=None, case_id=None, config=None):
        self.path, self.case_id, self.config = path, case_id, config
        self.run_id = run_id or uuid.uuid4().hex[:12]

    def write(self, **record):
        if not self.path:
            return
        record = {"run_id": self.run_id, "case_id": self.case_id, "ts": time.time(),
                  "model": getattr(self.config, "model", None),
                  "config_hash": self.config.config_hash() if self.config else None, **record}
        line = redact(json.dumps(record, default=str, ensure_ascii=False))
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
