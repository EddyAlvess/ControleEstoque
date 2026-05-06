#include "wifi_manager.h"
#include "config.h"
#include <WiFi.h>

WiFiManager wifiManager;

bool WiFiManager::connect(unsigned long timeoutMs) {
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < timeoutMs) {
        delay(500);
    }
    return WiFi.status() == WL_CONNECTED;
}

bool WiFiManager::isConnected() {
    return WiFi.status() == WL_CONNECTED;
}

void WiFiManager::reconnectIfNeeded() {
    if (!isConnected()) {
        WiFi.reconnect();
    }
}

String WiFiManager::getIP() {
    return WiFi.localIP().toString();
}
