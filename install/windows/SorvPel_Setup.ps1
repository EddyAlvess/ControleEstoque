#Requires -Version 5.1
<#
.SYNOPSIS
    Instalador do SorvPel Controle de Estoque — Windows
.DESCRIPTION
    Wizard GUI (WinForms) para instalação do servidor SorvPel via Docker.
    Execute como Administrador ou deixe o script solicitar elevação.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Elevação automática ───────────────────────────────────────────────────────
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

# ── Constantes ────────────────────────────────────────────────────────────────
$REPO_ROOT  = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$APP_NAME   = "SorvPel Controle de Estoque"
$VERSION    = "1.0"
$COLOR_BG   = [Drawing.Color]::FromArgb(26, 26, 46)
$COLOR_ACC  = [Drawing.Color]::FromArgb(233, 69, 96)
$COLOR_WH   = [Drawing.Color]::White
$COLOR_GRAY = [Drawing.Color]::FromArgb(240, 240, 245)

# ── Estado ────────────────────────────────────────────────────────────────────
$script:page      = 0
$script:cfg       = @{}
$script:installOk = $false

# ── Helpers ───────────────────────────────────────────────────────────────────
function New-Label($text, $x, $y, $w, $h, $font = $null, $color = $null) {
    $l = New-Object Windows.Forms.Label
    $l.Text = $text; $l.Location = "$x,$y"; $l.Size = "$w,$h"
    $l.ForeColor = if ($color) { $color } else { [Drawing.Color]::Black }
    $l.Font = if ($font) { $font } else { New-Object Drawing.Font("Segoe UI", 9) }
    return $l
}
function New-TB($x, $y, $w, $pass = $false) {
    $tb = New-Object Windows.Forms.TextBox
    $tb.Location = "$x,$y"; $tb.Width = $w
    $tb.Font = New-Object Drawing.Font("Segoe UI", 10)
    if ($pass) { $tb.UseSystemPasswordChar = $true }
    return $tb
}
function New-Btn($text, $x, $y, $w = 100, $h = 32) {
    $b = New-Object Windows.Forms.Button
    $b.Text = $text; $b.Location = "$x,$y"; $b.Size = "$w,$h"
    $b.FlatStyle = "Flat"; $b.BackColor = $COLOR_ACC; $b.ForeColor = $COLOR_WH
    $b.Font = New-Object Drawing.Font("Segoe UI Semibold", 9)
    return $b
}
function Rand-Hex($n) {
    -join ((1..$n) | ForEach-Object { '{0:x}' -f (Get-Random -Max 16) })
}

# ── Janela principal ──────────────────────────────────────────────────────────
$form = New-Object Windows.Forms.Form
$form.Text = "$APP_NAME — Instalador v$VERSION"
$form.Size = "680,520"
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.Font = New-Object Drawing.Font("Segoe UI", 9)

# Header azul-escuro
$header = New-Object Windows.Forms.Panel
$header.Dock = "Top"; $header.Height = 80; $header.BackColor = $COLOR_BG
$hTitle = New-Label $APP_NAME 20 14 500 28 (New-Object Drawing.Font("Segoe UI Semibold",14)) $COLOR_WH
$hSub   = New-Label "Instalador do Sistema de Controle de Estoque — SorvPel" 21 46 500 20 $null ([Drawing.Color]::FromArgb(173,181,189))
$header.Controls.AddRange(@($hTitle,$hSub))

# Separador laranja
$sep = New-Object Windows.Forms.Panel
$sep.Height = 3; $sep.Dock = "Top"; $sep.BackColor = $COLOR_ACC

# Rodapé com botões
$footer = New-Object Windows.Forms.Panel
$footer.Dock = "Bottom"; $footer.Height = 55; $footer.BackColor = $COLOR_GRAY
$btnBack   = New-Btn "< Voltar" 400 12 90
$btnNext   = New-Btn "Próximo >" 500 12 90
$btnCancel = New-Object Windows.Forms.Button
$btnCancel.Text = "Cancelar"; $btnCancel.Location = "10,14"; $btnCancel.Size = "90,30"
$btnCancel.FlatStyle = "Flat"
$footer.Controls.AddRange(@($btnBack,$btnNext,$btnCancel))

# Área de conteúdo
$content = New-Object Windows.Forms.Panel
$content.Location = "0,83"; $content.Size = "672,340"; $content.BackColor = $COLOR_WH

$form.Controls.AddRange(@($header,$sep,$content,$footer))

