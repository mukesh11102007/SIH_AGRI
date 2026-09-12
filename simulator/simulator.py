"""
Smart Farming Sensor Simulator — Main Entry Point.

Publishes realistic sensor telemetry to the MQTT broker.
Polls the backend API for the active scenario to allow
live switching from the frontend without restarting.

Data Source: SIMULATION
The backend processes this data through the exact same pipeline
as real ESP32 hardware.
"""
from __future__ import annotations
import asyncio
import json
import os
import time
import httpx
from datetime import datetime, timezone

import aiomqtt
from engine.sensor_engine import SensorEngine

# ── Configuration from environment ───────────────────────────────────────────
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "farmdevice")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "changeme_mqtt_password")

FARM_ID = os.getenv("SIMULATOR_FARM_ID", "farm-001")
FIELD_ID = os.getenv("SIMULATOR_FIELD_ID", "field-north-01")
DEVICE_ID = os.getenv("SIMULATOR_DEVICE_ID", "sim-esp32-01")
INTERVAL = float(os.getenv("SIMULATOR_INTERVAL_SECONDS", "10"))
INITIAL_SCENARIO = os.getenv("SIMULATOR_SCENARIO", "NORMAL")
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

TELEMETRY_TOPIC = f"farm/{FARM_ID}/field/{FIELD_ID}/device/{DEVICE_ID}/telemetry"
STATUS_TOPIC = f"farm/{FARM_ID}/field/{FIELD_ID}/device/{DEVICE_ID}/status"


async def poll_scenario(client: httpx.AsyncClient, current: str) -> str:
    """Check the backend for the active scenario. Fail silently."""
    try:
        r = await client.get(f"{BACKEND_URL}/api/v1/simulator/scenario", timeout=3.0)
        if r.status_code == 200:
            return r.json().get("scenario", current)
    except Exception:
        pass
    return current


async def run_simulator() -> None:
    engine = SensorEngine()
    engine.set_scenario(INITIAL_SCENARIO)
    scenario = INITIAL_SCENARIO

    print(f"[SIMULATOR] Starting — Device: {DEVICE_ID} | Farm: {FARM_ID} | Field: {FIELD_ID}")
    print(f"[SIMULATOR] MQTT: {MQTT_HOST}:{MQTT_PORT} | Interval: {INTERVAL}s")
    print(f"[SIMULATOR] Initial scenario: {scenario}")

    reconnect_interval = 5
    sequence = 0

    async with httpx.AsyncClient() as http_client:
        while True:
            try:
                async with aiomqtt.Client(
                    hostname=MQTT_HOST,
                    port=MQTT_PORT,
                    username=MQTT_USERNAME,
                    password=MQTT_PASSWORD,
                    identifier=f"simulator-{DEVICE_ID}",
                    keepalive=60,
                ) as mqtt:
                    print(f"[SIMULATOR] MQTT connected to {MQTT_HOST}")
                    reconnect_interval = 5  # Reset on success

                    # Publish initial status
                    await mqtt.publish(
                        STATUS_TOPIC,
                        json.dumps({"status": "online", "scenario": scenario}),
                        qos=0,
                    )

                    while True:
                        # Check for scenario changes every 5 readings
                        if sequence % 5 == 0:
                            new_scenario = await poll_scenario(http_client, scenario)
                            if new_scenario != scenario:
                                scenario = new_scenario
                                engine.set_scenario(scenario)
                                print(f"[SIMULATOR] Scenario changed → {scenario}")

                        # Generate readings
                        readings = engine.generate()
                        sequence += 1

                        payload = {
                            "device_id": DEVICE_ID,
                            "farm_id": FARM_ID,
                            "field_id": FIELD_ID,
                            "firmware_version": "sim-1.0.0",
                            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                            "source": "simulator",
                            "sequence_number": sequence,
                            "readings": readings,
                            "sensor_status": {
                                "dht22": "ok",
                                "ds18b20": "ok",
                                "soil_moisture": "ok",
                                "bh1750": "ok",
                                "leaf_wetness": "ok",
                                "vibration": "ok",
                                "float_switch": "ok",
                            },
                        }

                        await mqtt.publish(
                            TELEMETRY_TOPIC,
                            json.dumps(payload),
                            qos=1,  # At-least-once delivery
                        )

                        print(
                            f"[SIMULATOR] [{scenario:16s}] #{sequence:5d} | "
                            f"T={readings['air_temperature_c']:5.1f}°C | "
                            f"H={readings['air_humidity_pct']:5.1f}% | "
                            f"SM={readings['soil_moisture_pct']:5.1f}% | "
                            f"Water={'✓' if readings['water_level_available'] else '✗'}"
                        )

                        await asyncio.sleep(INTERVAL)

            except aiomqtt.MqttError as exc:
                print(f"[SIMULATOR] MQTT disconnected: {exc}. Reconnecting in {reconnect_interval}s...")
                await asyncio.sleep(reconnect_interval)
                reconnect_interval = min(reconnect_interval * 2, 60)
            except asyncio.CancelledError:
                print("[SIMULATOR] Shutting down.")
                break
            except Exception as exc:
                print(f"[SIMULATOR] Unexpected error: {exc}")
                await asyncio.sleep(reconnect_interval)


if __name__ == "__main__":
    asyncio.run(run_simulator())
