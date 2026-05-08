#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#ifdef USE_HTTPS
#include <WiFiClientSecure.h>
// ISRG Root X1 — CA raiz do Let's Encrypt, necessária para validar HTTPS.
// Fonte: https://letsencrypt.org/certs/isrgrootx1.pem
extern const char ISRG_ROOT_X1[];
#endif

struct Operator {
    int    id;
    String name;
    String badge_code;
};

struct Product {
    int    id;
    String name;
    String unit;
};

class ApiClient {
public:
    bool fetchOperators(Operator* out, int* count, int maxCount);
    bool fetchProducts(Product* out, int* count, int maxCount);
    bool postMovement(const char* type, int operatorId, int productId,
                      float quantity, const char* shift);
    bool checkOtaVersion(String& serverVersion);
};

extern ApiClient apiClient;
