#pragma once

// ─── WiFi ────────────────────────────────────────────────────────────────────
#define WIFI_SSID     "SUA_REDE_WIFI"
#define WIFI_PASSWORD "SUA_SENHA_WIFI"

// ─── Servidor ────────────────────────────────────────────────────────────────
// Exemplo local: "http://192.168.1.100"  |  Cloud: "https://estoque.suaempresa.com"
#define SERVER_URL    "http://192.168.1.100"
#define API_KEY       "COLE_AQUI_A_ESP32_API_KEY_DO_ENV"

// ─── Identificação do terminal ───────────────────────────────────────────────
#define DEVICE_ID     "ESP32-LINHA-A"
#define FIRMWARE_VER  "1.0.0"

// ─── Display LCD 16x2 I2C ────────────────────────────────────────────────────
#define LCD_I2C_ADDR  0x27
#define LCD_COLS      16
#define LCD_ROWS      2

// ─── Teclado matricial 4x4 ───────────────────────────────────────────────────
// Pinos de linha e coluna do teclado 4x4
// Ajuste conforme sua fiação
#define KP_ROW1 13
#define KP_ROW2 12
#define KP_ROW3 14
#define KP_ROW4 27
#define KP_COL1 26
#define KP_COL2 25
#define KP_COL3 33
#define KP_COL4 32

// ─── Scanner serial (opcional) ───────────────────────────────────────────────
// Para habilitar scanner de código de barras via UART:
//   #define SCANNER_ENABLED
//   O scanner deve ser conectado ao Serial2 (RX=16, TX=17)
// #define SCANNER_ENABLED
#define SCANNER_RX_PIN 16
#define SCANNER_TX_PIN 17
#define SCANNER_BAUD   9600

// ─── OTA ─────────────────────────────────────────────────────────────────────
#define OTA_CHECK_ON_BOOT true

// ─── Timeouts (ms) ───────────────────────────────────────────────────────────
#define HTTP_TIMEOUT_MS  8000
#define WIFI_TIMEOUT_MS  15000
#define MENU_IDLE_MS     60000   // volta ao início após 60s sem atividade
