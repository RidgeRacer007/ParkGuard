#include <Arduino.h>
#include <DHT.h>

static constexpr uint8_t DHT_PIN = 4;
static constexpr uint8_t MQ135_PIN = 34;
static constexpr uint8_t MQ4_PIN = 35;
static constexpr char NODE_ID[] = "demo-node";
DHT dht(DHT_PIN, DHT22);
uint32_t startMs = 0;
uint32_t lastSample = 0;

static uint16_t readAverage(uint8_t pin) {
  uint32_t sum = 0;
  for (int i = 0; i < 16; ++i) {
    sum += analogRead(pin);
    delay(2);
  }
  return static_cast<uint16_t>(sum / 16);
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  analogSetPinAttenuation(MQ135_PIN, ADC_11db);
  analogSetPinAttenuation(MQ4_PIN, ADC_11db);
  dht.begin();
  startMs = millis();
  delay(1500);
  Serial.println("PARKGUARD_SENSOR_READY");
}

void loop() {
  if (millis() - lastSample < 3000) return;
  lastSample = millis();

  const float temperature = dht.readTemperature();
  const float humidity = dht.readHumidity();
  const uint16_t mq135 = readAverage(MQ135_PIN);
  const uint16_t mq4 = readAverage(MQ4_PIN);

  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("DHT22_READ_ERROR");
    return;
  }

  // Serial-to-local-dashboard test. MQ fields are raw ADC counts, not ppm.
  Serial.printf(
      "{\"node_id\":\"%s\",\"mq135\":%u,\"mq4\":%u,\"temperature\":%.1f,\"humidity\":%.1f,\"duration_s\":%lu,\"event_window\":false,\"sensor_alarm\":false,\"smoke_or_flame\":false}\n",
      NODE_ID, mq135, mq4, temperature, humidity,
      static_cast<unsigned long>((millis() - startMs) / 1000));
}

