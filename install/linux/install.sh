#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  SorvPel Controle de Estoque — Instalador Linux
#  Testado em: Ubuntu 20.04+, Debian 11+, CentOS/RHEL 8+
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Cores ────────────────────────────────────────────────────────────────────
RED='\033[0;31m';  GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m';  BOLD='\033[1m'; NC='\033[0m'

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APP_NAME="SorvPel Controle de Estoque"

# ── Helpers ───────────────────────────────────────────────────────────────────
info()    { echo -e "${CYAN}►${NC} $*"; }
ok()      { echo -e "${GREEN}✔${NC} $*"; }
warn()    { echo -e "${YELLOW}⚠${NC} $*"; }
error()   { echo -e "${RED}✘${NC} $*"; }
die()     { error "$*"; exit 1; }
hr()      { printf "${BLUE}%0.s─${NC}" $(seq 1 60); echo; }
rand_hex(){ cat /dev/urandom | tr -dc 'a-f0-9' | head -c "$1"; }

header() {
    clear
    hr
    echo -e "  ${BOLD}${CYAN}${APP_NAME}${NC}  —  Instalador v1.0"
    echo -e "  Passo $1 de 4: ${BOLD}$2${NC}"
    hr
    echo
}

require_root() {
    if [[ $EUID -ne 0 ]]; then
        warn "Este instalador requer privilégios de root."
        exec sudo bash "$0" "$@"
    fi
}

# ── Passo 0: Boas-vindas ──────────────────────────────────────────────────────
step_welcome() {
    header "0" "Boas-vindas"
    cat <<'EOF'
  Bem-vindo ao instalador do SorvPel Controle de Estoque!

  Este script irá:
    • Instalar Docker Engine e Docker Compose (se necessário)
    • Configurar o arquivo .env com suas credenciais
    • Iniciar os containers (banco de dados, backend, Nginx)
    • Executar as migrações do banco de dados
    • Criar o usuário administrador

  REQUISITOS:
    • Ubuntu 20.04+ / Debian 11+ / CentOS 8+ / RHEL 8+
    • Acesso à internet (para baixar imagens Docker)
    • Porta HTTP livre (padrão: 8080)

EOF
    read -rp "  Pressione ENTER para continuar ou Ctrl+C para cancelar..."
}

# ── Passo 1: Pré-requisitos ───────────────────────────────────────────────────
step_prereqs() {
    header "1" "Verificando Pré-requisitos"

    # Docker
    if command -v docker &>/dev/null; then
        ok "Docker instalado: $(docker --version)"
    else
        warn "Docker não encontrado. Instalando..."
        install_docker
    fi

    # Docker Compose (plugin v2)
    if docker compose version &>/dev/null 2>&1; then
        ok "Docker Compose: $(docker compose version --short)"
    else
        warn "Docker Compose plugin não encontrado. Instalando..."
        install_docker_compose
    fi

    # Docker daemon
    if docker info &>/dev/null 2>&1; then
        ok "Docker daemon em execução"
    else
        info "Iniciando Docker daemon..."
        systemctl start docker 2>/dev/null || service docker start 2>/dev/null || die "Não foi possível iniciar o Docker"
        ok "Docker iniciado"
    fi

    # Habilitar Docker no boot
    systemctl enable docker 2>/dev/null || true

    echo
    ok "Todos os pré-requisitos atendidos!"
    echo
}

install_docker() {
    if command -v apt-get &>/dev/null; then
        apt-get update -qq
        apt-get install -y -qq ca-certificates curl gnupg lsb-release
        mkdir -p /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
            > /etc/apt/sources.list.d/docker.list
        apt-get update -qq
        apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    elif command -v yum &>/dev/null; then
        yum install -y -q yum-utils
        yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        yum install -y -q docker-ce docker-ce-cli containerd.io docker-compose-plugin
    else
        die "Gerenciador de pacotes não suportado. Instale o Docker manualmente: https://docs.docker.com/engine/install/"
    fi
    ok "Docker instalado com sucesso"
}

install_docker_compose() {
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name"' | cut -d'"' -f4)
    curl -sSL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    ok "Docker Compose instalado"
}

# ── Passo 2: Configuração ─────────────────────────────────────────────────────
step_config() {
    header "2" "Configuração"

    echo -e "  Configure os parâmetros abaixo. Pressione ENTER para usar o padrão.\n"

    # Diretório
    echo -e "  ${BOLD}Diretório de instalação${NC} [${REPO_ROOT}]:"
    read -rp "  > " INSTALL_DIR
    INSTALL_DIR="${INSTALL_DIR:-$REPO_ROOT}"
    [[ -d "$INSTALL_DIR" ]] || die "Diretório não encontrado: $INSTALL_DIR"

    # Porta
    echo -e "\n  ${BOLD}Porta HTTP (Nginx)${NC} [8080]:"
    read -rp "  > " PORT
    PORT="${PORT:-8080}"

    # Senha do banco
    DEFAULT_DB_PW=$(rand_hex 16)
    echo -e "\n  ${BOLD}Senha do banco de dados${NC} [${DEFAULT_DB_PW}]:"
    read -rsp "  > " DB_PW; echo
    DB_PW="${DB_PW:-$DEFAULT_DB_PW}"

    # Senha admin
    echo -e "\n  ${BOLD}Senha do usuário admin (portal web)${NC} [admin123]:"
    read -rsp "  > " ADMIN_PW; echo
    ADMIN_PW="${ADMIN_PW:-admin123}"

    # API Key ESP32
    DEFAULT_API_KEY=$(rand_hex 20)
    echo -e "\n  ${BOLD}Chave API para terminais ESP32${NC} [${DEFAULT_API_KEY}]:"
    read -rp "  > " API_KEY
    API_KEY="${API_KEY:-$DEFAULT_API_KEY}"

    SECRET_KEY=$(rand_hex 32)

    echo
    hr
    echo -e "  ${BOLD}Resumo da configuração:${NC}"
    echo -e "    Diretório : $INSTALL_DIR"
    echo -e "    Porta     : $PORT"
    echo -e "    Admin     : admin / ${ADMIN_PW}"
    echo -e "    API Key   : ${API_KEY}"
    hr
    echo
    read -rp "  Confirmar instalação? [s/N]: " CONFIRM
    [[ "${CONFIRM,,}" == "s" ]] || die "Instalação cancelada pelo usuário."

    # Exporta variáveis para o próximo passo
    export INSTALL_DIR PORT DB_PW ADMIN_PW API_KEY SECRET_KEY
}

# ── Passo 3: Instalação ───────────────────────────────────────────────────────
step_install() {
    header "3" "Instalando"

    cd "$INSTALL_DIR"

    # Cria .env
    info "Gerando arquivo .env..."
    cat > .env <<EOF
POSTGRES_DB=controle_estoque
POSTGRES_USER=sorv_user
POSTGRES_PASSWORD=${DB_PW}
SECRET_KEY=${SECRET_KEY}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
ESP32_API_KEY=${API_KEY}
NGINX_PORT=${PORT}
ENVIRONMENT=production
TZ=America/Sao_Paulo
EOF
    ok ".env criado"

    # Inicia containers
    info "Iniciando containers Docker (pode demorar na primeira vez)..."
    docker compose up -d --build
    ok "Containers iniciados"

    # Aguarda banco
    info "Aguardando banco de dados..."
    for i in $(seq 1 30); do
        if docker compose exec postgres pg_isready -U sorv_user &>/dev/null 2>&1; then
            ok "Banco de dados pronto"
            break
        fi
        [[ $i -eq 30 ]] && die "Timeout aguardando banco de dados"
        sleep 2
    done

    # Migrações
    info "Executando migrações do banco de dados..."
    docker compose run --rm backend alembic upgrade head
    ok "Banco de dados atualizado"

    # Cria usuário admin
    info "Criando usuário administrador..."
    docker compose run --rm backend python - <<PYEOF
import asyncio, sys
sys.path.insert(0, '/app')
from app.database import AsyncSessionLocal
from app.models.user import WebUser
from app.services.auth_service import hash_password
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(WebUser).where(WebUser.username == 'admin'))
        if not r.scalar_one_or_none():
            u = WebUser(username='admin', full_name='Administrador',
                        hashed_password=hash_password('${ADMIN_PW}'),
                        role='admin', is_active=True)
            db.add(u)
            await db.commit()
            print('Usuário admin criado com sucesso')
        else:
            print('Usuário admin já existe — mantendo senha atual')

asyncio.run(main())
PYEOF
    ok "Usuário admin configurado"

    # Adiciona usuário corrente ao grupo docker (Linux)
    if [[ -n "${SUDO_USER:-}" ]]; then
        usermod -aG docker "$SUDO_USER" 2>/dev/null || true
        info "Usuário ${SUDO_USER} adicionado ao grupo docker (requer logout/login)"
    fi

    echo
    hr
}

# ── Passo 4: Conclusão ────────────────────────────────────────────────────────
step_done() {
    header "4" "Instalação Concluída"

    cat <<EOF

  ${GREEN}✔ SorvPel instalado com sucesso!${NC}

  Acesso ao portal:
    URL     : http://localhost:${PORT}
    Usuário : admin
    Senha   : ${ADMIN_PW}

  Chave API ESP32: ${API_KEY}
  (configure esta chave no arquivo esp32/src/config.h e no .env)

  Comandos úteis:
    Iniciar   : cd ${INSTALL_DIR} && docker compose up -d
    Parar     : cd ${INSTALL_DIR} && docker compose down
    Logs      : cd ${INSTALL_DIR} && docker compose logs -f
    Atualizar : cd ${INSTALL_DIR} && git pull && docker compose up -d --build

  O manual do sistema está em: ${INSTALL_DIR}/docs/SorvPel_Manual.html

EOF
    hr

    # Gera PDF se Chromium/Chrome disponível
    if command -v chromium-browser &>/dev/null || command -v google-chrome &>/dev/null || command -v chromium &>/dev/null; then
        info "Gerando manual em PDF..."
        bash "${INSTALL_DIR}/docs/gerar_pdf.sh" 2>/dev/null || true
    else
        warn "Chromium não encontrado — abra docs/SorvPel_Manual.html no navegador e salve como PDF"
    fi
}

# ── Main ──────────────────────────────────────────────────────────────────────
require_root "$@"
step_welcome
step_prereqs
step_config
step_install
step_done
