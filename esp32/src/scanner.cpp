#include "scanner.h"
#include "config.h"

BarcodeScanner scanner;
static String _buf = "";

void BarcodeScanner::begin() {
#ifdef SCANNER_ENABLED
    Serial2.begin(SCANNER_BAUD, SERIAL_8N1, SCANNER_RX_PIN, SCANNER_TX_PIN);
#endif
}

bool BarcodeScanner::available() {
#ifdef SCANNER_ENABLED
    while (Serial2.available()) {
        char c = Serial2.read();
        if (c == '\n' || c == '\r') {
            if (_buf.length() > 0) return true;
        } else {
            _buf += c;
        }
    }
#endif
    return false;
}

String BarcodeScanner::read() {
    String result = _buf;
    _buf = "";
    return result;
}
