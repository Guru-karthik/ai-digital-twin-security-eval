# AI Digital Twin: security evaluation

A tool-using, document-grounded chat agent (the "digital twin") plus a reproducible harness that measures how well
layered defenses (D0 to D3, modules M1 to M3) resist prompt injection, indirect injection and tool misuse.

- `twin/` the agent (Gradio chat, OpenAI-compatible API, two tools, mock or real backend)
- `eval/` cases (`eval/cases`), harness (`eval/harness`), model registry (`eval/models.yaml`), results (`eval/results`)
- `docs/` threat model and protocol, implementation plan, architecture findings, model licence notes
- `tests/` pytest suite including a D0-equivalence test against a frozen copy of the baseline loop

Status: baseline (D0) refactor and evaluation harness done; defenses (D1 to D3), new tools and the adaptive
attacker are planned in `docs/IMPLEMENTATION_PLAN.md`. Results under `eval/results/stub-dev` come from stub models
and are not findings about any real model.

## Run
```
pip install -r requirements-dev.txt openai pypdf requests python-dotenv
python -m pytest -q tests
PYTHONPATH=. python -m eval.harness.run --models stub-gullible stub-refuser --split dev --k 1 --dry-run
```
Live twin: copy your own `summary.txt` and `linkedin.pdf` into `twin/` (they are git-ignored), set `OPENAI_API_KEY`
(and Pushover variables if you want notifications), then `cd twin && python app.py`.

## Ethics
Attacks run only against this repository's own twin, through a mock tool sink, with a fictional persona.
`attacker.example` style hosts are placeholders and are never contacted. No licence has been chosen yet.
