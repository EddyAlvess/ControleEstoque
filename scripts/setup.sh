#!/usr/bin/env bash
# SorvPel - Setup Automatizado (Linux/macOS)
# Uso: bash scripts/setup.sh
set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RED='\033[0;31m'; NC='\033[0m'

echo -e "${CYAN}=== SorvPel Controle de Estoque - Setup ===${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

# 1. Pre-requisitos
echo -e "\n${YELLOW}[1/7] Verificando pre-requisitos...${NC}"
command -v docker &>/dev/null || { echo -e "${RED}Docker nao encontrado.${NC}"; exit 1; }
docker compose version &>/dev/null || { echo -e "${RED}Docker Compose v2 nao encontrado.${NC}"; exit 1; }
echo -e "  ${GREEN}Docker OK${NC}"

# 2. .env
echo -e "\n${YELLOW}[2/7] Configurando variaveis de ambiente...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    SECRET_KEY=$(openssl rand -hex 32)
    DB_PASS=$(openssl rand -base64 18 | tr -dc 'a-zA-Z0-9' | head -c 24)
    API_KEY=$(openssl rand -hex 16)
    sed -i "s/CHANGE_ME_SECRET_KEY_256BIT_HEX/$SECRET_KEY/" .env
    sed -i "s/CHANGE_ME_DB_PASSWORD/$DB_PASS/" .env
    sed -i "s/CHANGE_ME_ESP32_API_KEY/$API_KEY/" .env
    echo -e "  ${GREEN}.env criado com secrets gerados${NC}"
    echo -e "  ${CYAN}ANOTE a ESP32_API_KEY do .env para o firmware!${NC}"
else
    echo -e "  ${GREEN}.env ja existe${NC}"
fi

# 3. Build
echo -e "\n${YELLOW}[3/7] Construindo imagens Docker...${NC}"
docker compose build
echo -e "  ${GREEN}Build concluido${NC}"

# 4. Postgres
echo -e "\n${YELLOW}[4/7] Iniciando PostgreSQL...${NC}"
docker compose up -d postgres
echo -e "  Aguardando banco..."
until docker compose exec postgres pg_isready -U sorv_user &>/dev/null; do sleep 2; done
echo -e "  ${GREEN}PostgreSQL pronto${NC}"

# 5. Migrations
echo -e "\n${YELLOW}[5/7] Aplicando migracoes...${NC}"
docker compose run --rm backend alembic upgrade head
echo -e "  ${GREEN}Migracoes aplicadas${NC}"

# 6. Seed
echo -e "\n${YELLOW}[6/7] Inserindo dados iniciais...${NC}"
docker compose run --rm backend python scripts/seed_data.py
echo -e "  ${GREEN}Seed concluido${NC}"

# 7. Start
echo -e "\n${YELLOW}[7/7] Iniciando todos os servicos...${NC}"
docker compose up -d
echo -e "  ${GREEN}Servicos iniciados${NC}"

PORT=$(grep NGINX_PORT .env | cut -d= -f2 || echo "80")
echo -e "\n${CYAN}============================================${NC}"
echo -e "  ${GREEN}Setup concluido com sucesso!${NC}"
echo -e "  Acesse: http://localhost:${PORT}"
echo -e "  Login:  admin / admin123"
echo -e "  ${RED}ATENCAO: Altere a senha do admin!${NC}"
echo -e "  ESP32 API Key: veja .env (ESP32_API_KEY)"
echo -e "${CYAN}============================================${NC}"
