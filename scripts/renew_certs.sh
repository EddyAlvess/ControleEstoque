#!/usr/bin/env bash
# Renovação manual do certificado Let's Encrypt + reload do nginx.
# Normalmente não é necessário: o container certbot renova automaticamente a cada 12h.
set -euo pipefail

INSTALL_DIR="/opt/inventcontrol"
cd "$INSTALL_DIR"

source .env 2>/dev/null || true

DC="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

echo "[INFO] Renovando certificado para ${DOMAIN:-?}..."
$DC exec certbot certbot renew \
    --webroot -w /var/www/certbot \
    --non-interactive

echo "[INFO] Recarregando nginx..."
$DC exec nginx nginx -s reload

echo "[INFO] Pronto. Certificado válido até:"
$DC exec certbot certbot certificates 2>/dev/null | grep "Expiry Date" | head -1
