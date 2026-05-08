#!/usr/bin/env bash
# Migração de HTTP provisório → HTTPS com Let's Encrypt.
# Execute quando o registro DNS do domínio já estiver propagado para o IP do servidor.
#
# Uso: bash setup_https.sh
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERRO]${NC} $*"; exit 1; }

INSTALL_DIR="/opt/inventcontrol"
cd "$INSTALL_DIR"

# ─── Ler configuração atual ───────────────────────────────────────────────────
source .env 2>/dev/null || true
CURRENT_DOMAIN="${DOMAIN:-}"

echo ""
echo "======================================"
echo "  InventControl — Ativar HTTPS"
echo "======================================"
echo ""
[[ -n "$CURRENT_DOMAIN" ]] && echo "  Domínio atual no .env: $CURRENT_DOMAIN"
echo ""

read -rp "Domínio (ex: estoque.suaempresa.com): " NEW_DOMAIN
[[ -z "$NEW_DOMAIN" ]] && error "Domínio não pode ser vazio."

# Não aceitar IP
if echo "$NEW_DOMAIN" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'; then
    error "Let's Encrypt não emite certificados para IPs. Use um domínio DNS."
fi

read -rp "E-mail para Let's Encrypt: " CERTBOT_EMAIL
[[ -z "$CERTBOT_EMAIL" ]] && error "E-mail não pode ser vazio."

read -rp "Usar Let's Encrypt staging? (s/N): " STAGING
[[ "${STAGING,,}" == "s" ]] && CERTBOT_STAGING=true || CERTBOT_STAGING=false

# ─── Verificar DNS ────────────────────────────────────────────────────────────
info "Verificando resolução DNS de $NEW_DOMAIN..."
RESOLVED_IP=$(dig +short "$NEW_DOMAIN" A | head -1)
SERVER_IP=$(curl -sf https://api.ipify.org || echo "")

if [[ -z "$RESOLVED_IP" ]]; then
    warn "DNS não resolvido ainda. Aguarde a propagação antes de continuar."
    read -rp "Continuar mesmo assim? (s/N): " FORCE
    [[ "${FORCE,,}" != "s" ]] && exit 0
elif [[ -n "$SERVER_IP" && "$RESOLVED_IP" != "$SERVER_IP" ]]; then
    warn "DNS resolve para $RESOLVED_IP, mas o IP deste servidor é $SERVER_IP."
    warn "O certbot pode falhar se o DNS não apontar para este servidor."
    read -rp "Continuar mesmo assim? (s/N): " FORCE
    [[ "${FORCE,,}" != "s" ]] && exit 0
else
    info "DNS OK: $NEW_DOMAIN → $RESOLVED_IP"
fi

# ─── Atualizar .env ───────────────────────────────────────────────────────────
info "Atualizando .env com novo domínio..."
sed -i "s/^DOMAIN=.*/DOMAIN=${NEW_DOMAIN}/" .env
sed -i "s/^CERTBOT_EMAIL=.*/CERTBOT_EMAIL=${CERTBOT_EMAIL}/" .env
grep -q '^CERTBOT_STAGING=' .env \
    && sed -i "s/^CERTBOT_STAGING=.*/CERTBOT_STAGING=${CERTBOT_STAGING}/" .env \
    || echo "CERTBOT_STAGING=${CERTBOT_STAGING}" >> .env
grep -q '^SECURE_COOKIES=' .env \
    && sed -i "s/^SECURE_COOKIES=.*/SECURE_COOKIES=true/" .env \
    || echo "SECURE_COOKIES=true" >> .env

# ─── Certificado autoassinado temporário ─────────────────────────────────────
# Criar DENTRO do volume Docker (certbot_certs) — não no FS do host
info "Gerando certificado temporário para bootstrap do nginx HTTPS..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    run --rm --no-deps --entrypoint sh certbot -c "
        mkdir -p /etc/letsencrypt/live/${NEW_DOMAIN}
        openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
            -keyout /etc/letsencrypt/live/${NEW_DOMAIN}/privkey.pem \
            -out    /etc/letsencrypt/live/${NEW_DOMAIN}/fullchain.pem \
            -subj '/CN=${NEW_DOMAIN}' 2>/dev/null
        [ -f /etc/letsencrypt/ssl-dhparams.pem ] || \
            openssl dhparam -out /etc/letsencrypt/ssl-dhparams.pem 2048 2>/dev/null
    "

# ─── Parar modo HTTP provisório e subir com HTTPS ────────────────────────────
info "Parando modo HTTP provisório..."
docker compose down 2>/dev/null || true

info "Subindo nginx com configuração HTTPS (cert temporário)..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d postgres backend nginx

info "Aguardando nginx ficar pronto..."
for i in $(seq 1 20); do
    curl -sf --insecure "https://localhost/health" &>/dev/null && break
    sleep 3
done

# ─── Obter certificado real ───────────────────────────────────────────────────
info "Solicitando certificado Let's Encrypt para ${NEW_DOMAIN}..."
STAGING_FLAG=""
[[ "$CERTBOT_STAGING" == "true" ]] && STAGING_FLAG="--staging"

docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    run --rm --no-deps \
    --entrypoint certbot certbot \
    certonly --webroot \
    -w /var/www/certbot \
    -d "${NEW_DOMAIN}" \
    --email "${CERTBOT_EMAIL}" \
    --agree-tos --non-interactive \
    $STAGING_FLAG || error "Certbot falhou. Verifique DNS e tente novamente."

# ─── Reiniciar nginx com cert real e subir todos os serviços ─────────────────
info "Reiniciando nginx com certificado real..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart nginx

info "Subindo todos os serviços..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# ─── Verificação ─────────────────────────────────────────────────────────────
sleep 5
info "Verificando HTTPS..."
HTTP_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "https://${NEW_DOMAIN}/health" || echo "ERR")
if [[ "$HTTP_STATUS" == "200" ]]; then
    info "HTTPS ativo! https://${NEW_DOMAIN}/health → 200"
else
    warn "Verificação retornou: $HTTP_STATUS — confira os logs com: docker compose logs nginx"
fi

echo ""
echo "======================================"
echo "  HTTPS configurado com sucesso!"
echo "======================================"
echo ""
echo "  URL: https://${NEW_DOMAIN}"
echo ""
echo "  Próximo passo: atualize o ESP32"
echo "  - SERVER_URL = \"https://${NEW_DOMAIN}\""
echo "  - Descomente #define USE_HTTPS em config_local.h"
echo "  - Recompile e grave (ou use OTA)"
echo ""
