# Decisions

Short records of why the console is built the way it is. Newest last.

## Laravel for the admin API and dashboard
Conventions, Eloquent, Sanctum, validation, migrations, rate limiting and CSRF are built in, which suits a first PHP project. Symfony would also work but needs more assembly. Laravel pieces used: Sanctum (API tokens), form validation in controllers, `RateLimiter` named limiters, Blade (auto-escaped output), PHPUnit feature tests.

## Fastify for the gateway
Built-in JSON-schema validation (used with `removeAdditional: false` so unknown fields are rejected, matching the OpenAPI contract), a maintained rate-limit plugin, and TypeScript support. The gateway is stateless; it authenticates, validates, rate limits, proxies and reports to the console.

## Two kinds of credentials, kept apart
Humans get Sanctum tokens or a session (roles `admin`, `viewer`). Machines (gateway, eval-reporter) use one static service token that only unlocks the write endpoints (`POST` leads, conversations, evaluation runs, audit events). A service token cannot read data, and a user token cannot write as a service. Both are compared in constant time, and the API refuses service calls if the token is unset.

## Honest scope of "approval"
The agent has no human-approval step. The audit log records decisions that exist (policy gate, output guard, tool calls) plus admin approve/reject actions taken in the console. The console action is a new feature and is labelled as such.

## Metrics are never on a public listener
Gateway metrics are on port 9100 and the API's on nginx port 8081. Neither is published by Compose; public nginx returns 404 for `/metrics`; the API also requires a bearer token and returns 404 when none is configured. Metric labels use route patterns and status codes, never user input.

## Postgres only; MongoDB skipped
The plan marks MongoDB conversation logs optional. Conversations are stored as JSON in Postgres, one database fewer to run and secure.

## Twin-api: stub by default, real agent behind a profile
`infra/twin-stub` returns canned replies so CI and a fresh clone need no LLM; it is not the agent and the README says so. The real agent is `twin/server.py` (`--profile agent`).

## `tool_calls` means executed calls only
`dispatcher.tool_calls` also lists calls that a defense blocked. If the gateway stored those as leads, a blocked injection attempt (for example D2's `EMAIL_PROVENANCE`) would still reach the console. `server.py` wraps the backend per request and reports only calls that reached it; blocked attempts appear in `decisions`. A test covers this. Existing agent code is unchanged.

## One request at a time in the agent API
`Defenses` keeps per-request state on a shared object, so `server.py` serialises `run_chat` with a lock instead of changing the defense code. Throughput is limited by that; fine for a demo, not for load.

## Idempotent evaluation-run upsert
The reporter re-posts results, so `POST /evaluation-runs` upserts on `(run_key, model, defense)`. The migration de-duplicates existing rows first (found by running it against data the previous version had created).

## Reporter depends on nothing
`eval-reporter` uses only the standard library, so its image has no third-party packages to patch.

## Conversation rows per turn
The gateway is stateless and the API enforces unique `external_id`, so each turn is stored as `<conversation_id>:<n>` with the transcript so far.
