"""Results tooling: python -m eval.harness.report eval/results/<exp> -> tables as markdown + CSV, from raw logs only."""
import csv
import json
import sys
from pathlib import Path

from . import stats


def load_runs(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def md(rows, cols):
    head = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    def fmt(v):
        return f"{v:.3f}" if isinstance(v, float) else str(v)

    return head + "\n".join("| " + " | ".join(fmt(r.get(c)) for c in cols) + " |" for r in rows) + "\n"


def build(exp_dir):
    exp = Path(exp_dir)
    runs = load_runs(exp / "runs.jsonl")
    manifest = json.loads((exp / "manifest.json").read_text())
    t = stats.asr_table(runs)
    cols = ["class", "model", "defense", "successes", "n", "unscored", "asr", "ci_low", "ci_high"]
    text = f"# ASR per class, model and defense\n\nSource: {exp}/runs.jsonl ({len(runs)} runs, seed {manifest['seed']}, " \
           f"date {manifest['date']}, models {list(manifest['models'])}).\n\n" + md(t, cols)
    (exp / "table_asr.md").write_text(text)
    with open(exp / "table_asr.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(t)
    return text


if __name__ == "__main__":
    print(build(sys.argv[1]))