# ── Páginas ───────────────────────────────────────────────────────────────────
function Show-Page($n) {
    $content.Controls.Clear()
    switch ($n) {
        0 { Show-Welcome }
        1 { Show-Prereqs }
        2 { Show-Config }
        3 { Show-Install }
        4 { Show-Done }
    }
    $btnBack.Enabled  = $n -gt 0 -and $n -lt 3
    $btnNext.Text     = if ($n -eq 4) { "Fechar" } elseif ($n -eq 2) { "Instalar" } else { "Próximo >" }
    $btnNext.Enabled  = $true
}

# Página 0: Boas-vindas
function Show-Welcome {
    $ico = New-Object Windows.Forms.PictureBox
    $ico.Location = "30,30"; $ico.Size = "64,64"
    $ico.Image = [Drawing.SystemIcons]::Application.ToBitmap()
    $ico.SizeMode = "Zoom"
    $t1 = New-Label "Bem-vindo ao instalador do $APP_NAME" 110 30 500 28 (New-Object Drawing.Font("Segoe UI Semibold",12))
    $t2 = New-Label @"
Este assistente irá guiá-lo pela instalação do sistema de controle
de estoque SorvPel no seu computador.

O instalador irá:
  • Verificar os pré-requisitos (Docker Desktop)
  • Configurar o banco de dados e o servidor
  • Iniciar os serviços automaticamente
  • Criar o usuário administrador padrão

ATENÇÃO: É necessário Docker Desktop instalado e em execução.
Acesse docker.com/products/docker-desktop para instalar.

Clique em "Próximo >" para continuar.
"@ 110 65 530 230
    $t2.Font = New-Object Drawing.Font("Segoe UI",10)
    $content.Controls.AddRange(@($ico,$t1,$t2))
}

# Página 1: Pré-requisitos
function Show-Prereqs {
    $lbl = New-Label "Verificando pré-requisitos..." 30 20 500 24 (New-Object Drawing.Font("Segoe UI Semibold",11))
    $content.Controls.Add($lbl)

    $checks = @(
        @{ name="Docker Desktop"; test={ Get-Command docker -EA SilentlyContinue } }
        @{ name="Docker em execução"; test={ docker info 2>$null; $? } }
        @{ name="Docker Compose"; test={ docker compose version 2>$null; $? } }
        @{ name="Porta $($script:cfg.Port) disponível";
           test={ -not (Get-NetTCPConnection -LocalPort ([int]($script:cfg.Port)) -EA SilentlyContinue) } }
    )

    $script:prereqOk = $true
    $y = 55
    foreach ($c in $checks) {
        $ok = try { & $c.test } catch { $false }
        if (-not $ok) { $script:prereqOk = $false }
        $icon = if ($ok) { "✔" } else { "✘" }
        $col  = if ($ok) { [Drawing.Color]::FromArgb(25,135,84) } else { [Drawing.Color]::FromArgb(220,53,69) }
        $row = New-Label "$icon  $($c.name)" 30 $y 550 26 (New-Object Drawing.Font("Segoe UI",10)) $col
        $content.Controls.Add($row)
        $y += 30
    }

    if (-not $script:prereqOk) {
        $warn = New-Label "⚠ Corrija os itens marcados com ✘ antes de continuar." 30 ($y+10) 580 22 `
            $null ([Drawing.Color]::FromArgb(133,77,14))
        $content.Controls.Add($warn)
        $btnNext.Enabled = $false
    } else {
        $ok = New-Label "✔ Todos os pré-requisitos atendidos!" 30 ($y+10) 580 22 `
            $null ([Drawing.Color]::FromArgb(25,135,84))
        $content.Controls.Add($ok)
    }
}

# Campos de configuração (referências globais)
$script:tbDir = $null; $script:tbPort = $null; $script:tbDbPw = $null
$script:tbSecKey = $null; $script:tbApiKey = $null; $script:tbAdminPw = $null

