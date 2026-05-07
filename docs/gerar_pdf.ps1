#Requires -Version 5.1
<#
.SYNOPSIS
    SorvPel — Gera os manuais em PDF a partir do HTML.
.DESCRIPTION
    Usa Microsoft Edge (headless) para converter os manuais HTML em PDF.
    Gera: SorvPel_Manual.pdf e SorvPel_Manual_Operacional.pdf
    Execute a partir da raiz do projeto ou da pasta docs/.
#>

$ErrorActionPreference = "Stop"

$DOCS_DIR = $PSScriptRoot

$FILES = @(
    @{ Html = "SorvPel_Manual.html";            Pdf = "SorvPel_Manual.pdf" },
    @{ Html = "SorvPel_Manual_Operacional.html"; Pdf = "SorvPel_Manual_Operacional.pdf" }
)

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
    Write-Host "  Abra manualmente os arquivos HTML no Edge/Chrome e use Ctrl+P > Salvar como PDF."
    exit 1
}

$ok = 0; $fail = 0
foreach ($f in $FILES) {
    $htmlPath = Join-Path $DOCS_DIR $f.Html
    $pdfPath  = Join-Path $DOCS_DIR $f.Pdf

    if (-not (Test-Path $htmlPath)) {
        Write-Err "Nao encontrado: $htmlPath"
        $fail++; continue
    }

    Write-Info "Gerando $($f.Pdf)..."
    $fileUri = "file:///" + ($htmlPath -replace "\\", "/")

    & $edgeExe `
        --headless `
        --disable-gpu `
        --run-all-compositor-stages-before-draw `
        --print-to-pdf="$pdfPath" `
        --print-to-pdf-no-header `
        --no-pdf-header-footer `
        "$fileUri" 2>$null

    if ($LASTEXITCODE -eq 0 -and (Test-Path $pdfPath)) {
        $size = [math]::Round((Get-Item $pdfPath).Length / 1KB, 1)
        Write-Ok "  Gerado: $pdfPath ($size KB)"
        $ok++
    } else {
        Write-Err "  Falha ao gerar: $($f.Pdf)"
        $fail++
    }
}

Write-Host ""
if ($fail -eq 0) {
    Write-Ok "Todos os PDFs gerados com sucesso em: $DOCS_DIR"
} else {
    Write-Err "$fail arquivo(s) com falha. Gere manualmente: abra o HTML no Edge/Chrome e use Ctrl+P > Salvar como PDF."
    exit 1
}
