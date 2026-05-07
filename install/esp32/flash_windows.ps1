#Requires -Version 5.1
<#
.SYNOPSIS
    SorvPel — Gravador de Firmware ESP32 (Windows)
.DESCRIPTION
    Detecta a porta COM, configura o firmware e grava via PlatformIO.
    Execute a partir do diretório raiz do projeto.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$REPO_ROOT = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$ESP32_DIR = Join-Path $REPO_ROOT "esp32"
$CONFIG_H  = Join-Path $ESP32_DIR "src\config.h"

# ── Helpers ───────────────────────────────────────────────────────────────────
function Get-ComPorts {
    Get-WmiObject Win32_PnPEntity |
        Where-Object { $_.Caption -match 'COM\d+' } |
        ForEach-Object {
            if ($_.Caption -match 'COM(\d+)') {
                [PSCustomObject]@{ Port = "COM$($Matches[1])"; Name = $_.Caption }
            }
        } | Sort-Object Port
}

function Check-Pio {
    if (Get-Command pio -EA SilentlyContinue) { return $true }
    if (Get-Command platformio -EA SilentlyContinue) { return $true }
    # Procura em paths comuns
    $paths = @(
        "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe",
        "$env:LOCALAPPDATA\platformio\penv\Scripts\pio.exe"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) { $env:PATH += ";$(Split-Path $p)"; return $true }
    }
    return $false
}

function Install-Pio {
    $pyCmd = Get-Command python -EA SilentlyContinue
    if (-not $pyCmd) { $pyCmd = Get-Command python3 -EA SilentlyContinue }
    if (-not $pyCmd) {
        [Windows.Forms.MessageBox]::Show(
            "Python não encontrado.`nInstale Python 3.8+ em python.org e execute novamente.",
            "Pré-requisito", "OK", "Error") | Out-Null
        exit 1
    }
    & $pyCmd.Source -m pip install platformio --quiet
}

# ── GUI ───────────────────────────────────────────────────────────────────────
$form = New-Object Windows.Forms.Form
$form.Text = "SorvPel — Gravador ESP32"
$form.Size = "540,480"
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false

# Header
$hdr = New-Object Windows.Forms.Panel
$hdr.Dock = "Top"; $hdr.Height = 60
$hdr.BackColor = [Drawing.Color]::FromArgb(26,26,46)
$htitle = New-Object Windows.Forms.Label
$htitle.Text = "Gravador de Firmware ESP32"; $htitle.ForeColor = [Drawing.Color]::White
$htitle.Font = New-Object Drawing.Font("Segoe UI Semibold",12)
$htitle.Location = "16,16"; $htitle.AutoSize = $true
$hdr.Controls.Add($htitle)

$main = New-Object Windows.Forms.Panel
$main.Location = "0,60"; $main.Size = "534,360"; $main.Padding = "16,16,16,0"

$F9  = New-Object Drawing.Font("Segoe UI",9)
$F10 = New-Object Drawing.Font("Segoe UI",10)
$F9B = New-Object Drawing.Font("Segoe UI Semibold",9)

# Porta COM
$lblPort = New-Object Windows.Forms.Label
$lblPort.Text = "Porta COM (ESP32):"; $lblPort.Location = "16,16"
$lblPort.Font = $F9B; $lblPort.AutoSize = $true

$cmbPort = New-Object Windows.Forms.ComboBox
$cmbPort.Location = "16,36"; $cmbPort.Width = 280; $cmbPort.Font = $F10
$cmbPort.DropDownStyle = "DropDownList"

$btnRefresh = New-Object Windows.Forms.Button
$btnRefresh.Text = "↻ Atualizar"; $btnRefresh.Location = "308,34"
$btnRefresh.Size = "100,26"; $btnRefresh.Font = $F9
$btnRefresh.Add_Click({
    $cmbPort.Items.Clear()
    $ports = Get-ComPorts
    foreach ($p in $ports) { $cmbPort.Items.Add("$($p.Port) — $($p.Name)") | Out-Null }
    if ($cmbPort.Items.Count -gt 0) { $cmbPort.SelectedIndex = 0 }
    else { [Windows.Forms.MessageBox]::Show("Nenhum dispositivo COM detectado.`nConecte o ESP32 via USB e tente novamente.","Aviso","OK","Warning")|Out-Null }
})

# Config WiFi
$sep1 = New-Object Windows.Forms.Label
$sep1.Text = "───── Configuração do Firmware ─────────────────────"
$sep1.Location = "16,76"; $sep1.Font = $F9; $sep1.ForeColor = [Drawing.Color]::Gray
$sep1.AutoSize = $true

$mkLbl = { param($t,$y) $l=New-Object Windows.Forms.Label; $l.Text=$t; $l.Location="16,$y"; $l.Font=$F9B; $l.AutoSize=$true; $l }
$mkTb  = { param($y,$w,$d) $tb=New-Object Windows.Forms.TextBox; $tb.Location="16,$y"; $tb.Width=$w; $tb.Font=$F10; $tb.Text=$d; $tb }

$lblSsid   = & $mkLbl "SSID da Rede WiFi:"  100
$tbSsid    = & $mkTb  120 380 ""
$lblWpass  = & $mkLbl "Senha do WiFi:"      152
$tbWpass   = & $mkTb  172 380 ""
$tbWpass.UseSystemPasswordChar = $true

