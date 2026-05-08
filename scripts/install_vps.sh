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
echo "  Sem domínio ainda? Opções:"
echo "  1. Use IP.nip.io como domínio (ex: 1.2.3.4.nip.io) — HTTPS grátis via Let's Encrypt"
echo "  2. Digite o IP do servidor — instala em modo HTTP provisório (sem HTTPS)"
echo "     Execute 'bash scripts/setup_https.sh' quando o domínio estiver pronto."
echo ""

read -rp "Domínio ou IP do servidor: " DOMAIN
[[ -z "$DOMAIN" ]] && error "Não pode ser vazio."

# Detectar se é IP (modo HTTP provisório) ou domínio (modo HTTPS)
HTTP_ONLY=false
if echo "$DOMAIN" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'; then
    HTTP_ONLY=true
    warn "IP detectado — instalando em modo HTTP provisório (sem HTTPS/certbot)."
    warn "Execute 'bash scripts/setup_https.sh' quando o domínio estiver registrado."
    CERTBOT_EMAIL=""
    CERTBOT_STAGING=false
else
    read -rp "E-mail para Let's Encrypt: " CERTBOT_EMAIL
    [[ -z "$CERTBOT_EMAIL" ]] && error "E-mail não pode ser vazio."
    read -rp "Usar Let's Encrypt staging? (s/N): " STAGING
    [[ "${STAGING,,}" == "s" ]] && CERTBOT_STAGING=true || CERTBOT_STAGING=false
fi

