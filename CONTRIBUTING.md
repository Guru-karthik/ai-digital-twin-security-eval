# Contributing

- Branch from `main` as `feat/<area>`; open a PR; keep the existing `ci.yml` and the existing tests green.
- Set your own identity before committing: `git config user.name` and `git config user.email`.
- Never commit secrets. `.env` is git-ignored; `./infra/gen-env.sh` creates one. `.dockerignore` files keep `.env`, `eval/manual/persona` and `twin/summary.txt` out of images.
- Checks per area (all runnable in Docker, no local PHP/Node needed):
  - Python: `ruff check twin tests eval` and `python -m pytest -q tests`
  - `console-php/`: `php artisan test` (PHPUnit)
  - `gateway/`: `npm run lint && npm test && npm run build`
  - Whole stack: `./infra/gen-env.sh && docker compose up -d --build && ./infra/smoke.sh`
- API changes start in `docs/openapi.yaml`.
- Dependency versions are pinned; update them deliberately.

## Baseline recorded at the start of the console work
`ruff` clean; `pytest tests`: 74 passed; `gitleaks` over the repository history in this clone (140 commits): no leaks. The 3,000+ commits of the upstream course repository were not part of this clone, so they were not scanned.