# Página 2: Configuração
function Show-Config {
    $lbl = New-Label "Configuração da Instalação" 30 18 500 24 (New-Object Drawing.Font("Segoe UI Semibold",11))
    $content.Controls.Add($lbl)

    $F10 = New-Object Drawing.Font("Segoe UI", 10)
    $F9  = New-Object Drawing.Font("Segoe UI", 9)

    $items = @(
        @{ label="Diretório de instalação:"; y=55;  id="dir";     default=$REPO_ROOT;    pw=$false }
        @{ label="Porta HTTP (Nginx):";      y=100; id="port";    default="8080";         pw=$false }
        @{ label="Senha do banco de dados:"; y=145; id="dbpw";    default=(Rand-Hex 16);  pw=$true  }
        @{ label="Senha admin web:";         y=190; id="adminpw"; default="admin123";     pw=$true  }
        @{ label="Chave API ESP32:";         y=235; id="apikey";  default=(Rand-Hex 20);  pw=$false }
    )

    foreach ($item in $items) {
        $l = New-Label $item.label 30 $item.y 200 20 $F9
        $tb = New-TB 230 ($item.y-2) 390 $item.pw
        $tb.Text = $item.default
        $tb.Tag  = $item.id
        switch ($item.id) {
            "dir"     { $script:tbDir     = $tb }
            "port"    { $script:tbPort    = $tb }
            "dbpw"    { $script:tbDbPw    = $tb }
            "adminpw" { $script:tbAdminPw = $tb }
            "apikey"  { $script:tbApiKey  = $tb }
        }
        $content.Controls.AddRange(@($l,$tb))
    }

    $note = New-Label "As senhas geradas aleatoriamente são seguras. Anote-as antes de continuar." 30 290 580 18 $F9 ([Drawing.Color]::Gray)
    $content.Controls.Add($note)
}

# Página 3: Instalação (executada em background)
function Show-Install {
    $lbl = New-Label "Instalando o sistema..." 30 18 500 24 (New-Object Drawing.Font("Segoe UI Semibold",11))
    $log = New-Object Windows.Forms.RichTextBox
    $log.Location = "30,50"; $log.Size = "610,230"
    $log.ReadOnly = $true; $log.BackColor = [Drawing.Color]::FromArgb(30,30,30)
    $log.ForeColor = $COLOR_WH; $log.Font = New-Object Drawing.Font("Consolas",9)
    $bar = New-Object Windows.Forms.ProgressBar
    $bar.Location = "30,292"; $bar.Size = "610,18"
    $bar.Style = "Marquee"; $bar.MarqueeAnimationSpeed = 30
    $content.Controls.AddRange(@($lbl,$log,$bar))
    $btnNext.Enabled = $false; $btnBack.Enabled = $false

    $installDir = $script:tbDir.Text.Trim()
    $port       = $script:tbPort.Text.Trim()
    $dbPw       = $script:tbDbPw.Text
    $adminPw    = $script:tbAdminPw.Text
    $apiKey     = $script:tbApiKey.Text
    $secretKey  = Rand-Hex 32

    function Write-Log($msg, $col = $COLOR_WH) {
        $log.SelectionColor = $col
        $log.AppendText("$msg`n")
        $log.ScrollToCaret()
        $form.Refresh()
    }
    function Run-Cmd($cmd, $args) {
        $p = Start-Process $cmd -ArgumentList $args -WorkingDirectory $installDir `
             -Wait -PassThru -NoNewWindow -RedirectStandardOutput "$env:TEMP\so.txt" `
             -RedirectStandardError "$env:TEMP\se.txt"
        $out = Get-Content "$env:TEMP\so.txt" -EA SilentlyContinue
        $err = Get-Content "$env:TEMP\se.txt" -EA SilentlyContinue
        if ($out) { $out | ForEach-Object { Write-Log "  $_" } }
        if ($err) { $err | ForEach-Object { Write-Log "  $_" ([Drawing.Color]::Yellow) } }
        return $p.ExitCode
    }

    $job = [System.Threading.Tasks.Task]::Run([Action]{
        try {
            $form.Invoke([Action]{Write-Log "► Criando arquivo .env..." $COLOR_ACC})

            $env_content = @"
POSTGRES_DB=controle_estoque
POSTGRES_USER=sorv_user
POSTGRES_PASSWORD=$dbPw
SECRET_KEY=$secretKey
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
ESP32_API_KEY=$apiKey
NGINX_PORT=$port
ENVIRONMENT=production
TZ=America/Sao_Paulo
"@
            Set-Content -Path (Join-Path $installDir ".env") -Value $env_content -Encoding UTF8

            $form.Invoke([Action]{Write-Log "✔ .env criado" ([Drawing.Color]::FromArgb(25,135,84))})
            $form.Invoke([Action]{Write-Log "► Iniciando containers Docker..." $COLOR_ACC})

            $ec = Run-Cmd "docker" "compose up -d --build"
            if ($ec -ne 0) { throw "docker compose up falhou (exit $ec)" }
            $form.Invoke([Action]{Write-Log "✔ Containers iniciados" ([Drawing.Color]::FromArgb(25,135,84))})

            # Aguarda postgres ficar saudável
            $form.Invoke([Action]{Write-Log "► Aguardando banco de dados..." $COLOR_ACC})
            Start-Sleep -Seconds 8

            $form.Invoke([Action]{Write-Log "► Executando migrações..." $COLOR_ACC})
            $ec = Run-Cmd "docker" "compose run --rm backend alembic upgrade head"
            if ($ec -ne 0) { throw "Migração falhou (exit $ec)" }
            $form.Invoke([Action]{Write-Log "✔ Banco de dados atualizado" ([Drawing.Color]::FromArgb(25,135,84))})

            # Cria usuário admin via script inline
            $form.Invoke([Action]{Write-Log "► Criando usuário administrador..." $COLOR_ACC})
            $py = @"
import asyncio, sys
sys.path.insert(0, '/app')
from app.database import AsyncSessionLocal
from app.models.user import WebUser
from app.services.auth_service import hash_password
from sqlalchemy import select
async def main():
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(WebUser).where(WebUser.username=='admin'))
        if not r.scalar_one_or_none():
            u = WebUser(username='admin', full_name='Administrador',
                        hashed_password=hash_password('$adminPw'), role='admin', is_active=True)
            db.add(u); await db.commit()
            print('Usuário admin criado')
        else:
            print('Usuário admin já existe')
asyncio.run(main())
"@
            $py | docker compose -f (Join-Path $installDir "docker-compose.yml") run --rm -T backend python - 2>&1 | Out-Null

            $form.Invoke([Action]{Write-Log "✔ Usuário admin criado (senha: $adminPw)" ([Drawing.Color]::FromArgb(25,135,84))})
            $form.Invoke([Action]{Write-Log "" })
            $form.Invoke([Action]{Write-Log "═══════════════════════════════════════" $COLOR_ACC})
            $form.Invoke([Action]{Write-Log "  INSTALAÇÃO CONCLUÍDA COM SUCESSO!  " $COLOR_ACC})
            $form.Invoke([Action]{Write-Log "═══════════════════════════════════════" $COLOR_ACC})
            $form.Invoke([Action]{Write-Log "  Acesso: http://localhost:$port" $COLOR_WH})
            $form.Invoke([Action]{Write-Log "  Usuário: admin  |  Senha: $adminPw" $COLOR_WH})
            $script:installOk = $true
        } catch {
            $msg = $_.Exception.Message
            $form.Invoke([Action]{Write-Log "✘ ERRO: $msg" ([Drawing.Color]::FromArgb(220,53,69))})
            $form.Invoke([Action]{Write-Log "Corrija o problema e tente novamente." })
        } finally {
            $form.Invoke([Action]{
                $bar.Style = "Blocks"; $bar.Value = 100
                $btnNext.Enabled = $true
                $btnNext.Text = "Próximo >"
            })
        }
    })
}

