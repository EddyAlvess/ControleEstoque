#include <Arduino.h>
#include <time.h>
#include "config.h"
#include "wifi_manager.h"
#include "display.h"
#include "keypad.h"
#include "scanner.h"
#include "api_client.h"
#include "menu.h"
#include "ota_updater.h"

static Operator operators[32];
static Product  products[64];
static int      opCount   = 0;
static int      prodCount = 0;

void setup() {
    Serial.begin(115200);

    display.begin();
    display.showTwoLines("SorvPel Estoque", "Iniciando...");

    // WiFi
    display.showTwoLines("Conectando WiFi", WIFI_SSID);
    if (!wifiManager.connect(WIFI_TIMEOUT_MS)) {
        display.showTwoLines("Erro WiFi!", "Verifique config");
        delay(5000);
        ESP.restart();
    }
    display.showTwoLines("WiFi OK", wifiManager.getIP());
    delay(1000);

    // Sincronizar relógio via NTP
    configTime(-3 * 3600, 0, "pool.ntp.org", "time.google.com");
    display.showProgress("Sincron. relogio");
    unsigned long ntpStart = millis();
    while (time(nullptr) < 100000 && millis() - ntpStart < 10000) delay(100);

    // OTA check ao iniciar
    display.showProgress("Verificando OTA");
    otaUpdater.checkAndApply();  // pode reiniciar aqui se houver update

    // ArduinoOTA (push via PlatformIO)
    otaUpdater.beginArduinoOTA();

    // Carregar dados do servidor
    display.showProgress("Carregando dados");
    if (!apiClient.fetchOperators(operators, &opCount, 32)) {
        display.showTwoLines("Erro: servidor", "indisponivel");
        delay(3000);
    }
    if (!apiClient.fetchProducts(products, &prodCount, 64)) {
        display.showTwoLines("Erro: produtos", "indisponivel");
        delay(3000);
    }

    display.showTwoLines("Carregado!", String(opCount) + " op " + String(prodCount) + " prod");
    delay(1500);

    keypadInput.begin();
    scanner.begin();
    menu.begin(operators, opCount, products, prodCount);
}

void loop() {
    ArduinoOTA.handle();
    wifiManager.reconnectIfNeeded();

    // Scanner tem prioridade sobre teclado
    if (scanner.available()) {
        String code = scanner.read();
        menu.handleScanner(code);
        menu.render();
    } else {
        char key = keypadInput.read();
        if (key != '\0') menu.handleKey(key);
        menu.render();
    }

    delay(50);
}
