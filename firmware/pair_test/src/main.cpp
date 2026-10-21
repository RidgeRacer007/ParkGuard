#if defined(PARKGUARD_CAM)
#include <WiFi.h>
#include <WebServer.h>

static const char *AP_SSID = "ParkGuard-CAM";
static const char *AP_PASSWORD = "parkguard123";
WebServer server(80);

void setup() {
  Serial.begin(115200);
  delay(500);
  WiFi.mode(WIFI_AP);
  bool started = WiFi.softAP(AP_SSID, AP_PASSWORD);
  Serial.println(started ? "ESP32-CAM access point ready" : "Access point start failed");
  Serial.print("Connect DevKit to SSID: ");
  Serial.println(AP_SSID);
  Serial.print("Camera health URL: http://");
  Serial.println(WiFi.softAPIP());
  server.on("/", HTTP_GET, []() {
    server.send(200, "text/plain", "ParkGuard ESP32-CAM test node is online");
  });
  server.on("/health", HTTP_GET, []() {
    server.send(200, "application/json", "{\"node\":\"esp32-cam\",\"status\":\"online\"}");
  });
  server.begin();
}

void loop() {
  server.handleClient();
}
#else
#include <WiFi.h>
#include <HTTPClient.h>

static const char *CAM_SSID = "ParkGuard-CAM";
static const char *CAM_PASSWORD = "parkguard123";
static const char *CAM_HEALTH_URL = "http://192.168.4.1/health";
static unsigned long lastCheck = 0;

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("ParkGuard pair test: DevKit joining ESP32-CAM access point");
  WiFi.mode(WIFI_STA);
  WiFi.begin(CAM_SSID, CAM_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print('.');
  }
  Serial.println();
  Serial.print("Connected. DevKit IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.reconnect();
    delay(500);
    return;
  }
  if (millis() - lastCheck < 5000) return;
  lastCheck = millis();
  HTTPClient http;
  if (!http.begin(CAM_HEALTH_URL)) {
    Serial.println("Could not start HTTP request");
    return;
  }
  int status = http.GET();
  Serial.printf("Camera health HTTP status: %d\n", status);
  if (status > 0) Serial.println(http.getString());
  http.end();
}
#endif
