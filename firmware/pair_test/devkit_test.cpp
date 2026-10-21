#include <WiFi.h>
#include <HTTPClient.h>

// This first-stage test uses the camera board's local Wi-Fi access point.
// No home Wi-Fi credentials, sensors, cloud API, or camera pin map are needed.
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
