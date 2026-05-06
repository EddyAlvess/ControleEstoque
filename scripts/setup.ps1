# SorvPel - Setup Automatizado (Windows PowerShell)
# Execute: .\scripts\setup.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== SorvPel Controle de Estoque - Setup ===" -ForegroundColor Cyan

# 1. Verificar pre-requisitos
Write-Host "`n[1/7] Verificando pre-requisitos..." -ForegroundColor Yellow

try { docker version | Out-Null } catch { Write-Error "Docker nao encontrado. Instale o Docker Desktop."; exit 1 }
try { docker compose version | Out-Null } catch { Write-Error "Docker Compose v2 nao encontrado."; exit 1 }

Write-Host "  Docker OK" -ForegroundColor Green

# 2. Gerar .env se nao existir
Write-Host "`n[2/7] Configurando variaveis de ambiente..." -ForegroundColor Yellow

$envFile = Join-Path $PSScriptRoot ".." ".env"
$envExample = Join-Path $PSScriptRoot ".." ".env.example"

if (-not (Test-Path $envFile)) {
    Copy-Item $envExample $envFile

    # Gerar secrets aleatorios
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()

    $secretBytes = New-Object byte[] 32
    $rng.GetBytes($secretBytes)
    $secretKey = [BitConverter]::ToString($secretBytes) -replace '-', ''

    $dbPassBytes = New-Object byte[] 18
    $rng.GetBytes($dbPassBytes)
    $dbPass = [Convert]::ToBase64String($dbPassBytes) -replace '[+/=]', 'x'

    $apiKeyBytes = New-Object byte[] 16
    $rng.GetBytes($apiKeyBytes)
    $apiKey = [BitConverter]::ToString($apiKeyBytes) -replace '-', ''

    (Get-Content $envFile) `
        -replace 'CHANGE_ME_SECRET_KEY_256BIT_HEX', $secretKey `
        -replace 'CHANGE_ME_DB_PASSWORD', $dbPass `
        -replace 'CHANGE_ME_ESP32_API_KEY', $apiKey |
        Set-Content $envFile -Encoding utf8

    Write-Host "  .env criado com secrets gerados" -ForegroundColor Green
    Write-Host "  ANOTE a ESP32_API_KEY do arquivo .env para configurar o firmware!" -ForegroundColor Magenta
} else {
    Write-Host "  .env ja existe, usando existente" -ForegroundColor Green
}

# 3. Build das imagens
Write-Host "`n[3/7] Construindo imagens Docker..." -ForegroundColor Yellow
Set-Location (Join-Path $PSScriptRoot "..")
docker compose build
Write-Host "  Build concluido" -ForegroundColor Green

# 4. Iniciar postgres e aguardar health check
Write-Host "`n[4/7] Iniciando PostgreSQL..." -ForegroundColor Yellow
docker compose up -d postgres

Write-Host "  Aguardando banco ficar pronto..." -ForegroundColor Gray
$maxAttempts = 30
for ($i = 1; $i -le $maxAttempts; $i++) {
    try {
        docker compose exec postgres pg_isready -U sorv_user 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { break }
    } catch {}
    Start-Sleep 2
    if ($i -eq $maxAttempts) { Write-Error "Postgres nao iniciou no tempo esperado."; exit 1 }
}
Write-Host "  PostgreSQL pronto" -ForegroundColor Green

# 5. Rodar migrations
Write-Host "`n[5/7] Aplicando migracoes do banco de dados..." -ForegroundColor Yellow
docker compose run --rm backend alembic upgrade head
Write-Host "  Migracoes aplicadas" -ForegroundColor Green

# 6. Seed inicial
Write-Host "`n[6/7] Inserindo dados iniciais..." -ForegroundColor Yellow
docker compose run --rm backend python scripts/seed_data.py
Write-Host "  Dados iniciais inseridos" -ForegroundColor Green

# 7. Subir todos os servicos
Write-Host "`n[7/7] Iniciando todos os servicos..." -ForegroundColor Yellow
docker compose up -d
Write-Host "  Servicos iniciados" -ForegroundColor Green

# Resultado
$envContent = Get-Content $envFile | Where-Object { $_ -match '^NGINX_PORT=' }
$port = if ($envContent) { ($envContent -split '=')[1].Trim() } else { "80" }

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  Setup concluido com sucesso!" -ForegroundColor Green
Write-Host "  Acesse: http://localhost:$port" -ForegroundColor White
Write-Host "  Login:  admin / admin123" -ForegroundColor White
Write-Host "  ATENCAO: Altere a senha do admin no primeiro acesso!" -ForegroundColor Red
Write-Host "  ESP32 API Key: veja o arquivo .env (ESP32_API_KEY)" -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Cyan
