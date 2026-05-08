#!/bin/sh
# Em produção: substitui $DOMAIN no template e gera default.conf.
# Em dev (overlay monta default.conf como read-only): pula envsubst e usa o arquivo montado.
set -e
DOMAIN="${DOMAIN:-localhost}"
CONF="/etc/nginx/conf.d/default.conf"
if [ -w "$CONF" ] || [ ! -f "$CONF" ]; then
    envsubst '${DOMAIN}' < /etc/nginx/nginx.conf.template > "$CONF"
fi
exec nginx -g 'daemon off;'
