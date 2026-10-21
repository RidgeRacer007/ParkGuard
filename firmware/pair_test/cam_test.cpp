#include <WiFi.h>
#include <WebServer.h>

// Camera bring-up only: validates the ESP32-CAM board and Wi-Fi link first.
// OV5640 capture is deliberately added after this connection test passes.
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