read -rsp "Senha do administrador (mín. 8 chars): " ADMIN_PASS
echo ""
[[ ${#ADMIN_PASS} -lt 8 ]] && error "Senha muito curta."

INSTALL_DIR="/opt/inventcontrol"
REPO_URL="${REPO_URL:-}"   # opcional: repositório git

# ─── 1. Dependências do sistema ───────────────────────────────────────────────
info "Atualizando sistema..."
apt-get update -qq && apt-get upgrade -y -qq

info "Instalando utilitários..."
apt-get install -y -qq curl git ufw openssl dnsutils

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
[[ "$HTTP_ONLY" == "false" ]] && ufw allow 443/tcp
ufw --force enable
info "UFW ativo: SSH + 80$([ "$HTTP_ONLY" == "false" ] && echo " + 443" || echo "")"

# ─── 4. Diretório de instalação ──────────────────────────────────────────────
info "Criando diretório $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

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
    error "Não encontrei arquivos. Execute a partir do repositório ou defina REPO_URL."
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
# Em modo HTTP provisório, SECURE_COOKIES=false até migrar para HTTPS
SECURE_COOKIES=$([ "$HTTP_ONLY" == "true" ] && echo "false" || echo "true")
ENVIRONMENT=production
LOG_DIR=/app/logs
EOF

chmod 600 "$INSTALL_DIR/.env"
info ".env gerado em $INSTALL_DIR/.env"

# ─── 6. Build ────────────────────────────────────────────────────────────────
cd "$INSTALL_DIR"
info "Fazendo build das imagens..."

if [[ "$HTTP_ONLY" == "true" ]]; then
    DC="docker compose -f docker-compose.yml -f docker-compose.prod-http.yml"
else
    DC="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
fi

$DC build --quiet

# ─── 7. Certificado temporário (apenas modo HTTPS) ───────────────────────────
# IMPORTANTE: o cert deve ser criado DENTRO do volume Docker (certbot_certs),
# não no FS do host — o container nginx lê do volume, não de /etc/letsencrypt.
if [[ "$HTTP_ONLY" == "false" ]]; then
    info "Gerando certificado temporário para bootstrap nginx HTTPS..."
    $DC run --rm --no-deps --entrypoint sh certbot -c "
        mkdir -p /etc/letsencrypt/live/${DOMAIN}
        openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
            -keyout /etc/letsencrypt/live/${DOMAIN}/privkey.pem \
            -out    /etc/letsencrypt/live/${DOMAIN}/fullchain.pem \
            -subj '/CN=${DOMAIN}' 2>/dev/null
        [ -f /etc/letsencrypt/ssl-dhparams.pem ] || \
            openssl dhparam -out /etc/letsencrypt/ssl-dhparams.pem 2048 2>/dev/null
    "
fi

# ─── 8. Primeiro start ───────────────────────────────────────────────────────
info "Iniciando serviços..."
$DC up -d postgres backend nginx

info "Aguardando backend ficar saudável..."
for i in $(seq 1 30); do
    # Em modo HTTP: curl http; em modo HTTPS: porta 80 redireciona, testar https
    if curl -sf "http://localhost/health" &>/dev/null || \
       curl -sf --insecure "https://localhost/health" &>/dev/null; then
        break
    fi
    sleep 3
done

# ─── 9. Certbot (apenas modo HTTPS) ──────────────────────────────────────────
# IMPORTANTE: usar $DC run para que o certbot grave no volume correto
# (inventcontrol_certbot_certs), não em um volume avulso sem prefixo.
if [[ "$HTTP_ONLY" == "false" ]]; then
    info "Obtendo certificado Let's Encrypt para ${DOMAIN}..."
    STAGING_FLAG=""
    [[ "$CERTBOT_STAGING" == "true" ]] && STAGING_FLAG="--staging"

    $DC run --rm --no-deps \
        --entrypoint certbot certbot \
        certonly --webroot \
        -w /var/www/certbot \
        -d "${DOMAIN}" \
        --email "${CERTBOT_EMAIL}" \
        --agree-tos --non-interactive \
        $STAGING_FLAG || warn "Certbot falhou — verifique DNS e tente: bash scripts/setup_https.sh"

    $DC restart nginx
fi

# ─── 10. Todos os serviços ───────────────────────────────────────────────────
info "Subindo todos os serviços..."
$DC up -d

# ─── 11. Migrações do banco ──────────────────────────────────────────────────
info "Rodando migrações do banco..."
$DC run --rm backend alembic upgrade head

# ─── 12. Seed inicial ────────────────────────────────────────────────────────
info "Criando dados iniciais (usuário admin)..."
$DC run --rm \
    -e ADMIN_PASSWORD="${ADMIN_PASS}" \
    backend python scripts/seed_data.py

# ─── 13. Logrotate ───────────────────────────────────────────────────────────
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

# ─── 14. Backup diário do banco ──────────────────────────────────────────────
info "Configurando backup diário do banco..."
mkdir -p /opt/inventcontrol/backups
cat > /etc/cron.d/inventcontrol-backup <<CRON
0 3 * * * root cd $INSTALL_DIR && docker compose exec -T postgres pg_dump -U inv_user controle_estoque | gzip > /opt/inventcontrol/backups/db_\$(date +\%F).sql.gz 2>/dev/null
5 3 * * * root find /opt/inventcontrol/backups -name 'db_*.sql.gz' -mtime +30 -delete 2>/dev/null
CRON

# ─── Resumo ───────────────────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "  InventControl instalado com sucesso!"
echo "============================================"
echo ""
if [[ "$HTTP_ONLY" == "true" ]]; then
    echo "  MODO: HTTP provisório (sem HTTPS)"
    echo "  URL:  http://${DOMAIN}"
    echo ""
    echo "  ⚠  Quando o domínio DNS estiver pronto:"
    echo "     bash /opt/inventcontrol/scripts/setup_https.sh"
    echo ""
    echo "  ESP32: use SERVER_URL=\"http://${DOMAIN}\""
    echo "         NÃO defina USE_HTTPS até migrar para HTTPS"
else
    echo "  MODO: HTTPS ativo"
    echo "  URL:  https://${DOMAIN}"
fi
echo ""
echo "  Usuário:       admin"
echo "  Senha:         ${ADMIN_PASS}"
echo ""
echo "  ESP32 API Key: ${ESP32_API_KEY}"
echo "  (copie para config_local.h no firmware)"
echo ""
echo "  Arquivos em:   ${INSTALL_DIR}"
echo "  Logs em:       ${INSTALL_DIR}/logs"
echo "  Backups em:    /opt/inventcontrol/backups"
echo ""
