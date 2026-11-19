#!/bin/sh
# End-to-end smoke test against a running Compose stack (reads secrets from .env). Exits non-zero on the first failure.
set -eu
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
fail() { echo "FAIL: $1" >&2; exit 1; }
code() { curl -s -o /dev/null -w "%{http_code}" "$@"; }

for i in $(seq 1 60); do [ "$(code localhost:8000/login)" = 200 ] && break; sleep 2; done
[ "$(code localhost:8000/login)" = 200 ] || fail "dashboard login page not reachable"
[ "$(code localhost:8080/health)" = 200 ] || fail "gateway health"

[ "$(code -XPOST localhost:8080/chat -H 'content-type: application/json' -d '{"message":"hi"}')" = 401 ] || fail "gateway must reject a missing API key"
[ "$(code localhost:8000/metrics)" = 404 ] || fail "/metrics must not be public"
[ "$(code localhost:8000/api/v1/leads)" = 401 ] || fail "leads API must require auth"
[ "$(code -XPOST localhost:8000/api/v1/leads -H 'content-type: application/json' -d '{"email":"a@example.com"}')" = 401 ] || fail "lead create must require service token"
curl -sI localhost:8000/login | grep -qi "content-security-policy" || fail "CSP header missing"

reply=$(curl -s -XPOST localhost:8080/chat -H "x-api-key: $GATEWAY_API_KEY" -H 'content-type: application/json' \
  -d '{"message":"my email is smoke@example.com","conversation_id":"smoke"}')
echo "$reply" | grep -q '"reply"' || fail "chat reply missing: $reply"

# the lead should reach the console (webhook is async)
for i in $(seq 1 15); do
  n=$(docker compose exec -T postgres psql -U console -d console -tAc "select count(*) from leads where email='smoke@example.com'" | tr -d '[:space:]')
  [ "$n" -ge 1 ] 2>/dev/null && { echo "OK: chat -> gateway -> console lead stored"; exit 0; }
  sleep 1
done
fail "lead did not reach the console"
