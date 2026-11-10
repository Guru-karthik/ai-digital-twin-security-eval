# Implementation plan: AI Digital Twin security evaluation and tool extensions

(On approval this is copied verbatim to `docs/IMPLEMENTATION_PLAN.md` as the first commit of `phase-0-recon`. No code is changed before approval.)

## Context
Build a reproducible study of how layered defenses (D0-D3, modules M1-M3) protect a tool-using, document-grounded agent, then extend the twin with new tools and measure how attack surface grows (RQ5). Spec = the threat-model doc; seed data = the attack-case workbook. Output: harness, defenses, tools, `docs/REPORT.md`, CI.

## Pre-flight findings (read-only, done)
**Attached files: both present, but not at the paths you named.**
- Spec: `1_foundations/twin/docs/Threat Model and Evaluation Protocol AI Digital Twin.md` (414 lines, read in full) -> target `docs/threat-model.md`.
- Workbook: `1_foundations/twin/Eval/cases/digital_twin_attack_cases_v2.xlsx` -> target `eval/cases/digital_twin_attack_cases.xlsx`. Not opened yet (`openpyxl` is not installed in `.venv`); contents get diffed in Phase 2.
- I treat these as "not missing". Tell me if you disagree.

**Repo state.** The twin is at `1_foundations/twin/`, not `twin/`. Working tree is dirty: my earlier cleanup (hundreds of staged deletions), modified notebooks, untracked `ThanushreeSridhara_updated_CV.pdf` at the root and new `docs/`+`Eval/` under twin. `.env` is gitignored (I will not read it). No `render.yaml` in the repo; the Render service must point at some path I cannot see.

**Baseline code (all 5 small files read): `app.py`, `context.py`, `tools.py`, `styles.py`, `requirements.txt`.** Early answers to the VERIFY list (to be confirmed with tests, not just reading, in Phase 0):
- Tool loop: `while finish_reason == "tool_calls"` with **no iteration cap** (T12 exposure).
- History: Gradio `history` is concatenated as-is; no truncation, no length cap, trusts client-supplied roles/format.
- Argument validation: none. `json.loads` + `tool(**arguments)`; bad args raise TypeError and crash the request; no try/except; unknown tool returns a string.
- Storage: **no lead store exists**. `record_user_details` only calls Pushover (the spec says "stores lead"; I will correct this in the findings). Logging = `print("Tool called: name")` only.
- Pushover payload: raw f-string with attacker-controlled name/email/notes/question, no length cap, no sanitising. Credentials read at import; if unset, `requests.post` still fires with `None`.
- Rate limiting: none in code (Render unknown). Streaming: none (`return content`). Vector store: none.
- Prompt: `linkedin.pdf` read with a cwd-relative path at import (app must start from `twin/`); `summary.txt` is injected raw. Model hardcoded `gpt-5.4-mini`, no temperature set, deps unpinned.
- Still to test empirically: whether Gradio renders markdown images/links/raw HTML (T13), and what pypdf returns for white/tiny/metadata text (generated PDF via reportlab).

**Spec issues to settle (not blocking):**
- Tool configs are named T0-T3 and collide with threat IDs T1-T19. Proposal: call them TC0-TC3 in code/workbook, keep the doc's wording in the report.
- Spec section 11 says the workbook already has AC-023..AC-049, BN-009..016, Tools sheet, RQ5 table, while your brief says to add AC-023..027. Phase 2 diffs the workbook first and adds only what is missing, keeping IDs stable.
- Typo "Tineteen" (19 threats listed); the "2026" OWASP/ATLAS/EU-AI-Act facts in the spec are flagged unverified by the spec itself; I will carry that label into the report and not assert them.
- "Eval/" vs `eval/` casing; layout in the spec is `twin/ eval/{cases,harness,results} docs/`.

