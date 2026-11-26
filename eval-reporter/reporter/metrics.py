"""Prometheus text exposition built from the aggregated runs (no client library needed)."""


def _esc(v) -> str:
    return str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def render(runs: list[dict]) -> str:
    families = [
        ("eval_attack_success_rate", "Share of attack trials that succeeded", "attack_success_rate"),
        ("eval_attack_trials", "Scored attack trials", "total_cases"),
        ("eval_attack_trials_blocked", "Attack trials the defense held against", "passed_cases"),
        ("eval_mean_latency_seconds", "Mean request latency", "mean_latency_s"),
        ("eval_cost_usd", "Total cost of the runs", "cost_usd"),
    ]
    lines = []
    for name, help_, field in families:
        lines += [f"# HELP {name} {help_}", f"# TYPE {name} gauge"]
        for r in runs:
            if r.get(field) is None:
                continue
            labels = f'run_key="{_esc(r["run_key"])}",model="{_esc(r["model"])}",defense="{_esc(r["defense"])}"'
            lines.append(f"{name}{{{labels}}} {r[field]}")
    return "\n".join(lines) + "\n"
