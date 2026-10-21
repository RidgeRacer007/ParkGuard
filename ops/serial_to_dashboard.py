"""Forward live ESP32 JSON lines from COM4 into the local ParkGuard API."""
import argparse
import json
import sys

import httpx
import serial


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="COM4")
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--node-key", default="demo-key-change-me")
    args = parser.parse_args()

    headers = {"X-Device-Key": args.node_key, "Content-Type": "application/json"}
    with serial.Serial(args.port, 115200, timeout=1, dsrdtr=False, rtscts=False) as port, httpx.Client(timeout=4) as client:
        port.dtr = False
        port.rts = False
        print(f"Reading {args.port} at 115200 baud; forwarding live readings to {args.api}", flush=True)
        while True:
            line = port.readline().decode("utf-8", errors="replace").strip()
            if not line:
                continue
            if not line.startswith("{"):
                # Board boot text can contain undecodable bytes on Windows consoles.
                print(line.encode("ascii", errors="replace").decode("ascii"), flush=True)
                continue
            try:
                reading = json.loads(line)
                response = client.post(f"{args.api}/api/readings", content=line, headers=headers)
                response.raise_for_status()
                result = response.json()
                decision = result.get("decision", {})
                print(
                    "LIVE {node_id} | MQ135 {mq135} | MQ4 {mq4} | {temperature:.1f} C | {humidity:.1f}% RH | {label}, level {level}".format(
                        **reading,
                        label=decision.get("label", "unknown"),
                        level=decision.get("level", "?")
                    ),
                    flush=True,
                )
            except (json.JSONDecodeError, httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                print(f"Forward failed: {exc}; line={line}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    raise SystemExit(main())

