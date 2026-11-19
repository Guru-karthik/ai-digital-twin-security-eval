#!/bin/sh
set -e
# Fail closed: the container refuses to start without the secrets the app depends on.
: "${APP_KEY:?APP_KEY is required}"
: "${CONSOLE_SERVICE_TOKEN:?CONSOLE_SERVICE_TOKEN is required}"
if [ "$1" = "php-fpm" ]; then
  php artisan migrate --force
  php artisan config:cache
  php artisan route:cache
  php artisan view:cache
fi
exec "$@"
