#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  SorvPel — Gravador de Firmware ESP32 (Linux)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ESP32_DIR="${REPO_ROOT}/esp32"

info()  { echo -e "${CYAN}►${NC} $*"; }
ok()    { echo -e "${GREEN}✔${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC} $*"; }
die()   { echo -e "${RED}✘${NC} $*"; exit 1; }
hr()    { printf "${CYAN}%0.s─${NC}" $(seq 1 55); echo; }

header() {
    clear; hr
    echo -e "  ${BOLD}${CYAN}SorvPel — Gravador de Firmware ESP32${NC}"
    hr; echo
}

# ── Detectar porta ESP32 ──────────────────────────────────────────────────────
detect_port() {
    local ports=()
    for p in /dev/ttyUSB* /dev/ttyACM*; do
        [[ -e "$p" ]] && ports+=("$p")
    done
    echo "${ports[@]:-}"
}

select_port() {
    local ports=()
    while IFS= read -r -d '' p; do ports+=("$p"); done < <(find /dev -maxdepth 1 \( -name 'ttyUSB*' -o -name 'ttyACM*' \) -print0 2>/dev/null | sort -z)

    if [[ ${#ports[@]} -eq 0 ]]; then
        die "Nenhum dispositivo ESP32 detectado.
     Certifique-se de que:
       • O cabo USB está conectado
       • O driver CH340/CP2102 está instalado
       • Você tem permissão no grupo 'dialout'"
    fi

    if [[ ${#ports[@]} -eq 1 ]]; then
        PORT="${ports[0]}"
        ok "ESP32 detectado em: ${PORT}"
        return
    fi

    echo -e "  Múltiplos dispositivos detectados. Selecione:\n"
    for i in "${!ports[@]}"; do
        echo -e "    [$((i+1))] ${ports[$i]}"
    done
    echo
    read -rp "  Número da porta: " choice
    PORT="${ports[$((choice-1))]}"
    ok "Porta selecionada: ${PORT}"
}

# ── PlatformIO ────────────────────────────────────────────────────────────────
check_pio() {
    command -v pio &>/dev/null || \
    command -v platformio &>/dev/null || \
    [[ -f "${HOME}/.platformio/penv/bin/pio" ]]
}

install_pio() {
    info "Instalando PlatformIO..."
    if command -v pip3 &>/dev/null; then
        pip3 install --quiet platformio
    elif command -v pip &>/dev/null; then
        pip install --quiet platformio
    else
        # Instala via script oficial
        curl -fsSL https://raw.githubusercontent.com/platformio/platformio-core-installer/master/get-platformio.py -o /tmp/get-pio.py
        python3 /tmp/get-pio.py
    fi

    # Adiciona ao PATH
    export PATH="${HOME}/.platformio/penv/bin:${PATH}"
    ok "PlatformIO instalado"
}

pio_cmd() {
    if command -v pio &>/dev/null; then echo "pio"
    elif command -v platformio &>/dev/null; then echo "platformio"
    elif [[ -f "${HOME}/.platformio/penv/bin/pio" ]]; then echo "${HOME}/.platformio/penv/bin/pio"
    else die "PlatformIO não encontrado"
    fi
}

# ── Grupo dialout ─────────────────────────────────────────────────────────────
check_dialout() {
    if ! groups | grep -q dialout; then
        warn "Seu usuário não está no grupo 'dialout' (necessário para acesso ao ESP32)."
        if [[ $EUID -eq 0 ]]; then
            REAL_USER="${SUDO_USER:-$USER}"
            usermod -aG dialout "$REAL_USER"
            ok "Adicionado ao grupo dialout. Faça logout/login para que tenha efeito."
        else
            echo -e "  Execute: ${BOLD}sudo usermod -aG dialout \$USER${NC}"
            echo -e "  Depois faça logout e login novamente."
            read -rp "  Tentar com sudo agora? [s/N]: " r
            [[ "${r,,}" == "s" ]] && sudo usermod -aG dialout "$USER" && warn "Faça logout/login para ativar."
        fi
    fi
}

# ── Main ──────────────────────────────────────────────────────────────────────
header

[[ -d "$ESP32_DIR" ]] || die "Diretório esp32 não encontrado: ${ESP32_DIR}"

# Coleta configurações
echo -e "  ${BOLD}Configuração do Firmware${NC}\n"

read -rp "  SSID da rede WiFi: "                               WIFI_SSID
read -rsp "  Senha do WiFi: " WIFI_PASSWORD; echo
read -rp "  URL do servidor [http://192.168.1.100]: "          SERVER_URL
SERVER_URL="${SERVER_URL:-http://192.168.1.100}"
read -rp "  Chave API ESP32 (do arquivo .env): "              API_KEY
read -rp "  ID do Terminal [ESP32-LINHA-A]: "                  DEVICE_ID
DEVICE_ID="${DEVICE_ID:-ESP32-LINHA-A}"

echo
hr

# Verifica grupo dialout
check_dialout

# Detecta porta
select_port

# Verifica / instala PlatformIO
if ! check_pio; then
    install_pio
else
    ok "PlatformIO: $($(pio_cmd) --version 2>/dev/null || echo 'instalado')"
fi

# Gera config_local.h
info "Gerando configuração do firmware..."
cat > "${ESP32_DIR}/src/config_local.h" <<EOF
#pragma once
// Gerado automaticamente pelo instalador SorvPel — NÃO versionar
#define WIFI_SSID     "${WIFI_SSID}"
#define WIFI_PASSWORD "${WIFI_PASSWORD}"
#define SERVER_URL    "${SERVER_URL}"
#define API_KEY       "${API_KEY}"
#define DEVICE_ID     "${DEVICE_ID}"
#define FIRMWARE_VER  "1.0.0"
EOF
ok "config_local.h gerado"

# Compila e grava
info "Compilando e gravando firmware (pode demorar ~1 minuto na primeira vez)..."
cd "$ESP32_DIR"
$(pio_cmd) run -t upload --upload-port "$PORT"

echo
ok "Firmware gravado com sucesso em ${PORT}!"
echo -e "\n  O terminal ESP32 tentará conectar ao WiFi '${WIFI_SSID}'"
echo -e "  e ao servidor '${SERVER_URL}'.\n"
hr
