# eval/

Harness for the Digital Twin security study (spec: `docs/threat-model.md`).

```
PYTHONPATH=. python -m eval.harness.cases                      # workbook -> eval/cases/*.jsonl + csv
PYTHONPATH=. python -m eval.harness.run --models stub-gullible stub-refuser --split dev --k 3 --dry-run
PYTHONPATH=. python -m eval.harness.run --models stub-gullible stub-refuser --split dev --k 3 --out eval/results/stub-dev
PYTHONPATH=. python -m eval.harness.report eval/results/stub-dev   # table from raw logs only
```

- `eval/results/stub-dev/` was produced by **stub models** (`eval/harness/stub_model.py`). It checks that the
  pipeline works. It says nothing about any real model and must not be quoted as a finding.
- Real models (`eval/models.yaml`) are blocked until a budget is given with `--budget-usd` and prices are filled in.
- Only cases with `tool_config <= --tool-config` run (default TC0: the two baseline tools). Cases that need
  Phase 4 tools are exported but skipped.
- Experiments use a fake CV with canaries and a mock tool backend; the real CV and real Pushover are never used.
