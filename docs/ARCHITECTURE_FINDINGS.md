# Architecture findings (Phase 0)

Scope: `twin/` at the commit tagged `v0-baseline`. Method: reading `app.py`, `context.py`, `tools.py`, `styles.py`, `requirements.txt`, plus the experiments in `eval/scratch/`. Status per item: **Verified** (read in code or reproduced), **Unverified** (needs something I could not run).

| Item (VERIFY in the protocol) | Finding | Status |
| --- | --- | --- |
| Tool-loop iteration cap | None. `while finish_reason == "tool_calls"` in `app.py` repeats until the model stops asking. T12 exposure. | Verified (code) |
| History handling | Gradio `history` is concatenated into the messages unchanged. No truncation, no length cap, no role or format check. | Verified (code) |
| Argument validation | None. `json.loads` then `tool(**arguments)`. Malformed JSON or unexpected keys raise and the request fails. No try/except. An unknown tool name returns a string to the model. | Verified (code) |
| Where leads are stored | Nowhere. `record_user_details` only sends a Pushover push. The protocol says it "stores" a lead; that is wrong for this code. | Verified (code) |
| Where logs are stored | Only `print("Tool called: <name>")` to stdout. No arguments, no messages, no file. | Verified (code) |
| Pushover payload | Raw f-string with visitor-controlled name, email, notes or question. No length cap, no sanitising. Credentials are read from the environment at import; if unset, the POST is still sent with `None` values. | Verified (code) |
| Rate limiting | None in code. Hosting (Render) rules are unknown. | Unverified (hosting) |
| Streaming | No. `chat()` returns the full string. Buffering for D3 needs no change. | Verified (code) |
| Vector store | None. CV text and `summary.txt` go straight into the system prompt. | Verified (code) |
| Markdown, links, raw HTML in Gradio | Gradio 6.24.0 `Chatbot` defaults: `render_markdown=True`, `sanitize_html=True`, `allow_tags=True`. Rendering happens in the browser. Standard markdown images and links are expected to render; the sanitiser removes scripts and handlers but not `<img src="https://...">`. I could not run a browser here, so image requests are **not** observed. T13 stays an open exposure until tested in a browser. | Partly verified (defaults); behaviour Unverified |
| PDF extractor and hidden text | `eval/scratch/pdf_hidden_text.py` with pypdf 6.10.2: plain, white-on-white, 1 pt and off-page text are **all** returned by `extract_text()`. Document metadata is not returned by the `context.py` path. Hidden text therefore reaches the model. | Verified (generated fake PDF) |

## Other observations
- `context.py` reads `linkedin.pdf` and `summary.txt` with cwd-relative paths at import, so the app must start from `twin/`.
- Model is hardcoded as `gpt-5.4-mini`; no temperature is set; `requirements.txt` is unpinned.
- `twin/linkedin.pdf` is now the owner's updated CV (previously the course author's profile). It is **not committed**; see the decisions list in the phase report.
- The protocol says the baseline stores leads and uses 2 tools; the tools are `record_user_details` and `record_unknown_question`.

## Secret scan
- Tool: `detect-secrets` (run ad hoc via `uv`, not added as a dependency). Scope: working tree of `twin/`, `docs/`, `eval/`, `1_foundations/` (including the notebooks), `README.md`, `pyproject.toml`. Result: **0 findings**. Output was reduced to file, line and type; no matched strings were printed.
- **Not done:** git history. `detect-secrets` does not scan history and `gitleaks` is not installed. A history scan needs your approval to download a pinned gitleaks release. `.env` was not read.

## Reproduce
```
uv run --no-project --with reportlab --with pypdf python -I eval/scratch/pdf_hidden_text.py
uv run --no-project --with detect-secrets python -I -m detect_secrets scan --all-files --exclude-files '(\.venv|\.git|uv\.lock)' twin docs eval 1_foundations
```
