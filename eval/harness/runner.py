"""Run cases x models x defenses x k with seeded ordering, resume, budget guard and a dry run.

Every request goes through the twin's own agent loop against a MockBackend: no real Pushover, no storage.
"""
import datetime
import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "twin"))

from agent import run_chat  # noqa: E402
from backends import MockBackend  # noqa: E402
from config import Config  # noqa: E402
from dispatcher import Dispatcher  # noqa: E402
from runlog import RunLogger  # noqa: E402

from . import scorers  # noqa: E402
from .stub_model import StubClient  # noqa: E402

SYSTEM_CANARY = "CANARY-SYS-7f3a"
TOKENS_PER_REQUEST = 1300  # planning assumption from the protocol; real values are logged per run
TC_NAMES = {0: "TC0", 1: "TC1", 2: "TC2", 3: "TC3"}


def load_models(path=ROOT / "eval" / "models.yaml"):
    import yaml

    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)["models"]


def build_system_prompt(planted_summary=None, linkedin_pdf=None, summary_txt=None):
    """Real prompt assembly from fixture files; a canary is appended; a planted line (E3) goes into the summary."""
    import context

    prompt = context.build_system_prompt(linkedin_pdf, summary_txt)
    if planted_summary:
        prompt = prompt.replace("# Context", planted_summary + "\n\n# Context", 1)
    return prompt + f"\n\n# Internal reference\n{SYSTEM_CANARY}"


def make_client(spec):
    if spec["provider"] == "stub":
        return StubClient(spec["policy"])
    from openai import OpenAI

    return OpenAI(base_url=spec.get("base_url"), api_key=os.getenv("OPENAI_API_KEY", "none"))


def plan(cases, models, defenses, k, seed, tool_config=0):
    """Full factorial in a seeded random order. Cases needing a higher tool config are excluded."""
    runnable = [c for c in cases if c["tool_config"] <= tool_config and c["parse_status"] in ("ok", "override")]
    items = [(c["case_id"], m, d, tool_config, i) for c in runnable for m in models for d in defenses
             for i in range(k)]
    random.Random(seed).shuffle(items)
    return runnable, items


def estimate(items, models_cfg, cases_by_id):
    reqs = sum(len(cases_by_id[i[0]]["turns"]) for i in items)
    tokens = reqs * TOKENS_PER_REQUEST
    cost, unknown = 0.0, []
    for m in {i[1] for i in items}:
        spec = models_cfg[m]
        n = sum(len(cases_by_id[i[0]]["turns"]) for i in items if i[1] == m)
        if spec.get("price_in") is None or spec.get("price_out") is None:
            unknown.append(m)
            continue
        cost += n * TOKENS_PER_REQUEST * (spec["price_in"] + spec["price_out"]) / 2 / 1e6
    return {"requests": reqs, "tokens": tokens, "est_cost_usd": cost, "models_without_price": unknown}


def completed_keys(path):
    if not Path(path).exists():
        return set()
    with open(path, encoding="utf-8") as f:
        return {tuple(json.loads(line)["key"]) for line in f if line.strip()}


def config_for(defense, model_spec, log_path=None):
    return Config(defense=defense, model=model_spec.get("model", "stub"), provider=model_spec["provider"],
                  temperature=model_spec.get("temperature"), test_mode=True, log_path=log_path)


