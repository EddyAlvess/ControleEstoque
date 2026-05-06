#pragma once
#include <Arduino.h>

class OtaUpdater {
public:
    void beginArduinoOTA();     // OTA push via PlatformIO/IDE
    bool checkAndApply();       // OTA pull do servidor (verifica versão e aplica)
};

extern OtaUpdater otaUpdater;
