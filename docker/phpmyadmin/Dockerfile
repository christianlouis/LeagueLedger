# Keep phpMyAdmin 5.2.3 while rebuilding its PHP runtime with fixed PHP 8.3.36.
FROM phpmyadmin/phpmyadmin:5.2.3@sha256:42a200db07b4e70fbf32c594ad4521cf16399b8e54bbb5adceae98e7566dfbeb AS phpmyadmin
FROM php:8.3.36-apache@sha256:d89e8b3d2033c3179dcd9999d913670eb12a07410a95e60205c64e7d0fac7aef

ARG BUILD_JOBS=4
ENV PMA_SSL_DIR=/etc/phpmyadmin/ssl SESSION_SAVE_PATH=/sessions

RUN set -eux; apt-get update; apt-get install -y --no-install-recommends libbz2-dev libfreetype6-dev libjpeg-dev libpng-dev libwebp-dev libxpm-dev libzip-dev libsqlite3-dev; \
    docker-php-ext-configure gd --with-freetype --with-jpeg --with-webp --with-xpm; docker-php-ext-install -j"${BUILD_JOBS}" bz2 gd mysqli opcache zip bcmath; \
    rm -rf /var/lib/apt/lists/*; a2enmod remoteip; mkdir -p "$SESSION_SAVE_PATH" "$PMA_SSL_DIR"; chmod 1777 "$SESSION_SAVE_PATH"; chmod 755 "$PMA_SSL_DIR"

COPY --from=phpmyadmin /var/www/html /var/www/html
COPY --from=phpmyadmin /etc/phpmyadmin /etc/phpmyadmin
COPY --from=phpmyadmin /docker-entrypoint.sh /docker-entrypoint.sh
COPY --from=phpmyadmin /usr/local/lib/php/extensions/no-debug-non-zts-20230831/uploadprogress.so /usr/local/lib/php/extensions/no-debug-non-zts-20230831/uploadprogress.so
COPY --from=phpmyadmin /usr/local/etc/php/conf.d/docker-php-ext-uploadprogress.ini /usr/local/etc/php/conf.d/docker-php-ext-uploadprogress.ini
RUN chown -R www-data:www-data /etc/phpmyadmin /var/www/html/tmp; chmod 1777 /var/www/html/tmp
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["apache2-foreground"]
