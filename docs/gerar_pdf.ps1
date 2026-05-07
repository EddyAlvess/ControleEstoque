#Requires -Version 5.1
<#
.SYNOPSIS
    SorvPel — Gera o manual em PDF a partir do HTML.
.DESCRIPTION
    Usa Microsoft Edge (headless) para converter SorvPel_Manual.html em PDF.
    Execute a partir da raiz do projeto ou da pasta docs/.
#>

$ErrorActionPreference = "Stop"

$DOCS_DIR  = $PSScriptRoot
$HTML_FILE = Join-Path $DOCS_DIR "SorvPel_Manual.html"
$PDF_FILE  = Join-Path $DOCS_DIR "SorvPel_Manual.pdf"

function Write-Info($msg)  { Write-Host "► $msg" -ForegroundColor Cyan }
function Write-Ok($msg)    { Write-Host "✔ $msg" -ForegroundColor Green }
function Write-Err($msg)   { Write-Host "✘ $msg" -ForegroundColor Red }

# Localiza o Edge
$edgePaths = @(
    "${env:ProgramFiles}\Microsoft\Edge\Application\msedge.exe",
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "${env:LOCALAPPDATA}\Microsoft\Edge\Application\msedge.exe"
)
$edgeExe = $edgePaths | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $edgeExe) {
    # Tenta no PATH
    $cmd = Get-Command msedge -ErrorAction SilentlyContinue
    if ($cmd) { $edgeExe = $cmd.Source }
}

if (-not $edgeExe) {
    Write-Err "Microsoft Edge nao encontrado."
    Write-Host "  Abra manualmente docs\SorvPel_Manual.html no Edge/Chrome e use"
    Write-Host "  Ctrl+P > Salvar como PDF."
    exit 1
}

if (-not (Test-Path $HTML_FILE)) {
    Write-Err "Arquivo nao encontrado: $HTML_FILE"
    exit 1
}

Write-Info "Gerando PDF com Microsoft Edge..."
Write-Info "  Fonte : $HTML_FILE"
Write-Info "  Saida : $PDF_FILE"

$fileUri = "file:///" + ($HTML_FILE -replace "\\", "/")

& $edgeExe `
    --headless `
    --disable-gpu `
    --run-all-compositor-stages-before-draw `
    --print-to-pdf="$PDF_FILE" `
    --print-to-pdf-no-header `
    --no-pdf-header-footer `
    "$fileUri" 2>$null

if ($LASTEXITCODE -eq 0 -and (Test-Path $PDF_FILE)) {
    $size = [math]::Round((Get-Item $PDF_FILE).Length / 1KB, 1)
    Write-Ok "PDF gerado: $PDF_FILE ($size KB)"
} else {
    Write-Err "Falha ao gerar PDF. Tente manualmente:"
    Write-Host "  1. Abra $HTML_FILE no Edge ou Chrome"
    Write-Host "  2. Ctrl+P > Impressora: 'Salvar como PDF'"
    Write-Host "  3. Clique em Salvar"
    exit 1
}