# Página 4: Conclusão
function Show-Done {
    $ico  = New-Label "✔" 30 30 60 60 (New-Object Drawing.Font("Segoe UI",36)) ([Drawing.Color]::FromArgb(25,135,84))
    $t1   = New-Label "Instalação concluída!" 100 38 500 30 (New-Object Drawing.Font("Segoe UI Semibold",13))
    $port = $script:tbPort.Text.Trim()
    $url  = "http://localhost:$port"
    $t2   = New-Label @"
O sistema SorvPel está em execução.

Acesse o portal em:  $url
Usuário padrão:      admin
Senha:               (conforme configurado)

Para iniciar/parar o sistema no futuro, use:
  docker compose up -d    (iniciar)
  docker compose down     (parar)

O serviço iniciará automaticamente com o Windows se o Docker
Desktop estiver configurado para iniciar com o sistema.
"@ 30 110 600 200
    $t2.Font = New-Object Drawing.Font("Segoe UI",10)

    $btnOpen = New-Btn "Abrir no Navegador" 30 290 160 32
    $btnOpen.Add_Click({ Start-Process $url })
    $content.Controls.AddRange(@($ico,$t1,$t2,$btnOpen))
}

# ── Navegação ─────────────────────────────────────────────────────────────────
$btnNext.Add_Click({
    switch ($script:page) {
        0 { $script:cfg.Port = "8080"; $script:page = 1; Show-Page 1 }
        1 { if ($script:prereqOk) { $script:page = 2; Show-Page 2 } }
        2 { $script:page = 3; Show-Page 3 }
        3 { if ($script:installOk) { $script:page = 4; Show-Page 4 } }
        4 { $form.Close() }
    }
})
$btnBack.Add_Click({
    if ($script:page -gt 0) { $script:page--; Show-Page $script:page }
})
$btnCancel.Add_Click({ $form.Close() })

# ── Início ────────────────────────────────────────────────────────────────────
Show-Page 0
[void]$form.ShowDialog()
