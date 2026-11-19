# syntax=docker/dockerfile:1
FROM composer:2.8 AS vendor
WORKDIR /app
COPY composer.json composer.lock ./
RUN composer install --no-dev --no-scripts --no-interaction --prefer-dist --optimize-autoloader

FROM php:8.4-fpm-alpine AS app
RUN apk upgrade --no-cache && apk add --no-cache postgresql-dev \
 && docker-php-ext-install pdo_pgsql opcache
WORKDIR /var/www/html
COPY --from=vendor /app/vendor ./vendor
COPY . .
RUN rm -f .env \
 && php artisan package:discover --ansi \
 && mkdir -p storage/framework/{cache,sessions,views} storage/logs bootstrap/cache \
 && chown -R www-data:www-data storage bootstrap/cache
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
USER www-data
ENTRYPOINT ["entrypoint.sh"]
CMD ["php-fpm"]

# nginx serves public/ and forwards PHP to the app container
FROM nginx:1.29-alpine AS web
RUN apk upgrade --no-cache
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY public /var/www/html/public
