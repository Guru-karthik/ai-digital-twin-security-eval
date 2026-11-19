#!/bin/sh
# Writes .env with fresh random secrets. Refuses to overwrite an existing .env.
set -e
cd "$(dirname "$0")/.."
[ -e .env ] && { echo ".env already exists; delete it first to regenerate." >&2; exit 1; }
r() { openssl rand -hex 24; }
umask 077
cat > .env <<ENV
APP_KEY=base64:$(openssl rand -base64 32)
DB_PASSWORD=$(r)
CONSOLE_SERVICE_TOKEN=$(r)
CONSOLE_METRICS_TOKEN=$(r)
GATEWAY_API_KEY=$(r)
GRAFANA_ADMIN_PASSWORD=$(r)
# Leave empty to have the seeder generate and print random passwords:
SEED_ADMIN_PASSWORD=
SEED_VIEWER_PASSWORD=
# Set to true when serving over HTTPS:
SESSION_SECURE_COOKIE=false
ENV
echo "Wrote .env (mode 600). Do not commit it."