$lblUrl    = & $mkLbl "URL do Servidor (ex: http://192.168.1.100):" 204
$tbUrl     = & $mkTb  224 380 "http://192.168.1.100"
$lblApiKey = & $mkLbl "Chave API ESP32 (do arquivo .env):" 256
$tbApiKey  = & $mkTb  276 380 ""
$lblDev    = & $mkLbl "ID do Terminal:" 308
$tbDev     = & $mkTb  328 200 "ESP32-LINHA-A"

# Port
$lblNginx  = & $mkLbl "Porta do servidor (se diferente de 80):" 256
# (não vamos duplicar — $tbUrl já tem a porta na URL)

# Log
$log = New-Object Windows.Forms.RichTextBox
$log.Location = "16,360"; $log.Size = "500,60"
$log.ReadOnly = $true; $log.BackColor = [Drawing.Color]::FromArgb(30,30,30)
$log.ForeColor = [Drawing.Color]::White; $log.Font = New-Object Drawing.Font("Consolas",8)

# Botão gravar
$btnFlash = New-Object Windows.Forms.Button
$btnFlash.Text = "▶  Gravar Firmware"
$btnFlash.Location = "320,328"; $btnFlash.Size = "196,28"
$btnFlash.BackColor = [Drawing.Color]::FromArgb(25,135,84)
$btnFlash.ForeColor = [Drawing.Color]::White
$btnFlash.Font = $F9B; $btnFlash.FlatStyle = "Flat"

$main.Controls.AddRange(@(
    $lblPort,$cmbPort,$btnRefresh,$sep1,
    $lblSsid,$tbSsid,$lblWpass,$tbWpass,
    $lblUrl,$tbUrl,$lblApiKey,$tbApiKey,
    $lblDev,$tbDev,$log,$btnFlash
))

$form.Controls.AddRange(@($hdr,$main))

# Popula portas ao iniciar
$btnRefresh.PerformClick()

# ── Flash ─────────────────────────────────────────────────────────────────────
function Write-Log($msg, $green = $false) {
    $log.SelectionColor = if ($green) { [Drawing.Color]::FromArgb(25,135,84) } else { [Drawing.Color]::White }
    $log.AppendText("$msg`n"); $log.ScrollToCaret(); $form.Refresh()
}

$btnFlash.Add_Click({
    if ($cmbPort.SelectedIndex -lt 0) {
        [Windows.Forms.MessageBox]::Show("Selecione a porta COM do ESP32.","Aviso","OK","Warning") | Out-Null; return
    }
    $portStr = ($cmbPort.SelectedItem -split " ")[0]
    if (-not (Test-Path $ESP32_DIR)) { [Windows.Forms.MessageBox]::Show("Diretório esp32 não encontrado: $ESP32_DIR","Erro","OK","Error")|Out-Null; return }
    if (-not $tbSsid.Text) { [Windows.Forms.MessageBox]::Show("Informe o SSID da rede WiFi.","Aviso","OK","Warning")|Out-Null; return }
    if (-not $tbApiKey.Text) { [Windows.Forms.MessageBox]::Show("Informe a Chave API ESP32.","Aviso","OK","Warning")|Out-Null; return }

    # Gera config_local.h
    Write-Log "Gerando configuração do firmware..."
    $configLocal = @"
#pragma once
// Gerado automaticamente pelo instalador SorvPel — NÃO versionar
#define WIFI_SSID     "$($tbSsid.Text)"
#define WIFI_PASSWORD "$($tbWpass.Text)"
#define SERVER_URL    "$($tbUrl.Text)"
#define API_KEY       "$($tbApiKey.Text)"
#define DEVICE_ID     "$($tbDev.Text)"
#define FIRMWARE_VER  "1.0.0"
"@
    Set-Content (Join-Path $ESP32_DIR "src\config_local.h") $configLocal -Encoding UTF8

    # Verifica / instala PlatformIO
    if (-not (Check-Pio)) {
        Write-Log "Instalando PlatformIO..."
        Install-Pio
    }

    $btnFlash.Enabled = $false
    $job = [System.Threading.Tasks.Task]::Run([Action]{
        try {
            $form.Invoke([Action]{ Write-Log "Compilando firmware (pode demorar ~1min na 1a vez)..." })
            $p = Start-Process pio -ArgumentList "run -t upload --upload-port $portStr" `
                -WorkingDirectory $ESP32_DIR -Wait -PassThru -NoNewWindow `
                -RedirectStandardOutput "$env:TEMP\pio_out.txt" `
                -RedirectStandardError "$env:TEMP\pio_err.txt"
            $out = (Get-Content "$env:TEMP\pio_out.txt" -EA SilentlyContinue) -join "`n"
            $err = (Get-Content "$env:TEMP\pio_err.txt" -EA SilentlyContinue) -join "`n"
            if ($p.ExitCode -eq 0) {
                $form.Invoke([Action]{ Write-Log "✔ Firmware gravado com sucesso!" $true })
            } else {
                $form.Invoke([Action]{ Write-Log "✘ Falha ao gravar. Verifique:" })
                $form.Invoke([Action]{ Write-Log "  $err" })
            }
        } catch {
            $msg = $_.Exception.Message
            $form.Invoke([Action]{ Write-Log "✘ Erro: $msg" })
        } finally {
            $form.Invoke([Action]{ $btnFlash.Enabled = $true })
        }
    })
})

[void]$form.ShowDialog()
