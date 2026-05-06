#pragma once
// Scanner de código de barras via UART (Serial2)
// Para habilitar: descomente #define SCANNER_ENABLED em config.h

#include <Arduino.h>

class BarcodeScanner {
public:
    void begin();
    bool available();       // retorna true se há código disponível
    String read();          // retorna o código escaneado
};

extern BarcodeScanner scanner;
