#include "api_client.h"
#include "config.h"
#include <HTTPClient.h>
#include <time.h>

ApiClient apiClient;

static String getTimestamp() {
    time_t now = time(nullptr);
    struct tm t;
    localtime_r(&now, &t);
    char buf[32];
    snprintf(buf, sizeof(buf), "%04d-%02d-%02dT%02d:%02d:%02d",
             t.tm_year + 1900, t.tm_mon + 1, t.tm_mday,
             t.tm_hour, t.tm_min, t.tm_sec);
    return String(buf);
}

static const char* currentShift() {
    time_t now = time(nullptr);
    struct tm t;
    localtime_r(&now, &t);
    if (t.tm_hour >= 6 && t.tm_hour < 14)  return "MORNING";
    if (t.tm_hour >= 14 && t.tm_hour < 22) return "AFTERNOON";
    return "NIGHT";
}

bool ApiClient::fetchOperators(Operator* out, int* count, int maxCount) {
    HTTPClient http;
    String url = String(SERVER_URL) + "/api/v1/operators";
    http.begin(url);
    http.addHeader("X-API-Key", API_KEY);
    http.setTimeout(HTTP_TIMEOUT_MS);

    int code = http.GET();
    if (code != 200) { http.end(); return false; }

    JsonDocument doc;
    deserializeJson(doc, http.getStream());
    http.end();

    *count = 0;
    for (JsonObject obj : doc.as<JsonArray>()) {
        if (*count >= maxCount) break;
        out[*count].id         = obj["id"];
        out[*count].name       = obj["name"].as<String>();
        out[*count].badge_code = obj["badge_code"].as<String>();
        (*count)++;
    }
    return true;
}

bool ApiClient::fetchProducts(Product* out, int* count, int maxCount) {
    HTTPClient http;
    String url = String(SERVER_URL) + "/api/v1/products";
    http.begin(url);
    http.addHeader("X-API-Key", API_KEY);
    http.setTimeout(HTTP_TIMEOUT_MS);

    int code = http.GET();
    if (code != 200) { http.end(); return false; }

    JsonDocument doc;
    deserializeJson(doc, http.getStream());
    http.end();

    *count = 0;
    for (JsonObject obj : doc.as<JsonArray>()) {
        if (*count >= maxCount) break;
        out[*count].id   = obj["id"];
        out[*count].name = obj["name"].as<String>();
        out[*count].unit = obj["unit"].as<String>();
        (*count)++;
    }
    return true;
}

bool ApiClient::postMovement(const char* type, int operatorId, int productId,
                             float quantity, const char* shift) {
    HTTPClient http;
    String url = String(SERVER_URL) + "/api/v1/movements";
    http.begin(url);
    http.addHeader("X-API-Key", API_KEY);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(HTTP_TIMEOUT_MS);

    JsonDocument doc;
    doc["movement_type"] = type;
    doc["operator_id"]   = operatorId;
    doc["product_id"]    = productId;
    doc["quantity"]      = quantity;
    doc["shift"]         = shift ? shift : currentShift();
    doc["device_id"]     = DEVICE_ID;
    doc["recorded_at"]   = getTimestamp();

    String body;
    serializeJson(doc, body);

    int code = http.POST(body);
    http.end();
    return code == 201;
}

bool ApiClient::checkOtaVersion(String& serverVersion) {
    HTTPClient http;
    String url = String(SERVER_URL) + "/api/v1/ota/version";
    http.begin(url);
    http.addHeader("X-API-Key", API_KEY);
    http.setTimeout(HTTP_TIMEOUT_MS);

    int code = http.GET();
    if (code != 200) { http.end(); return false; }

    JsonDocument doc;
    deserializeJson(doc, http.getStream());
    http.end();

    serverVersion = doc["version"].as<String>();
    return doc["available"].as<bool>();
}