## Decisions I need from you (before Phase 0 starts)
1. **Layout:** move `1_foundations/twin` -> `twin/` (spec layout; matches your brief) and `Eval` -> `eval`? Risk: the Render service root/start command may need updating. Alternative: keep `1_foundations/twin` and put `eval/`, `docs/` at the root.
2. **Working-tree hygiene:** commit the earlier cleanup + notebooks on a `chore/cleanup` branch first (so `v0-baseline` is a clean tag), or leave them out? I recommend committing it separately and not touching the notebooks.
3. **Models (three, one local):** which hosted pair and which Ollama model? Judge must be a different family from the answer model. Does `gpt-5.4-mini` accept a temperature of 0.7? If not, "fixed temperature" needs a per-model policy; D0 keeps today's default.
4. **Budget:** a hard USD cap for real runs (the spec's worst case is about 30,000 requests / 39M tokens). Real-model runs stay blocked until you approve the dry-run estimate.
5. **Dependencies over 200 MB:** M1 (torch + transformers + classifier weights), Presidio/spaCy if M2, Ollama images. I will ask again before adding any of these; the plan assumes M1 runs in the harness only first.
6. **Scanner:** `gitleaks` is a Go binary, not installed. OK to use `detect-secrets` via `uv` (and/or a pinned gitleaks release downloaded in CI)? Notebooks need `nbstripout`-style output scanning too.
7. **Phase-0 disclosure line:** wording and where it goes (title description vs. banner). It changes UI so `v0-baseline` includes it; the D0 behavioural test covers tool calls, not UI.

## Phase 0 - reconnaissance and hygiene (branch `phase-0-recon`, tag `v0-baseline`)
- Create `docs/`, `eval/cases/`, copy/move the two attachments, commit this plan.
- `docs/ARCHITECTURE_FINDINGS.md`: every VERIFY item above with evidence. Throwaway experiment scripts under `eval/scratch/` (not shipped): generated PDF with plain/white/tiny/metadata text through `pypdf`; Gradio render check using the installed Gradio version (read its sanitiser/markdown config plus a headless render of `![x](https://example.invalid/?d=1)`, `[a](...)`, `<img>`; no real hosts contacted).
- Secret scan (report only, no history rewrite, output redacted: file/rule/line only, never the match) over repo history + notebooks.
- Add the AI-assistant disclosure line to the chat UI (`app.py` description).
- Tests: none required except a trivial import test; tag `v0-baseline`.
- Report back: findings, how to re-run, unverified items.

## Phase 1 - make it testable (`phase-1-testability`)
Files (all new unless noted): `twin/config.py` (env + YAML, flags D0-D3, M1-M3, model/provider, temperature, test mode, config hash), `twin/dispatcher.py` (single choke point; D2 hooks, no behaviour in D0), `twin/backends.py` (`ToolBackend` interface; `RealBackend` = Pushover; `MockBackend` records tool/args/session/turn/timestamp and returns configurable results incl. attacker strings for E5), `twin/logging_.py` (JSONL: run id, case id, model, config hash, messages, tool calls, defense decisions + reason codes, tokens, latency; secrets redacted), edits to `app.py`/`tools.py` to route through these, `twin/agent.py` (loop extracted so the harness can drive it without Gradio), `docker-compose.test.yml` + `Dockerfile.test` + mock-sink service (internal network, non-root, read-only FS, CPU/mem limits, no real creds).
- **D0-unchanged proof:** `tests/test_d0_equivalence.py` replays fixed benign conversations against a scripted stub model through (a) a frozen copy of the baseline loop taken from tag `v0-baseline` and (b) the refactored path; asserts identical tool-call sequences and arguments.
- pytest + ruff config, pinned requirements, GitHub Actions workflow (tests + stub-model smoke subset, no keys).

## Phase 2 - evaluation harness (`phase-2-harness`)
`eval/harness/`: `cases.py` (xlsx -> JSONL/CSV export, loader; fields incl. source, split dev/test, parent, mutator), `runner.py` (cases x models x defenses x k, seeded ordering, resume via run-log keys, budget guard, `--dry-run` request/token estimate), `scorers/` (canary, regex/fuzzy, mock-sink rules, URL-exfil parser, counts, LLM judge with fixed rubric and cross-family guard, audit sampler + Cohen's kappa), `stats.py` (Wilson, McNemar/paired bootstrap grouped by parent case, Holm correction, overhead, plot), `mutators.py` and `poison.py` (placement x visibility x phrasing x goal; reportlab for PDFs), `results_to_workbook.py`.
- Workbook sync as described in the diff step above; expand cases to the section-7 sizes (60-100/class prioritised, 60+20 benign) with source tags. Writing 150-250 cases is large; I will draft in batches and ask you to review a sample (self-written attacks are a recorded validity threat).
- Every scorer and mutator gets pytest tests. First run: D0 on the dev split with the stub model only. Real models only after you approve the dry-run estimate.

## Phase 3 - defenses (`phase-3-defenses`, tag `v1-defenses`)
`twin/defenses/`: `d1_prompt.py`; `d2_policy.py` + `policy.yaml` (schema validation, length caps, per-session limits, argument provenance, code-generated confirmation state machine, notification sanitiser; taint rule is a separate flag for the section-11.3 ablation); `d3_output.py` (canary/prompt overlap, secret scan, URL/markdown filter, moderation, grounding judge, regenerate-once -> safe reply; buffered replies, no streaming exists so this is straightforward); `m1_detector.py` (optional, ablation on D2; classifier behind an interface so CI uses a stub). Each rule has a reason code and a unit test; false-block rate on the benign set measured after each level. M2/M3 not built unless asked.

## Phase 4 - new tools (`phase-4-tools`, from `v1-defenses`; v0/v1 results untouched)
Order A -> B -> C. Each tool: schema, mock backend + fixtures, policy entry, attack + benign cases, workbook rows, tests, then a re-run of prioritised classes per batch.
- A: `get_github_projects`/`get_repo_details` (enum from owner's own repo list, README untrusted, TTL cache, optional fine-grained read-only token from env, tests against a local mock API); `get_linkedin_profile` (reads `data/linkedin_export.json`, no network, `data/` gitignored with a fake fixture committed); `get_availability` (version 1 = scheduling link; free/busy later after checking current Google scopes, and that connector needs authorisation I do not have in this session); `search_projects` (local FAISS/Chroma, built offline; needs your size approval).
- B: `match_job_posting` (pasted text, cited evidence).
- C (off by default): `request_meeting`, `fetch_job_posting_url` (SSRF guard: private/link-local/loopback/metadata IPs blocked after DNS resolution, no cross-host redirects, size/time caps, text only; tested against local fixtures only).
- Report ASR vs tool count and tier (TC0-TC3), on all applicable cases and on the shared TC0 set.

## Phase 5 - adaptive attacker and report (`phase-5-report`)
LLM attacker, 20-turn budget, against D0, D1, D2, D2+M1; static and adaptive ASR reported separately. `docs/REPORT.md` (2-4 pages), README section, dataset card, `make reproduce-table` from raw logs in `eval/results/`.

## Cross-cutting rules (from your brief)
- Secrets: never printed, logged or committed; `.env` not read; fake secrets only in tests/fixtures; scanner output redacted.
- No real Pushover or third-party calls in tests/experiments; attacks run only against this repo's twin through the mock sink.
- No invented numbers: every figure traces to a run log with model name/version string, temperature, date, config hash; unverified items labelled.
- One branch per phase, small commits, tags `v0-baseline` / `v1-defenses`. I commit only on the phase branches, never to `main`, and never push.
- After each phase: what changed, how to run, what I could not verify, decisions for you.

## Risks
- Render deploy path changes if the twin is moved (decision 1).
- Hosted-model nondeterminism and silent version drift; mitigation: record version strings, rerun baseline at the end.
- Cost: mutators multiply request count; dry-run gate + cap.
- Mutated and poisoned variants are not independent evidence; statistics group by parent case.
- Judge bias / small self-written case set; mitigation: cross-family judge, 20% human audit with kappa, source tagging, dev/test split.
- gpt-5-family parameter restrictions (temperature) may make "fixed temperature" impossible for some models.
- M1 weights/torch size and licences (e.g. Llama Prompt Guard licence terms) need your sign-off.

## Verification of this plan's deliverables
Phase 0: findings file with evidence per item, scan report, tag exists, UI shows disclosure (manual run + screenshot-free check of the rendered string). Phase 1: `pytest` incl. D0-equivalence passes; CI green with no keys; `docker compose -f docker-compose.test.yml up` shows zero egress except the allowed route. Phase 2+: `python -m eval.harness.run --dry-run` prints estimate; stub-model D0 dev run produces JSONL; `make reproduce-table` regenerates a table byte-identically from `eval/results/`.
