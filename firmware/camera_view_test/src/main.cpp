#include <WiFi.h>
#include <WebServer.h>
#include "esp_camera.h"

// AI-Thinker ESP32-CAM carrier pin map. If the OV5640 carrier uses different
// wiring, Serial Monitor will report camera init failure and this map must change.
static constexpr int CAM_PWDN = 32;
static constexpr int CAM_RESET = -1;
static constexpr int CAM_XCLK = 0;
static constexpr int CAM_SIOD = 26;
static constexpr int CAM_SIOC = 27;
static constexpr int CAM_D7 = 35;
static constexpr int CAM_D6 = 34;
static constexpr int CAM_D5 = 39;
static constexpr int CAM_D4 = 36;
static constexpr int CAM_D3 = 21;
static constexpr int CAM_D2 = 19;
static constexpr int CAM_D1 = 18;
static constexpr int CAM_D0 = 5;
static constexpr int CAM_VSYNC = 25;
static constexpr int CAM_HREF = 23;
static constexpr int CAM_PCLK = 22;

static const char *AP_SSID = "ParkGuard-CAM";
static const char *AP_PASSWORD = "parkguard123";
WebServer server(80);
bool cameraReady = false;

static void handleStream() {
  if (!cameraReady) {
    server.send(503, "text/plain", "Camera initialization failed; check serial output and pin map.");
    return;
  }

  WiFiClient client = server.client();
  client.print("HTTP/1.1 200 OK\r\nContent-Type: multipart/x-mixed-replace; boundary=frame\r\nCache-Control: no-cache\r\nConnection: close\r\n\r\n");
  while (client.connected()) {
    camera_fb_t *frame = esp_camera_fb_get();
    if (!frame) {
      delay(100);
      continue;
    }
    client.print("--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ");
    client.print(frame->len);
    client.print("\r\n\r\n");
    size_t sent = client.write(frame->buf, frame->len);
    client.print("\r\n");
    esp_camera_fb_return(frame);
    if (sent == 0) break;
    delay(80);
  }
  client.stop();
}

void setup() {
  Serial.begin(115200);
  delay(700);
  Serial.println("ParkGuard camera view test booting");

  camera_config_t config = {};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = CAM_D0;
  config.pin_d1 = CAM_D1;
  config.pin_d2 = CAM_D2;
  config.pin_d3 = CAM_D3;
  config.pin_d4 = CAM_D4;
  config.pin_d5 = CAM_D5;
  config.pin_d6 = CAM_D6;
  config.pin_d7 = CAM_D7;
  config.pin_xclk = CAM_XCLK;
  config.pin_pclk = CAM_PCLK;
  config.pin_vsync = CAM_VSYNC;
  config.pin_href = CAM_HREF;
  config.pin_sccb_sda = CAM_SIOD;
  config.pin_sccb_scl = CAM_SIOC;
  config.pin_pwdn = CAM_PWDN;
  config.pin_reset = CAM_RESET;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;
  config.fb_location = CAMERA_FB_IN_PSRAM;

  const esp_err_t cameraStatus = esp_camera_init(&config);
  cameraReady = cameraStatus == ESP_OK;
  Serial.printf("Camera init: %s (0x%x)\n", cameraReady ? "OK" : "FAILED", cameraStatus);

  WiFi.mode(WIFI_AP);
  if (!WiFi.softAP(AP_SSID, AP_PASSWORD)) {
    Serial.println("Wi-Fi AP start failed");
  } else {
    Serial.printf("Connect to Wi-Fi %s (password %s)\n", AP_SSID, AP_PASSWORD);
    Serial.printf("Open http://%s/stream for live video\n", WiFi.softAPIP().toString().c_str());
  }

  server.on("/", HTTP_GET, []() {
    server.send(200, "text/html", "<html><body style='margin:0;background:#07120b;color:#9cff9c;font:16px monospace'><h2>ParkGuard ESP32-CAM</h2><p><a style='color:#9cff9c' href='/stream'>Open live stream</a></p><img src='/stream' style='width:100%;max-width:800px'></body></html>");
  });
  server.on("/health", HTTP_GET, []() {
    server.send(cameraReady ? 200 : 503, "application/json", cameraReady ? "{\"camera\":\"ready\"}" : "{\"camera\":\"init_failed\"}");
  });
  server.on("/stream", HTTP_GET, handleStream);
  server.begin();
  Serial.println("HTTP server ready");
}

void loop() {
  server.handleClient();
  delay(2);
}
