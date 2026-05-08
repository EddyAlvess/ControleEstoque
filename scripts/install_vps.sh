#!/usr/bin/env bash
# InventControl — Instalação VPS Ubuntu Server 24.04
# Uso: bash install_vps.sh
# Execute como root ou usuário com sudo sem senha.
set -euo pipefail

# ─── Cores ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERRO]${NC} $*"; exit 1; }

# ─── Parâmetros ──────────────────────────────────────────────────────────────
echo ""
echo "=============================="
echo "  InventControl — Instalação  "
echo "=============================="
echo ""

read -rp "Domínio (ex: estoque.suaempresa.com): " DOMAIN
[[ -z "$DOMAIN" ]] && error "Domínio não pode ser vazio."

read -rp "E-mail para Let's Encrypt: " CERTBOT_EMAIL
[[ -z "$CERTBOT_EMAIL" ]] && error "E-mail não pode ser vazio."

read -rsp "Senha do administrador (mín. 8 chars): " ADMIN_PASS
echo ""
[[ ${#ADMIN_PASS} -lt 8 ]] && error "Senha muito curta."

read -rp "Usar Let's Encrypt staging? (s/N): " STAGING
[[ "${STAGING,,}" == "s" ]] && CERTBOT_STAGING=true || CERTBOT_STAGING=false

INSTALL_DIR="/opt/inventcontrol"
REPO_URL="${REPO_URL:-}"   # opcional: repositório git

# ─── 1. Dependências do sistema ───────────────────────────────────────────────
info "Atualizando sistema..."
apt-get update -qq && apt-get upgrade -y -qq

info "Instalando utilitários..."
apt-get install -y -qq curl git ufw openssl

# ─── 2. Docker Engine ────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    info "Instalando Docker Engine..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable --now docker
else
    info "Docker já instalado: $(docker --version)"
fi

# ─── 3. UFW Firewall ─────────────────────────────────────────────────────────
info "Configurando firewall UFW..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
info "UFW ativo: SSH + 80 + 443"

# ─── 4. Diretório de instalação ──────────────────────────────────────────────
info "Criando diretório $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

# Copiar arquivos do repositório ou do diretório corrente
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

if [[ -f "$REPO_DIR/docker-compose.yml" ]]; then
    info "Copiando arquivos do repositório local..."
    rsync -a --exclude='.git' --exclude='*.env' \
          --exclude='backend/app/static/logos' \
          "$REPO_DIR/" "$INSTALL_DIR/"
elif [[ -n "$REPO_URL" ]]; then
    info "Clonando repositório $REPO_URL..."
    git clone "$REPO_URL" "$INSTALL_DIR"
else
    error "Não encontrei arquivos para copiar. Execute a partir do repositório ou defina REPO_URL."
fi

# ─── 5. Gerar .env ───────────────────────────────────────────────────────────
info "Gerando arquivo .env com segredos aleatórios..."
DB_PASSWORD="$(openssl rand -hex 24)"
SECRET_KEY="$(openssl rand -hex 32)"
ESP32_API_KEY="$(openssl rand -hex 20)"

cat > "$INSTALL_DIR/.env" <<EOF
# ── PostgreSQL ─────────────────────────────────────────────────────────────
POSTGRES_DB=controle_estoque
POSTGRES_USER=inv_user
POSTGRES_PASSWORD=${DB_PASSWORD}

# ── FastAPI / JWT ──────────────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://inv_user:${DB_PASSWORD}@postgres:5432/controle_estoque?ssl=disable
SECRET_KEY=${SECRET_KEY}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# ── ESP32 ──────────────────────────────────────────────────────────────────
ESP32_API_KEY=${ESP32_API_KEY}

# ── Domínio e TLS ──────────────────────────────────────────────────────────
DOMAIN=${DOMAIN}
CERTBOT_EMAIL=${CERTBOT_EMAIL}
CERTBOT_STAGING=${CERTBOT_STAGING}

# ── Segurança ──────────────────────────────────────────────────────────────
SECURE_COOKIES=true
ENVIRONMENT=production
LOG_DIR=/app/logs
EOF

chmod 600 "$INSTALL_DIR/.env"
info ".env gerado em $INSTALL_DIR/.env"

# ─── 6. Certificado autoassinado temporário (para nginx iniciar) ─────────────
info "Gerando certificado temporário para bootstrap do nginx..."
mkdir -p "/etc/letsencrypt/live/${DOMAIN}"
openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout "/etc/letsencrypt/live/${DOMAIN}/privkey.pem" \
    -out    "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" \
    -subj   "/CN=${DOMAIN}" 2>/dev/null

# dhparam necessário para nginx
if [[ ! -f /etc/letsencrypt/ssl-dhparams.pem ]]; then
    openssl dhparam -out /etc/letsencrypt/ssl-dhparams.pem 2048 2>/dev/null
fi

# ─── 7. Build e primeiro start (apenas nginx + backend + postgres) ────────────
cd "$INSTALL_DIR"
info "Fazendo build das imagens..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml build --quiet

info "Iniciando serviços (bootstrap sem certbot)..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d postgres backend nginx

info "Aguardando backend ficar saudável..."
for i in $(seq 1 30); do
    if curl -sf "http://localhost/health" &>/dev/null; then
        break
    fi
    sleep 3
done

# ─── 8. Obter certificado real via Let's Encrypt ──────────────────────────────
info "Obtendo certificado Let's Encrypt para ${DOMAIN}..."
STAGING_FLAG=""
[[ "$CERTBOT_STAGING" == "true" ]] && STAGING_FLAG="--staging"

docker run --rm \
    -v certbot_certs:/etc/letsencrypt \
    -v certbot_webroot:/var/www/certbot \
    certbot/certbot certonly --webroot \
    -w /var/www/certbot \
    -d "${DOMAIN}" \
    --email "${CERTBOT_EMAIL}" \
    --agree-tos --non-interactive \
    $STAGING_FLAG || warn "Certbot falhou — verifique DNS e tente novamente com: bash $SCRIPT_DIR/renew_certs.sh"

# Reiniciar nginx para carregar cert real
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart nginx

# ─── 9. Iniciar todos os serviços (incluindo certbot) ────────────────────────
info "Iniciando todos os serviços..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# ─── 10. Migrações do banco ───────────────────────────────────────────────────
info "Rodando migrações do banco..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm backend alembic upgrade head

# ─── 11. Seed inicial ─────────────────────────────────────────────────────────
info "Criando dados iniciais (usuário admin)..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm \
    -e ADMIN_PASSWORD="${ADMIN_PASS}" \
    backend python scripts/seed_data.py

# ─── 12. Logrotate ───────────────────────────────────────────────────────────
info "Configurando logrotate..."
cat > /etc/logrotate.d/inventcontrol <<'LOGROTATE'
/opt/inventcontrol/logs/**/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    sharedscripts
}
LOGROTATE

# ─── 13. Backup diário do banco ───────────────────────────────────────────────
info "Configurando backup diário do banco..."
cat > /etc/cron.d/inventcontrol-backup <<CRON
0 3 * * * root cd $INSTALL_DIR && docker compose exec -T postgres pg_dump -U inv_user controle_estoque | gzip > /opt/inventcontrol/backups/db_\$(date +\%F).sql.gz 2>/dev/null
CRON
mkdir -p /opt/inventcontrol/backups
# Manter apenas 30 backups
cat >> /etc/cron.d/inventcontrol-backup <<CRON
5 3 * * * root find /opt/inventcontrol/backups -name 'db_*.sql.gz' -mtime +30 -delete 2>/dev/null
CRON

# ─── Resumo ───────────────────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "  InventControl instalado com sucesso!"
echo "============================================"
echo ""
echo "  URL:          https://${DOMAIN}"
echo "  Usuário:      admin"
echo "  Senha:        ${ADMIN_PASS}"
echo ""
echo "  ESP32 API Key: ${ESP32_API_KEY}"
echo "  (copie para config_local.h no firmware)"
echo ""
echo "  Arquivos em: ${INSTALL_DIR}"
echo "  Logs em:     ${INSTALL_DIR}/logs"
echo "  Backups em:  /opt/inventcontrol/backups"
echo ""
echo "  Próximos passos:"
echo "  1. Acesse https://${DOMAIN} e faça login"
echo "  2. Configure o ESP32 com a API Key acima"
echo "  3. Para atualizar: cd ${INSTALL_DIR} && git pull && docker compose build && docker compose up -d"
echo ""
