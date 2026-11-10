"""Statistics: Wilson intervals, paired tests grouped by parent case, Holm correction, tables, plot."""
import collections
import math
import random


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, centre - half), min(1.0, centre + half)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact p for discordant counts b (A success, B fail) and c (A fail, B success)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def holm(pvals: dict) -> dict:
    """Holm-Bonferroni adjusted p-values."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, running = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


def per_case_rate(rows, key=lambda r: r["case_id"]):
    """Mean success per case over runs (only scoreable rows)."""
    acc = collections.defaultdict(list)
    for r in rows:
        if r["success"] is not None:
            acc[key(r)].append(1.0 if r["success"] else 0.0)
    return {k: sum(v) / len(v) for k, v in acc.items()}


def parent_of(r):
    return r.get("parent") or r["case_id"]


def paired_bootstrap(rows_a, rows_b, n_boot=2000, seed=0, group=parent_of):
    """Paired bootstrap over parent cases (children of one parent are not independent evidence).
    Returns (mean ASR difference A-B, 95% CI low, high, n_groups)."""
    ga, gb = collections.defaultdict(list), collections.defaultdict(list)
    for r in rows_a:
        if r["success"] is not None:
            ga[group(r)].append(float(r["success"]))
    for r in rows_b:
        if r["success"] is not None:
            gb[group(r)].append(float(r["success"]))
    common = sorted(set(ga) & set(gb))
    if not common:
        return (float("nan"),) * 3 + (0,)
    diffs = [sum(ga[g]) / len(ga[g]) - sum(gb[g]) / len(gb[g]) for g in common]
    rng = random.Random(seed)
    boots = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(n_boot))
    return sum(diffs) / len(diffs), boots[int(0.025 * n_boot)], boots[int(0.975 * n_boot) - 1], len(common)


def mcnemar_by_case(rows_a, rows_b, threshold=0.5):
    """Case-level McNemar: a case 'succeeds' if its success rate over runs exceeds `threshold`."""
    ra, rb = per_case_rate(rows_a), per_case_rate(rows_b)
    b = c = 0
    for k in set(ra) & set(rb):
        sa, sb = ra[k] > threshold, rb[k] > threshold
        b += sa and not sb
        c += sb and not sa
    return mcnemar_exact(b, c), b, c


def asr_table(rows, by=("class", "model", "defense")):
    """ASR with Wilson CI per group. Unscoreable runs are counted but excluded from the rate."""
    groups = collections.defaultdict(lambda: [0, 0, 0])
    for r in rows:
        if r.get("case_type", "attack") != "attack":
            continue
        g = groups[tuple(r.get(k) for k in by)]
        if r["success"] is None:
            g[2] += 1
        else:
            g[1] += 1
            g[0] += bool(r["success"])
    out = []
    for key, (k, n, unscored) in sorted(groups.items(), key=lambda kv: [str(x) for x in kv[0]]):
        p, lo, hi = wilson(k, n)
        out.append({**dict(zip(by, key)), "successes": k, "n": n, "unscored": unscored,
                    "asr": p, "ci_low": lo, "ci_high": hi})
    return out


def utility_table(rows):
    """Benign utility proxy: correct = not refused and no error; refusal rate from the `refused` flag."""
    g = collections.defaultdict(lambda: [0, 0, 0, 0])
    for r in rows:
        if r.get("case_type") != "benign":
            continue
        a = g[(r["model"], r["defense"])]
        a[0] += 1
        a[1] += bool(r.get("refused"))
        if r.get("correct") is not None:
            a[2] += 1
            a[3] += bool(r["correct"])
    return [{"model": m, "defense": d, "benign_runs": n, "refusals": k, "refusal_rate": k / n,
             "checked": c, "correct": ok, "utility": (ok / c if c else float("nan"))}
            for (m, d), (n, k, c, ok) in sorted(g.items())]


def overhead(rows, baseline="D0"):
    """Median and p95 latency and mean tokens per request, relative to the baseline defense."""
    import statistics

    by = collections.defaultdict(list)
    for r in rows:
        by[r["defense"]].append(r)

    def summ(rs):
        lat = sorted(x["latency_s"] for x in rs)
        tok = [x["tokens_in"] + x["tokens_out"] for x in rs]
        return {"median_latency": statistics.median(lat), "p95_latency": lat[max(0, math.ceil(0.95 * len(lat)) - 1)],
                "mean_tokens": sum(tok) / len(tok), "cost_usd": sum(x["cost_usd"] for x in rs)}

    base = summ(by[baseline]) if by.get(baseline) else None
    return {d: {**summ(rs), "tokens_vs_base": (summ(rs)["mean_tokens"] / base["mean_tokens"] if base else None)}
            for d, rs in sorted(by.items())}


def tradeoff_plot(points, path):
    """points: [(label, asr, utility)]. Matplotlib is imported lazily so the harness runs without it."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5, 4))
    for label, asr, util in points:
        ax.scatter(asr, util)
        ax.annotate(label, (asr, util))
    ax.set_xlabel("attack success rate")
    ax.set_ylabel("benign utility")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
