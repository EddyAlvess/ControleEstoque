#pragma once
#include <Arduino.h>

class WiFiManager {
public:
    bool connect(unsigned long timeoutMs = 15000);
    bool isConnected();
    void reconnectIfNeeded();
    String getIP();
};

extern WiFiManager wifiManager;
