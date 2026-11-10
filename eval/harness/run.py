"""CLI: python -m eval.harness.run --models stub-gullible --defenses D0 --split dev --k 3 --out eval/results/stub-dev"""
import argparse
import json
import tempfile
from pathlib import Path

from . import cases as C
from . import runner


def fixture_builder(tmp):
    """Fictional persona (eval/fixtures/persona.json) rendered to a CV PDF and summary; canaries included.
    The real CV is never used in experiments."""
    import io

    from reportlab.pdfgen import canvas

    persona = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "persona.json").read_text())
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 800
    for line in persona["cv_lines"]:
        c.setFont("Helvetica", 8)
        c.drawString(40, y, line[:140])
        y -= 14
    c.save()
    pdf = Path(tmp) / "cv.pdf"
    pdf.write_bytes(buf.getvalue())
    txt = Path(tmp) / "summary.txt"
    txt.write_text(persona["summary"], encoding="utf-8")
    return lambda planted: runner.build_system_prompt(planted, pdf, txt)


def make_judge(models_cfg, name):
    """Return (callable, model_id) for a judge model from the registry; None if no judge requested."""
    if not name:
        return None, None
    spec = models_cfg[name]
    client = runner.make_client(spec)

    def judge(prompt):
        r = client.chat.completions.create(model=spec.get("model", name),
                                           messages=[{"role": "user", "content": prompt}])
        return r.choices[0].message.content or ""

    return judge, spec.get("model", name)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--defenses", nargs="+", default=["D0"])
    ap.add_argument("--split", choices=["dev", "test"], default="dev")
    ap.add_argument("--k", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tool-config", type=int, default=0)
    ap.add_argument("--budget-usd", type=float, default=0.0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default="eval/results/run")
    ap.add_argument("--judge", default=None, help="registry name of the judge model (different family)")
    ap.add_argument("--include-drafts", action="store_true", help="also run unreviewed drafted cases")
    ap.add_argument("--workbook", action="store_true", help="re-export cases from the workbook first")
    a = ap.parse_args(argv)
    if a.workbook or not C.CASES_JSONL.exists():
        C.export()
    attack, benign = C.load_jsonl(C.CASES_JSONL), C.load_jsonl(C.BENIGN_JSONL)
    if a.include_drafts:
        da, db = C.load_drafts()
        attack, benign = attack + da, benign + db
    judge, judge_model = make_judge(runner.load_models(), a.judge)
    with tempfile.TemporaryDirectory() as tmp:
        res = runner.run_experiment(attack, benign, a.models, a.defenses, a.k, a.seed, a.out,
                                    a.budget_usd, a.dry_run, a.split, a.tool_config,
                                    system_prompt_builder=fixture_builder(tmp), judge=judge, judge_model=judge_model)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
