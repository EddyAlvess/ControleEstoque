#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>

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
