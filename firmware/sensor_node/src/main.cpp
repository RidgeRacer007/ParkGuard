#include "config.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <LittleFS.h>
#include <WiFiClientSecure.h>

// MQ analog input must stay <=3.3V. MQ_3V3_MODE powers sensors at 3.3V (lower sensitivity).
#if MQ_3V3_MODE
#warning "MQ_3V3_MODE: reduced sensitivity; never treat MQ readings as calibrated gas concentrations"
#endif
DHT dht(DHT_PIN,DHT22); const int LED_PIN=2; unsigned long lastSample=0,started=0; float baseGas=0,baseTemp=0; int calibrationCount=0; bool calibrated=false;
const char *QUEUE_FILE="/queue.jsonl";
String queueText="";
void directFallback(){
#if DIRECT_TELEGRAM_FALLBACK
 WiFiClientSecure client;client.setCACert(ROOT_CA_CERT);HTTPClient http;String endpoint="https://api.telegram.org/bot" TELEGRAM_BOT_TOKEN "/sendMessage";if(!http.begin(client,endpoint))return;StaticJsonDocument<512> msg;msg["chat_id"]=TELEGRAM_CHAT_ID;String link="https://www.google.com/maps?q="+String(NODE_LAT,6)+","+String(NODE_LON,6);msg["text"]=String("ParkGuard emergency: ")+NODE_BUILDING+" "+NODE_FLOOR+" bay "+NODE_BAY+". Position source: registered location. Maps: "+link+". Call 101 now.";String body;serializeJson(msg,body);http.addHeader("Content-Type","application/json");http.POST(body);http.end();
#endif
}
void connectWifi(){WiFi.mode(WIFI_STA);WiFi.begin(WIFI_SSID,WIFI_PASSWORD);}
void persist(const String &line,bool emergency){if(!LittleFS.begin(true))return;String old="";File in=LittleFS.open(QUEUE_FILE,"r");if(in){old=in.readString();in.close();}String record=String(emergency?"!":".")+line+"\n";old+=record;
 // Bounded flash ring: retain the newest complete records within a 48 KiB budget.
 if(old.length()>49152){int cut=old.length()-49152;int newline=old.indexOf('\n',cut);if(newline>=0)old.remove(0,newline+1);}
 File out=LittleFS.open(QUEUE_FILE,"w");if(out){out.print(old);out.close();}}
int sendJson(const String &url,const String &body){HTTPClient http;int code=0;if(url.startsWith("https://")){WiFiClientSecure client;client.setCACert(ROOT_CA_CERT);if(!http.begin(client,url))return 0;http.addHeader("Content-Type","application/json");http.addHeader("X-Device-Key",DEVICE_KEY);code=http.POST(body);http.end();}else{WiFiClient client;if(!http.begin(client,url))return 0;http.addHeader("Content-Type","application/json");http.addHeader("X-Device-Key",DEVICE_KEY);code=http.POST(body);http.end();}return code;}
void postJson(const String &body){bool emergency=body.indexOf("\"sensor_alarm\":true")>=0;if(WiFi.status()!=WL_CONNECTED){persist(body,emergency);if(emergency)directFallback();return;}int code=sendJson(String(API_URL)+"/api/readings",body);if(code<200||code>=300){persist(body,emergency);if(emergency)directFallback();}}
void resend(){if(WiFi.status()!=WL_CONNECTED||!LittleFS.exists(QUEUE_FILE))return;File f=LittleFS.open(QUEUE_FILE,"r");String emergency="",normal="";while(f.available()){String line=f.readStringUntil('\n');if(line.startsWith("!"))emergency+=line.substring(1)+"\n";else if(line.startsWith("."))normal+=line.substring(1)+"\n";}f.close();String all=emergency+normal;while(all.length()){int end=all.indexOf('\n');if(end<0)break;String body=all.substring(0,end);int code=sendJson(String(API_URL)+"/api/readings",body);if(code<200||code>=300)return;all.remove(0,end+1);}LittleFS.remove(QUEUE_FILE);}
void triggerCamera(){if(WiFi.status()!=WL_CONNECTED)return;HTTPClient h;h.begin(CAMERA_URL);h.addHeader("X-Device-Key",DEVICE_KEY);h.POST("capture");h.end();}
void setup(){pinMode(LED_PIN,OUTPUT);pinMode(BUZZER_PIN,OUTPUT);Serial.begin(115200);dht.begin();started=millis();connectWifi();}
void loop(){if(millis()-lastSample<3000)return;lastSample=millis();if(WiFi.status()!=WL_CONNECTED)connectWifi();float a=analogRead(MQ135_PIN),b=analogRead(MQ4_PIN),t=dht.readTemperature(),h=dht.readHumidity();if(isnan(t)||isnan(h))return;
 if(!calibrated&&millis()-started<60000){baseGas+=(a+b)/2;baseTemp+=t;calibrationCount++;if(millis()-started>=59000&&calibrationCount){baseGas/=calibrationCount;baseTemp/=calibrationCount;calibrated=true;}}
 bool high=(a>baseGas+800)||(b>baseGas+800)||t>55;int level=(t>70&&high)?3:(high?2:0);digitalWrite(LED_PIN,level>=3?HIGH:LOW);digitalWrite(BUZZER_PIN,level>=3?HIGH:LOW);if(level>=2)triggerCamera();
 StaticJsonDocument<768> doc;doc["node_id"]=NODE_ID;doc["mq135"]=a;doc["mq4"]=b;doc["temperature"]=t;doc["humidity"]=h;doc["event_window"]=false;doc["sensor_alarm"]=level>=2;doc["duration_s"]=(millis()-started)/1000;
#if WIFI_POSITIONING
 int count=WiFi.scanNetworks(false,true);JsonArray aps=doc.createNestedArray("wifi_aps");for(int i=0;i<count&&i<10;i++)aps.add(WiFi.BSSIDstr(i));WiFi.scanDelete();
#endif
 String body;serializeJson(doc,body);postJson(body);resend();}
