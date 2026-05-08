#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  InventControl — Gera os manuais em PDF a partir dos HTMLs
#  Usa Chromium ou Google Chrome em modo headless.
#  Gera: InventControl_Manual.pdf e InventControl_Manual_Operacional.pdf
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

GREEN='\033[0;32m'; CYAN='\033[0;36m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'

info() { echo -e "${CYAN}►${NC} $*"; }
ok()   { echo -e "${GREEN}✔${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }
err()  { echo -e "${RED}✘${NC} $*"; }

# Localiza browser headless
find_browser() {
    for cmd in chromium-browser chromium google-chrome google-chrome-stable; do
        command -v "$cmd" &>/dev/null && echo "$cmd" && return
    done
    for p in /usr/bin/chromium /usr/bin/chromium-browser /opt/google/chrome/chrome; do
        [[ -x "$p" ]] && echo "$p" && return
    done
    return 1
}

BROWSER=$(find_browser) || {
    err "Chromium/Chrome não encontrado."
    echo "  Instale com:  sudo apt install chromium-browser   (Debian/Ubuntu)"
    echo "                sudo yum install chromium            (CentOS/RHEL)"
    echo "  Ou abra cada arquivo HTML no navegador e use Ctrl+P > Salvar como PDF."
    exit 1
}

info "Usando browser: ${BROWSER}"
echo

# Lista de arquivos a gerar
declare -a HTMLS=("InventControl_Manual.html" "InventControl_Manual_Operacional.html")
declare -a PDFS=("InventControl_Manual.pdf"  "InventControl_Manual_Operacional.pdf")

OK=0; FAIL=0

for i in "${!HTMLS[@]}"; do
    HTML_FILE="${SCRIPT_DIR}/${HTMLS[$i]}"
    PDF_FILE="${SCRIPT_DIR}/${PDFS[$i]}"

    if [[ ! -f "$HTML_FILE" ]]; then
        err "Não encontrado: $HTML_FILE"
        (( FAIL++ )) || true
        continue
    fi

    info "Gerando ${PDFS[$i]}..."

    "$BROWSER" \
        --headless \
        --disable-gpu \
        --run-all-compositor-stages-before-draw \
        --print-to-pdf="${PDF_FILE}" \
        --no-pdf-header-footer \
        "file://${HTML_FILE}" 2>/dev/null || true

    if [[ -f "$PDF_FILE" ]]; then
        SIZE=$(du -k "$PDF_FILE" | cut -f1)
        ok "  Gerado: ${PDF_FILE} (${SIZE} KB)"
        (( OK++ )) || true
    else
        err "  Falha ao gerar: ${PDFS[$i]}"
        (( FAIL++ )) || true
    fi
done

echo
if [[ $FAIL -eq 0 ]]; then
    ok "Todos os PDFs gerados em: ${SCRIPT_DIR}"
else
    warn "${FAIL} arquivo(s) com falha. Gere manualmente: abra o HTML no navegador e use Ctrl+P > Salvar como PDF."
    exit 1
fi
