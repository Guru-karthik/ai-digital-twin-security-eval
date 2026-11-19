"""Aggregate harness run records into one summary per (result folder, model, defense).

Definitions (attack trials only; one record is one trial, so k repeats count separately):
- total_cases:   scored attack trials (records with case_type "attack", no error, and a success value)
- passed_cases:  trials where the attack did NOT succeed (the defense held)
- attack_success_rate: successes / total_cases
- failed_checks: cases where at least one trial succeeded, "<case_id> (<successes>/<trials>)", worst first, capped
Latency and cost are averaged/summed over every record in the group (attack and benign).
Benign over-refusal is not part of this summary; it needs its own field in the API contract.
"""
import json
from collections import defaultdict
from pathlib import Path

MAX_FAILED_CHECKS = 50


def read_runs(path: Path):
    """Yield records from a runs.jsonl file, skipping blank and malformed lines."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except ValueError:
                continue


def summarise(run_key: str, records) -> list[dict]:
    groups = defaultdict(list)
    for r in records:
        if r.get("model") and r.get("defense"):
            groups[(r["model"], r["defense"])].append(r)

    out = []
    for (model, defense), rows in sorted(groups.items()):
        trials = [r for r in rows if r.get("case_type") == "attack" and r.get("error") is None
                  and isinstance(r.get("success"), bool)]
        if not trials:
            continue  # benign-only group: nothing to say about attack success
        wins = sum(1 for r in trials if r["success"])
        per_case: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for r in trials:
            c = per_case[str(r.get("case_id"))]
            c[1] += 1
            c[0] += 1 if r["success"] else 0
        failed = sorted(((cid, w, n) for cid, (w, n) in per_case.items() if w), key=lambda t: (-t[1], t[0]))
        lat = [r["latency_s"] for r in rows if isinstance(r.get("latency_s"), (int, float))]
        out.append({
            "run_key": run_key,
            "defense": str(defense)[:32],
            "model": str(model)[:100],
            "total_cases": len(trials),
            "passed_cases": len(trials) - wins,
            "attack_success_rate": round(wins / len(trials), 6),
            "mean_latency_s": round(sum(lat) / len(lat), 4) if lat else None,
            "cost_usd": round(sum(r.get("cost_usd") or 0 for r in rows), 6),
            "failed_checks": [f"{cid} ({w}/{n})" for cid, w, n in failed[:MAX_FAILED_CHECKS]],
        })
    return out


def load_results(results_dir: Path) -> list[dict]:
    """One summary list entry per (folder, model, defense) across every folder that has a runs.jsonl."""
    runs = []
    for runs_file in sorted(Path(results_dir).glob("*/runs.jsonl")):
        runs.extend(summarise(runs_file.parent.name, read_runs(runs_file)))
    return runs
