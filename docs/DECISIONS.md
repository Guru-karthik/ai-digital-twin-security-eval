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

## Twin-api is a stub until T1
`infra/twin-stub` returns canned replies and extracts an email into a `record_user_details` tool call so the gateway-to-console path can be exercised. It is not the agent and the README says so. Swap the `twin-api` service in `docker-compose.yml` for the real image when `twin/Dockerfile` exists.

## Conversation rows per turn
The gateway is stateless and the API enforces unique `external_id`, so each turn is stored as `<conversation_id>:<n>` with the transcript so far.
