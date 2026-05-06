#include "ota_updater.h"
#include "config.h"
#include "api_client.h"
#include "display.h"
#include <ArduinoOTA.h>
#include <HTTPClient.h>
#include <Update.h>

OtaUpdater otaUpdater;

void OtaUpdater::beginArduinoOTA() {
    ArduinoOTA.setHostname(DEVICE_ID);
    ArduinoOTA.onStart([]() { display.showTwoLines("OTA: iniciando", "Nao desligue!"); });
    ArduinoOTA.onProgress([](unsigned int p, unsigned int t) {
        display.showTwoLines("Atualizando...", String(p * 100 / t) + "%");
    });
    ArduinoOTA.onEnd([]() { display.showTwoLines("OTA concluido", "Reiniciando..."); });
    ArduinoOTA.onError([](ota_error_t e) {
        display.showTwoLines("Erro OTA", String(e));
    });
    ArduinoOTA.begin();
}

bool OtaUpdater::checkAndApply() {
#if OTA_CHECK_ON_BOOT
    String serverVer;
    if (!apiClient.checkOtaVersion(serverVer)) return false;
    if (serverVer == FIRMWARE_VER) return false;

    display.showTwoLines("Nova versao:", serverVer);
    delay(2000);
    display.showProgress("Baixando...");

    HTTPClient http;
    String url = String(SERVER_URL) + "/api/v1/ota/firmware.bin";
    http.begin(url);
    http.addHeader("X-API-Key", API_KEY);
    http.setTimeout(30000);

    int code = http.GET();
    if (code != 200) { http.end(); return false; }

    int size = http.getSize();
    if (!Update.begin(size)) { http.end(); return false; }

    WiFiClient* stream = http.getStreamPtr();
    size_t written = Update.writeStream(*stream);
    http.end();

    if (written != (size_t)size || !Update.end()) return false;

    display.showTwoLines("Atualizado!", "Reiniciando...");
    delay(2000);
    ESP.restart();
#endif
    return false;
}
