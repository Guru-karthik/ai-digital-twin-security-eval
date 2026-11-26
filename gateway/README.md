# gateway

Fastify (TypeScript) service in front of the twin. Public chat surface for the admin console stack. Contract: `../docs/openapi.yaml`.

- `POST /chat` needs header `X-API-Key`. Validates the body (unknown fields are rejected), rate limits, proxies to `twin-api`, and returns JSON or, with `Accept: text/event-stream`, SSE.
- **Not real streaming.** The agent returns a finished reply; the gateway replays it as `delta` events then `done`.
- `GET /health`.
- After each reply it reports to the Laravel API (best effort, never fails the chat): the transcript, leads from `record_user_details` tool calls, tool-call and decision audit events. Skipped when `CONSOLE_API_URL`/`CONSOLE_SERVICE_TOKEN` are unset.
- Each turn stores its own conversation row (`external_id` = `<conversation_id>:<message count>`) because the gateway is stateless and the API enforces unique external ids.
- Logs never contain visitor messages; `x-api-key` and `authorization` are redacted.

## Contract with `twin/server.py`
`POST {TWIN_API_URL}/chat` takes `{message, history}` and returns `{reply, tool_calls, decisions, defense, model}`. `tool_calls` lists only calls that were *executed*; a call blocked by a defense appears in `decisions` instead, so a blocked injection attempt never becomes a lead. History roles are `user`/`assistant` only.

## Config (env)
`GATEWAY_API_KEY` (required, 16+ chars; the process will not start without it), `TWIN_API_URL`, `CONSOLE_API_URL`, `CONSOLE_SERVICE_TOKEN`, `PORT` (8080), `RATE_LIMIT_MAX` (30), `RATE_LIMIT_WINDOW` ("1 minute"), `UPSTREAM_TIMEOUT_MS` (60000).

## Develop
`npm ci && npm run lint && npm test && npm run build`
