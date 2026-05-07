#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  SorvPel — Gera o manual em PDF a partir do HTML
#  Usa Chromium ou Google Chrome em modo headless.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HTML_FILE="${SCRIPT_DIR}/SorvPel_Manual.html"
PDF_FILE="${SCRIPT_DIR}/SorvPel_Manual.pdf"

GREEN='\033[0;32m'; CYAN='\033[0;36m'; RED='\033[0;31m'; NC='\033[0m'

info() { echo -e "${CYAN}►${NC} $*"; }
ok()   { echo -e "${GREEN}✔${NC} $*"; }
die()  { echo -e "${RED}✘${NC} $*"; exit 1; }

# Localiza browser headless
find_browser() {
    for cmd in chromium-browser chromium google-chrome google-chrome-stable; do
        command -v "$cmd" &>/dev/null && echo "$cmd" && return
    done
    # Procura em paths comuns
    for p in /usr/bin/chromium /usr/bin/chromium-browser /opt/google/chrome/chrome; do
        [[ -x "$p" ]] && echo "$p" && return
    done
    return 1
}

[[ -f "$HTML_FILE" ]] || die "Arquivo não encontrado: $HTML_FILE"

BROWSER=$(find_browser) || {
    die "Chromium/Chrome não encontrado.
  Instale com:  sudo apt install chromium-browser   (Debian/Ubuntu)
                sudo yum install chromium            (CentOS/RHEL)
  Ou abra ${HTML_FILE} no navegador e use Ctrl+P > Salvar como PDF."
}

info "Gerando PDF com: ${BROWSER}"
info "  Fonte : ${HTML_FILE}"
info "  Saída : ${PDF_FILE}"

"$BROWSER" \
    --headless \
    --disable-gpu \
    --run-all-compositor-stages-before-draw \
    --print-to-pdf="${PDF_FILE}" \
    --no-pdf-header-footer \
    "file://${HTML_FILE}" 2>/dev/null

if [[ -f "$PDF_FILE" ]]; then
    SIZE=$(du -k "$PDF_FILE" | cut -f1)
    ok "PDF gerado: ${PDF_FILE} (${SIZE} KB)"
else
    die "Falha ao gerar PDF. Abra manualmente no navegador e use Ctrl+P > Salvar como PDF."
fi
