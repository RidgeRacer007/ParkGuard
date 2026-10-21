# ESP32 DevKit V1 + ESP32-CAM first connection test

This tiny PlatformIO project verifies the boards and their Wi-Fi connection before attaching the DHT22 or MQ sensors. It does not initialize the OV5640 yet, so its exact camera pin map is not needed for this first test.

## What success looks like

The ESP32-CAM creates a Wi-Fi network named `ParkGuard-CAM`. The DevKit joins it and prints an HTTP 200 response with `{"node":"esp32-cam","status":"online"}` every five seconds in the serial monitor.

## Wiring while flashing the ESP32-CAM through the DevKit USB-serial bridge

| DevKit V1 | ESP32-CAM |
|---|---|
| GPIO1 / TX0 | U0R / RX0 |
| GPIO3 / RX0 | U0T / TX0 |
| GND | GND |
| EN | Hold to GND to disable the DevKit MCU while using its USB-serial bridge |
| — | GPIO0 to GND only while flashing; release it and reset to run |
| — | Stable regulated 5 V supply to camera 5V |

Keep camera 5 V supply separate from the DevKit 3V3 pin. Use common ground during UART flashing. Remove the UART and GPIO0 jumpers after uploading. During the normal Wi-Fi test there are no UART signal wires between the boards.

## Upload in VS Code with PlatformIO

1. Open this `firmware/pair_test` folder in VS Code with the PlatformIO extension.
2. Select the `cam` environment and upload `src/main.cpp` to the ESP32-CAM. Keep GPIO0 grounded for upload; reset the camera when prompted if needed.
3. Remove the camera's GPIO0-to-GND wire and reset it. In the camera serial monitor, look for the `ParkGuard-CAM` AP and `192.168.4.1` address.
4. Reconnect the DevKit's USB-serial connection. Select the `devkit` environment and upload `src/main.cpp`.
5. Open the DevKit serial monitor at 115200 baud. Look for the online JSON response.

If no serial port appears, reconnect the board and check Windows Device Manager. This project uses a 2.4 GHz local Wi-Fi link and has no cloud or home-router dependency.