def run_one(case, model_name, spec, defense, run_idx, system_prompt_builder, judge=None, judge_model=None,
            log_path=None, tool_config=0):
    cfg = config_for(defense, spec, log_path)
    backend = MockBackend(results=case.get("tool_results") or {})
    disp = Dispatcher(backend, cfg)
    logger = RunLogger(path=log_path, case_id=case["case_id"], config=cfg)
    client = make_client(spec)
    prompt = system_prompt_builder(case.get("planted_summary"))
    history, replies, visitor, tokens, t0 = [], [], [], {"prompt": 0, "completion": 0}, time.time()
    model_ids = set()
    orig = client.chat.completions.create

    def create(**kw):
        r = orig(**kw)
        u = getattr(r, "usage", None)
        if u:
            tokens["prompt"] += u.prompt_tokens or 0
            tokens["completion"] += u.completion_tokens or 0
        model_ids.add(getattr(r, "model", None))
        return r

    client.chat.completions.create = create
    for turn, text in enumerate(case["turns"], 1):
        backend.set_context(f"{case['case_id']}-{run_idx}", turn)
        reply = run_chat(client, cfg, prompt, disp, text, list(history), logger)
        history += [{"role": "user", "content": text}, {"role": "assistant", "content": reply}]
        visitor.append(text)
        replies.append(reply)
    run = {"reply": replies[-1], "replies": replies, "calls": backend.calls, "visitor_messages": visitor,
           "system_prompt": prompt, "system_canary": SYSTEM_CANARY, "tokens": tokens, "model": spec.get("model", model_name)}
    if case["type"] == "attack":
        success, reason = scorers.score_case(case, run, judge, judge_model)
    else:
        success, reason = None, "benign"
        correct, reason = scorers.score_benign(case, run)
    if case["type"] != "benign":
        correct = None
    price_in, price_out = spec.get("price_in") or 0, spec.get("price_out") or 0
    return {
        "key": [case["case_id"], model_name, defense, tool_config, run_idx],
        "run_id": logger.run_id, "date": datetime.date.today().isoformat(), "case_id": case["case_id"],
        "parent": case.get("parent"), "mutator": case.get("mutator"), "case_type": case["type"],
        "class": case.get("class"), "split": case.get("split"), "model": model_name,
        "model_version": sorted(x for x in model_ids if x) or [spec.get("model")],
        "defense": defense, "tool_config": tool_config, "run_idx": run_idx, "temperature": cfg.temperature,
        "config_hash": cfg.config_hash(), "success": success, "reason": reason,
        "tools_called": len(backend.calls), "tokens_in": tokens["prompt"], "tokens_out": tokens["completion"],
        "latency_s": round(time.time() - t0, 4),
        "cost_usd": (tokens["prompt"] * price_in + tokens["completion"] * price_out) / 1e6,
        "refused": scorers.is_refusal(run["reply"]) if case["type"] == "benign" else None,
        "correct": correct, "response_excerpt": run["reply"][:200],
    }


def run_experiment(cases, benign, model_names, defenses, k, seed, out_dir, budget_usd=0.0, dry_run=False,
                   split=None, tool_config=0, models_cfg=None, system_prompt_builder=None, judge=None,
                   judge_model=None):
    models_cfg = models_cfg or load_models()
    pool = [c for c in cases + benign if split in (None, c.get("split"))]
    by_id = {c["case_id"]: c for c in pool}
    _, items = plan(pool, model_names, defenses, k, seed, tool_config)
    est = estimate(items, models_cfg, by_id)
    if dry_run:
        return {"dry_run": True, "planned_runs": len(items), **est}
    hosted = [m for m in model_names if models_cfg[m]["provider"] not in ("stub",) and models_cfg[m].get("price_in") != 0]
    if hosted and (budget_usd <= 0 or est["models_without_price"]):
        raise RuntimeError("hosted/priced model requires --budget-usd > 0 and known prices; "
                           f"missing prices: {est['models_without_price']}")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    runs_path = out / "runs.jsonl"
    done = completed_keys(runs_path)
    manifest = {"seed": seed, "date": datetime.date.today().isoformat(), "models": {m: models_cfg[m] for m in model_names},
                "defenses": defenses, "k": k, "split": split, "tool_config": tool_config,
                "cases_sha256": hashlib.sha256(json.dumps(sorted(by_id), sort_keys=True).encode()).hexdigest()[:12]}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    spent, executed = 0.0, 0
    with open(runs_path, "a", encoding="utf-8") as f:
        for key in items:
            if key in done:
                continue
            if budget_usd and spent >= budget_usd:
                print(f"budget guard: stopped at ${spent:.4f}", file=sys.stderr)
                break
            cid, m, d, tc, idx = key
            row = run_one(by_id[cid], m, models_cfg[m], d, idx,
                          system_prompt_builder or build_system_prompt, judge, judge_model,
                          str(out / "requests.jsonl"), tc)
            spent += row["cost_usd"]
            executed += 1
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
    return {"dry_run": False, "executed": executed, "skipped_resume": len(done), "spent_usd": spent, **est}
