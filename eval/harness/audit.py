"""Human-audit helper: export a reproducible sample of judged runs, then compute kappa against human labels.

  PYTHONPATH=. python -m eval.harness.audit export eval/results/<exp> [fraction]   -> <exp>/audit_sample.csv
  (fill the `human_label` column with 1 = attack succeeded, 0 = not, then)
  PYTHONPATH=. python -m eval.harness.audit kappa eval/results/<exp>
Replies are read from the per-request log (requests.jsonl), so the sample shows the full reply, not an excerpt.
"""
import csv
import json
import sys
from pathlib import Path

from .scorers import audit_sample, cohens_kappa


def _judged(exp):
    runs = [json.loads(line) for line in open(exp / "runs.jsonl", encoding="utf-8") if line.strip()]
    return [r for r in runs if str(r.get("reason", "")).startswith("judge:")]


def export(exp, fraction=0.2, seed=0):
    exp = Path(exp)
    judged = {(r["run_id"]): r for r in _judged(exp)}
    replies = {}
    for line in open(exp / "requests.jsonl", encoding="utf-8"):
        rec = json.loads(line)
        replies[rec["run_id"]] = rec.get("reply")
    keys = audit_sample(judged, fraction, seed)
    with open(exp / "audit_sample.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["run_id", "case_id", "judge_success", "reply", "human_label"])
        for k in keys:
            r = judged[k]
            w.writerow([k, r["case_id"], int(bool(r["success"])), replies.get(k), ""])
    return len(keys)


def kappa(exp):
    rows = list(csv.DictReader(open(Path(exp) / "audit_sample.csv", encoding="utf-8")))
    rows = [r for r in rows if r["human_label"] in ("0", "1")]
    return cohens_kappa([int(r["judge_success"]) for r in rows], [int(r["human_label"]) for r in rows]), len(rows)


if __name__ == "__main__":
    if sys.argv[1] == "export":
        print(export(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 0.2), "items")
    else:
        print(kappa(sys.argv[2]))
