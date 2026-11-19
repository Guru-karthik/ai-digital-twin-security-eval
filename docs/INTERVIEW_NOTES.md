# Interview notes: Guru (PHP, Node, DevOps parts)

Every claim below maps to code in this repo. Say "stub" or "not applied" where that is the truth.

## Q&A
**Why Laravel?** Conventions and built-ins (Sanctum, validation, rate limiting, CSRF, migrations) let a PHP newcomer ship a secure API quickly. See `docs/DECISIONS.md`.

**How is the API authenticated?** Two separate credentials. Humans: Sanctum tokens or a session, with roles `admin` and `viewer`. Machines: one static service token that can only call the write endpoints. Both compared in constant time; the service endpoints refuse if the token is unset (fail closed).

**What stops a viewer approving a lead?** A `role:admin` middleware returns 403, and tests cover both the API and the dashboard. Approvals write an `admin_action` audit event.

**How did you handle XSS and CSRF?** Blade `{{ }}` escaping everywhere, no raw output, a test that injects `<script>` into every field shown. Strict CSP with no inline script or style. CSRF tokens on every dashboard POST, with a test that a tokenless POST gets 419.

**Why a gateway in Node?** It is the only public surface: API-key check before validation, strict schema (unknown fields rejected), rate limit, upstream timeout, and no visitor messages in logs.

**Is the chat streaming?** No. The agent returns a finished reply; the gateway replays it as SSE chunks. I documented that instead of calling it streaming.

**What happens if the console is down?** Chat still works. Reporting to the console is best effort and logged; I tested it.

**How do you keep metrics private?** Separate internal ports (gateway 9100, nginx 8081), not published by Compose; public nginx returns 404 for `/metrics`; the API also needs a bearer token. Labels never contain user input.

**What did the security scan find?** Trivy flagged outdated Alpine packages in the nginx image and a vulnerable dependency bundled inside npm in the Node image. I upgraded the base and removed npm from the runtime images; scans are clean now (point in time).

**A bug you found by running it?** The container crashed because Laravel's cached package manifest from my dev install listed a dev-only provider that the production image lacked. Fixed with `.dockerignore` plus `package:discover` in the build. Another: Fastify strips unknown fields by default, which contradicted the contract; a test caught it.

**What is not done?** Real twin-api (stub), MongoDB (skipped), Terraform apply, TLS.

## CV (4 lines)
- Built a Laravel 13 admin API and dashboard (Sanctum auth, admin/viewer roles, audited approvals, CSRF/XSS/CSP protections) with 43 automated tests.
- Built a Fastify/TypeScript chat gateway with API-key auth, strict validation, rate limiting and SSE replay (27 tests).
- Containerised the stack with Docker Compose (Postgres, nginx, php-fpm, Prometheus, Grafana) with an end-to-end smoke test and Trivy-clean images.
- Wrote GitHub Actions workflows and a validated Terraform module for AWS (not applied).

## LinkedIn (3 lines)
Built an admin console around an AI chat agent: Laravel API and dashboard, Node gateway, Docker Compose, Prometheus and Grafana.
Focused on secure defaults: role-based access, audited admin actions, CSRF/XSS protection, private metrics, image scanning.
Open to backend and DevOps roles.
