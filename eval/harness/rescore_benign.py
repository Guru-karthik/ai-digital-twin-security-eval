"""Rescore benign runs from the full request log without calling any model.

Raw `runs.jsonl` is never modified. Output: `<exp>/benign_rescored.jsonl` with the current scorer's verdict next to
the original one. Only single-turn benign cases are rescored (the request log holds one record per request).
Usage: python -m eval.harness.rescore_benign eval/results/d0-dev-qwen3-8b
"""
import json
import sys
from pathlib import Path

from . import cases as C
from . import scorers


def rescore(exp_dir):
    exp = Path(exp_dir)
    cases = {c["case_id"]: c for c in C.load_jsonl(C.BENIGN_JSONL)}
    reqs = {}
    for line in open(exp / "requests.jsonl", encoding="utf-8"):
        q = json.loads(line)
        reqs.setdefault(q["run_id"], []).append(q)
    out = []
    for line in open(exp / "runs.jsonl", encoding="utf-8"):
        r = json.loads(line)
        case = cases.get(r["case_id"])
        if r["case_type"] != "benign" or case is None or len(case["turns"]) != 1 or r["run_id"] not in reqs:
            continue
        q = reqs[r["run_id"]][-1]
        calls = []
        for rq in reqs[r["run_id"]]:
            tc = rq.get("tool_calls")
            tc = json.loads(tc) if isinstance(tc, str) else tc
            for t in tc or []:
                calls.append({"tool": t.get("name") or t.get("tool"), "arguments": t.get("arguments") or {}})
        run = {"reply": q["reply"], "calls": calls}
        ok, why = scorers.score_benign(case, run)
        if ok != r["correct"]:
            out.append({"key": r["key"], "case_id": r["case_id"], "old": r["correct"], "new": ok, "reason": why})
    with open(exp / "benign_rescored.jsonl", "w", encoding="utf-8") as f:
        for o in out:
            f.write(json.dumps(o) + "\n")
    return out


if __name__ == "__main__":
    for d in sys.argv[1:]:
        res = rescore(d)
        print(d, "changed verdicts:", len(res), {x["case_id"] for x in res})
