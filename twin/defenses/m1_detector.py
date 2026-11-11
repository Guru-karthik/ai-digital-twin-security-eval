"""M1: injection detector for untrusted text (documents, tool results).

This is a transparent HEURISTIC detector with generic, literature-style patterns. It is NOT the trained classifier
named in the plan (that needs torch and model weights, which need approval as a >200 MB dependency). Patterns were
written before looking at held-out test results, but dev cases were visible when choosing which generic families to
include, so only the test split can support a claim about M1. The interface (`score`) lets a classifier replace it.
"""
import re

PATTERNS = [
    r"ignore (all |any )?(the )?(previous|prior|above|earlier) (instructions|rules|messages)",
    r"disregard (all |any )?(the )?(previous|prior|above|earlier|your) (instructions|rules)",
    r"(new|updated|additional) (system )?instructions?\b.{0,40}\b(from|by) the (administrator|developer|owner|system)",
    r"\bsystem (notice|message|override|prompt)\b",
    r"\[ ?system ?\]",
    r"\bnote to (the )?(ai |llm )?assistant",
    r"\bassistant (instruction|directive|note)s?\b",
    r"\b(if|when) you are an (ai|llm|assistant|language model)\b",
    r"\bassistants?\b.{0,60}\b(must|should|shall|are required to|need to)\b",
    r"\byou (must|should|are required to) (now )?(call|invoke|use) (the )?[\w -]{0,40}tool",
    r"\b(reveal|print|show|output|paste) (your |the )?(complete |full |hidden )?(system )?(prompt|instructions)",
    r"\b(now |also |then |please )*(call|invoke|run|use) (the |a )?[\w -]{0,40}\btool\b",
    r"\bretry (this|the) (call|request|operation)\b",
    r"\btell the (visitor|user) (that|to)\b",
    r"from now on you are\b",
    r"\bnew (role|persona)\b.{0,30}\byou\b",
    r"(end|begin|start|sign|append|finish) (every|each|all|your|the) (reply|answer|response|message|sentence)",
]
_RES = [re.compile(p, re.I | re.S) for p in PATTERNS]


class HeuristicDetector:
    name = "m1-heuristic"

    def score(self, text: str):
        """Return (flagged, matched_pattern_index or None)."""
        for i, r in enumerate(_RES):
            if r.search(text or ""):
                return True, i
        return False, None

    def redact(self, text: str, marker="[removed: suspected injected instruction]"):
        """Replace each line (or sentence if the line is long) that triggers the detector. Returns (text, n)."""
        n = 0
        out = []
        for line in (text or "").split("\n"):
            parts = re.split(r"(?<=[.!?])\s+", line) if len(line) > 160 else [line]
            keep = []
            for part in parts:
                if self.score(part)[0]:
                    n += 1
                    keep.append(marker)
                else:
                    keep.append(part)
            out.append(" ".join(keep))
        return "\n".join(out), n
