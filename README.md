# ParkGuard

ParkGuard is a simulator-first prototype for parking-bay smoke, gas-trend and heat alerts. It is **not a certified fire alarm**. MQ sensors report relative trends, not calibrated concentrations; the system cannot predict explosions and never calls emergency services automatically. Without GPS, node position is the registered location. Get building permission before capturing photos.

## Zero-hardware demo

Requirements: Docker Compose (or Python 3.11+). Copy `.env.example` to `.env`, then run `make demo`. Visit http://localhost:8000. The scripted incident emits readings and a sample photo. You can replay cases from the Demo page or run `python -m simulator.run --scenario vehicle_fire` with the API running.

Without Docker: `python -m venv .venv`; activate it; `pip install -r requirements.txt`; `uvicorn parkguard.main:app --reload`. MongoDB/MinIO are optional for laptop mode: the API uses an in-memory repository and local photo storage when those services are absent. `python -m simulator.run --scenario normal` sends simulated readings.

## Parts and wiring

Only the listed parts are assumed. ESP32: MQ135 AO GPIO34, MQ4 AO GPIO35, DHT22 data GPIO4, optional active buzzer GPIO25. Common ground. Power demo from a USB power bank to the dev board. **Never connect a 5V MQ analog output directly to an ESP32 ADC.** Use a resistor divider to keep ADC input at or below 3.3V. If resistors are unavailable, compile with `MQ_3V3_MODE=1` and power MQ modules from 3.3V; sensitivity is reduced and readings are not calibrated. The listed CN3791, TP4056, 18650 and B0505S are not needed for this demo. Solar/18650 backup is a future upgrade only; do not assume the listed modules alone form a safe, complete power system.

### ESP32-CAM upload

Use the dev board as a USB-serial bridge: disconnect power; tie dev-board EN to GND; connect dev-board TX to camera RX and dev-board RX to camera TX; connect grounds; connect camera GPIO0 to GND for upload; power the camera from a stable 5V supply. Select the ESP32-CAM board/port and upload, then remove GPIO0-GND and reset. The camera code keeps at most two JPEGs in PSRAM and retries uploads; power-cycle/outage can lose them. No SD card is used.

## Configuration

Fill `.env` values for Wi-Fi (firmware), Telegram token/chat, API base URL, and registered node coordinates in `config/nodes.json`. The ESP32 sends node ID; API attaches the registered position (`registered location`). Optional Wi-Fi positioning sends nearby BSSIDs to the experimental BeaconDB geolocation service; availability and coverage vary. Results are labelled `approximate (Wi-Fi)` and never replace registered coordinates. Phone GPS is a separate mobile node, labelled `phone GPS`. Direct Telegram fallback in device firmware is disabled by default; storing a bot token on a device exposes it if the device is captured.

Device API keys are configured in `PARKGUARD_DEVICE_KEYS` as JSON mapping node ID to key. Rotate defaults before deployment. Mongo URI and MinIO credentials are environment variables.

For remote use, terminate HTTPS at a trusted reverse proxy or Ingress and set firmware `API_URL` and camera API address to that HTTPS host. Paste the trusted root CA PEM into `ROOT_CA_CERT` in both firmware files before public deployment; plain HTTP is for a trusted demo LAN only. The manual CI deploy expects a repository secret named `KUBECONFIG_B64` containing a base64 kubeconfig.

## Scenarios and models

Scenarios: `normal`, `exhaust`, `firecracker_smoke`, `cng_leak`, `ev_fault`, `vehicle_fire`, `explosion`, `unwarranted_fire`, `spreading_fire`, and `network_outage`. Example: `python -m simulator.run --scenario spreading_fire`. During network outage, the simulator queues critical events first and replays after reconnect.

The classifier combines recent trend, duration, temperature and humidity. Rules are authoritative for danger; low-confidence ML/image labels never lower an alert level. Generate/train with `python -m parkguard.ai.train --generate` and retrain from logged JSONL with `--data`. Image check is a replaceable heuristic interface, not a trained vision model. Optional phone loudness page is a demo stand-in only, not a blast sensor.

## ESP32 firmware

Open `firmware/sensor_node/sensor_node.ino` in Arduino IDE. Install DHT sensor library and ArduinoJson. Set Wi-Fi, API URL, node ID and device key in `config.h`; calibrate baseline during the first 60 seconds. Sampling interval is 3 seconds. LittleFS ring buffer persists readings/events and prioritizes emergency records. Level 3 buzzer/onboard LED works offline; level 2 triggers the camera node over HTTP. Set `WIFI_POSITIONING` only for experimental AP identifiers.

## Escalation behavior

Levels: 0 normal, 1 warning, 2 alarm, 3 emergency. Emergency messages contain position source, map/directions/Waze links, photo, event hash, and “Call 101 now” tap-to-call (no auto-dial). Telegram re-pings every 30 seconds until acknowledged. Acknowledge and “I am at the scene” are available in the web UI. The escalation record models watchman → manager after 60 seconds → vehicle owner; SMS is a provider interface stub. Explosion-like rapid gas+temperature rise plus photo smoke/flame is a heuristic emergency, not explosion prediction. Unwarranted fire means fire signal outside a registered event window. Sustained rising fire >90s, matching neighboring nodes within five minutes, or growing photos marks spreading.

## Cloud and Kubernetes

Docker Compose is the safe demo-day fallback. It runs API, MongoDB, MinIO, Grafana and Prometheus. Grafana dashboard is provisioned. GitHub Actions runs tests, Trivy scan and GHCR build; deploy job is manual/needs secrets. Kubernetes manifests use Kustomize base/local/prod, PVCs, probes, limits, HPA, NetworkPolicy and nightly model retraining. Kubernetes is more operational work than this prototype needs; use Compose for demos. For a small server, install k3s, configure ingress/storage, then `make deploy`.

## Safe demo and troubleshooting

Use simulator first. For a supervised physical demo, use only a brief hair-dryer warm-up and a small amount of incense in a ventilated, permitted location; sanitizer vapour only in tiny amounts away from ignition and after ventilation. Never release fuel, burn materials, or make smoke indoors. Stop immediately if anyone feels unwell. MQ warm-up and humidity affect readings. Check sensor power, common ground, analog voltage ceiling, Wi-Fi, API key, camera wiring and PSRAM. This prototype is not suitable for life-safety decisions.

## Assumptions and values to fill in

- Wi-Fi name/password in firmware configuration.
- Telegram bot token and destination chat ID in `.env`.
- Registered latitude/longitude, building, floor and bay in `config/nodes.json`.
- Server address in firmware `API_URL` and `CAMERA_URL`.
- Trusted server root CA PEM in firmware when using HTTPS.
- Unique device keys per node before connecting real devices.
