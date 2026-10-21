#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include "esp_camera.h"
#include "esp_heap_caps.h"

const char* WIFI_SSID="CHANGE_ME"; const char* WIFI_PASSWORD="CHANGE_ME"; const char* API="http://192.168.1.10:8000"; const char* ROOT_CA_CERT=""; const char* NODE="demo-node"; const char* KEY="demo-key-change-me";
// Select camera pin map for the exact ESP32-CAM board and OV5640 carrier.
WebServer server(80); uint8_t* recent[2]={nullptr,nullptr}; size_t recentSize[2]={0,0}; int nextSlot=0; unsigned long lastRetry=0; bool cameraReady=false;
bool uploadFrame(int slot){if(!recent[slot]||WiFi.status()!=WL_CONNECTED)return false;HTTPClient http;String url=String(API)+"/api/photos/"+NODE;int code=0;if(url.startsWith("https://")){WiFiClientSecure client;client.setCACert(ROOT_CA_CERT);if(!http.begin(client,url))return false;http.addHeader("X-Device-Key",KEY);http.addHeader("Content-Type","image/jpeg");code=http.POST(recent[slot],recentSize[slot]);http.end();}else{WiFiClient client;if(!http.begin(client,url))return false;http.addHeader("X-Device-Key",KEY);http.addHeader("Content-Type","image/jpeg");code=http.POST(recent[slot],recentSize[slot]);http.end();}return code>=200&&code<300;}
void capture(){camera_fb_t* fb=esp_camera_fb_get();if(!fb){server.send(500,"text/plain","capture failed");return;}if(recent[nextSlot])heap_caps_free(recent[nextSlot]);recent[nextSlot]=(uint8_t*)heap_caps_malloc(fb->len,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);recentSize[nextSlot]=fb->len;if(recent[nextSlot])memcpy(recent[nextSlot],fb->buf,fb->len);uploadFrame(nextSlot);nextSlot=(nextSlot+1)%2;server.send(200,"application/json","{\"captured\":true}");esp_camera_fb_return(fb);}
void streamCamera(){
 if(!cameraReady){server.send(503,"text/plain","camera is not initialized");return;}
 WiFiClient client=server.client();
 client.print("HTTP/1.1 200 OK\r\nContent-Type: multipart/x-mixed-replace; boundary=frame\r\nCache-Control: no-cache\r\nConnection: close\r\n\r\n");
 while(client.connected()){
  camera_fb_t* fb=esp_camera_fb_get();
  if(!fb){delay(100);continue;}
  client.print("--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ");client.print(fb->len);client.print("\r\n\r\n");
  size_t sent=client.write(fb->buf,fb->len);client.print("\r\n");esp_camera_fb_return(fb);
  if(sent==0)break;
  delay(100);
 }
 client.stop();
}
void setup(){Serial.begin(115200);WiFi.begin(WIFI_SSID,WIFI_PASSWORD);while(WiFi.status()!=WL_CONNECTED)delay(500);camera_config_t c={};
 // AI-Thinker-compatible ESP32-CAM pin map. Verify the OV5640 carrier uses this layout.
 c.pin_pwdn=32;c.pin_reset=-1;c.pin_xclk=0;c.pin_sccb_sda=26;c.pin_sccb_scl=27;
 c.pin_d7=35;c.pin_d6=34;c.pin_d5=39;c.pin_d4=36;c.pin_d3=21;c.pin_d2=19;c.pin_d1=18;c.pin_d0=5;
 c.pin_vsync=25;c.pin_href=23;c.pin_pclk=22;
 c.ledc_channel=LEDC_CHANNEL_0;c.ledc_timer=LEDC_TIMER_0;c.pixel_format=PIXFORMAT_JPEG;c.frame_size=FRAMESIZE_SVGA;c.jpeg_quality=12;c.fb_count=2;c.fb_location=CAMERA_FB_IN_PSRAM;
 esp_err_t err=esp_camera_init(&c);cameraReady=(err==ESP_OK);if(!cameraReady)Serial.printf("Camera init failed: %d; confirm carrier pin map\n",err);else Serial.printf("Camera ready. Stream: http://%s/stream\n",WiFi.localIP().toString().c_str());server.on("/capture",HTTP_POST,capture);server.on("/stream",HTTP_GET,streamCamera);server.begin();}
void loop(){server.handleClient();if(millis()-lastRetry>15000){lastRetry=millis();for(int i=0;i<2;i++)uploadFrame(i);}}
