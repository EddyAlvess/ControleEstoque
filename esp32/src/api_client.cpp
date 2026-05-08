#include "api_client.h"
#include "config.h"
#include <time.h>

ApiClient apiClient;

// ─── ISRG Root X1 (Let's Encrypt) ───────────────────────────────────────────
// Necessário apenas com USE_HTTPS. Baixe o PEM em:
//   https://letsencrypt.org/certs/isrgrootx1.pem
// e substitua o conteúdo abaixo se o certificado for atualizado (válido até 2035).
#ifdef USE_HTTPS
const char ISRG_ROOT_X1[] = R"(
-----BEGIN CERTIFICATE-----
MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRGPgu2OCiwAwDQYJKoZIhvcNAQELBQAw
TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh
cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMTUwNjA0MTEwNDM4
WhcNMzUwNjA0MTEwNDM4WjBPMQswCQYDVQQGEwJVUzEpMCcGA1UEChMgSW50ZXJu
ZXQgU2VjdXJpdHkgUmVzZWFyY2ggR3JvdXAxFTATBgNVBAMTDElTUkcgUm9vdCBY
MTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoBggIBAK3oJHP0FDfzm54rVygc
h77ct984kIxuPOZXoHj3dcKi/vVqbvYATyjb3miGbESTtrFj/RQSa78f0uoxmyF+
0TM8ukj13Xnfs7j/EvEhmkvBioZxaUpmZmyPfjxwv60pIgbz5MDmgK7iS4+3mX6U
A5/TR5d8mUgjU+g4rk8Kb4Mu0UlXjIB0ttov0DiNewNwIRt18jA8+o+u3dpjq+sW
T8KOEUt+zwvo/7V3LvSye0rgTBIlDHCNAymg4VMk7BPZ7hm/ELNKjD+Jo2FR3qyH
B5T0Y3HsLuJvW5iB4YlcNHlsdu87kGJ55tukmi8mxdAQ4Q7e2RCOFvu396j3x+UC
B5iPNgiV5+I3lg02dZ77DnKxHZu8A/lJBdiB3QW0KtZB6awBdpUKD9jf1b0SHzUv
KBds0pjBqAlkd25HN7rOrFleaJ1/ctaJxQZBKT5ZPt0m9STJEadao0xAH0ahmbWn
OlFuhjuefXKnEgV4We0+UXgVCwOPjdAvBbI+e0ocS3MFEvzG6uBQE3xDk3SzynTn
jh8BCNAw1FtxNrQHusEwMFxIt4I7mKZ9YIqioymCzLq9gwQbooMDQaHWBfEbwrbw
qHyGO0aoSCqI3Haadr8faqU9GY/rOPNk3sgrDQoo//fb4hVCiSBJnrmqO0BAQIA
nAVuBJ6O+KlE47hzqL5z7bKXe3rMqIx6JbHSvHNSh+2PJbGN8M8/jSBZJ7LBDQN
PBBQQBJbBBPKM72KjwQH1SiQAWQ88jQi5TEOQ0o5OHVhJKkGHPyCqjgAAuqzRRKJ
TbGjGNBFMidJGMI=
-----END CERTIFICATE-----
)";
#endif

// ─── Helpers ─────────────────────────────────────────────────────────────────

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

// Inicia HTTPClient para HTTP ou HTTPS conforme USE_HTTPS.
// Retorna false se url inválida. Caller deve chamar http.end() após uso.
static bool beginRequest(HTTPClient& http, WiFiClient& plain,
#ifdef USE_HTTPS
                         WiFiClientSecure& ssl,
#endif
                         const String& url) {
#ifdef USE_HTTPS
    ssl.setCACert(ISRG_ROOT_X1);
    if (!http.begin(ssl, url)) return false;
#else
    if (!http.begin(plain, url)) return false;
#endif
    http.addHeader("X-API-Key", API_KEY);
    http.setTimeout(HTTP_TIMEOUT_MS);
    return true;
}

// ─── API calls ───────────────────────────────────────────────────────────────

bool ApiClient::fetchOperators(Operator* out, int* count, int maxCount) {
    HTTPClient http;
    WiFiClient plain;
#ifdef USE_HTTPS
    WiFiClientSecure ssl;
#endif
    String url = String(SERVER_URL) + "/api/v1/operators";
    if (!beginRequest(http, plain,
#ifdef USE_HTTPS
                      ssl,
#endif
                      url)) return false;

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
    WiFiClient plain;
#ifdef USE_HTTPS
    WiFiClientSecure ssl;
#endif
    String url = String(SERVER_URL) + "/api/v1/products";
    if (!beginRequest(http, plain,
#ifdef USE_HTTPS
                      ssl,
#endif
                      url)) return false;

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
    WiFiClient plain;
#ifdef USE_HTTPS
    WiFiClientSecure ssl;
#endif
    String url = String(SERVER_URL) + "/api/v1/movements";
    if (!beginRequest(http, plain,
#ifdef USE_HTTPS
                      ssl,
#endif
                      url)) return false;

    http.addHeader("Content-Type", "application/json");

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
    WiFiClient plain;
#ifdef USE_HTTPS
    WiFiClientSecure ssl;
#endif
    String url = String(SERVER_URL) + "/api/v1/ota/version";
    if (!beginRequest(http, plain,
#ifdef USE_HTTPS
                      ssl,
#endif
                      url)) return false;

    int code = http.GET();
    if (code != 200) { http.end(); return false; }

    JsonDocument doc;
    deserializeJson(doc, http.getStream());
    http.end();

    serverVersion = doc["version"].as<String>();
    return doc["available"].as<bool>();
}
