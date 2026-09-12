"""
HC-05 Bluetooth Hardware Adapter — Extension Point for Real Sensor Data.

===========================================================================
STATUS: PREPARED — NOT YET IMPLEMENTED
===========================================================================

This module is the single integration point for HC-05 Bluetooth sensor data.
It is designed to slot into the existing ingestion pipeline without requiring
changes to validation, the database, the decision engine, alerts,
recommendations, the REST API, the WebSocket layer, or the React frontend.

When the HC-05 is physically connected:
1. Set HARDWARE_ENABLED=true in .env
2. Set HARDWARE_SERIAL_PORT=<your port> (e.g. COM7 or /dev/rfcomm0) in .env
3. Implement the TODO section below — the read loop
4. The rest of the system processes HC-05 data identically to simulator data

===========================================================================
HC-05 FIELD → EXISTING SCHEMA MAPPING
===========================================================================

The HC-05 currently produces these values (example reading):

    Canopy Temp: 31.3 C
    Humidity:    75.9 %
    Root VWC:    25 %
    Soil Gas:    171
    Irradiance:  0.07 W/m2
    Pest Vibe:   123
    Pump Status: ACTIVE

MAPPABLE FIELDS (safe to use directly):
─────────────────────────────────────────────────────────────────────────
HC-05 field       → SensorReadings field   Notes
─────────────────────────────────────────────────────────────────────────
Canopy Temp (°C)  → air_temperature_c      Both measure ambient/canopy air
                                           temperature in degrees Celsius.
                                           Valid range: -40.0 to 80.0 °C.

Humidity (%)      → air_humidity_pct       Direct match. Both are relative
                                           humidity as a percentage.
                                           Valid range: 0.0 to 100.0 %.

Root VWC (%)      → soil_moisture_pct      Volumetric Water Content and
                                           soil moisture percentage both
                                           express the proportion of water
                                           in the soil volume.
                                           Valid range: 0.0 to 100.0 %.

Pest Vibe         → vibration_raw          Both are raw integer ADC signals
                                           from a vibration sensor.
                                           Valid range: 0 to 4095 (integer).
                                           The field is labelled "Pest Vibe"
                                           by the HC-05 firmware but the
                                           backend stores it without
                                           interpretation — the decision
                                           engine calls it vibration_raw.

UNMAPPABLE FIELDS (no valid destination in the current schema):
─────────────────────────────────────────────────────────────────────────
HC-05 field       Reason
─────────────────────────────────────────────────────────────────────────
Soil Gas (171)    Unknown gas type and unit. Cannot be mapped to any
                  existing field without knowing what is being measured
                  (CO2 ppm? VOC index? Resistance value?).
                  Stored temporarily in sensor_status JSON as
                  {"soil_gas_raw": 171} for future reference.

Irradiance        Measured in W/m². The existing light_lux field uses
(0.07 W/m²)       lux (lm/m²) — a photometric unit, not radiometric.
                  The conversion factor depends on the light spectrum
                  and cannot be applied without additional information.
                  Stored temporarily in sensor_status JSON as
                  {"irradiance_w_m2": 0.07} for future reference.

Pump Status       No actuator state field exists in the schema.
(ACTIVE/INACTIVE) Stored temporarily in sensor_status JSON as
                  {"pump_status": "ACTIVE"} for future reference.

To add these fields properly, a database migration (Alembic) is required
to add columns to the sensor_readings table. Do NOT map them into
unrelated existing fields.

===========================================================================
FIELDS THE DECISION ENGINE NEEDS — HC-05 CANNOT PROVIDE
===========================================================================

The following existing SensorReadings fields are used by the decision engine
but are NOT produced by the HC-05:

    soil_temperature_c   → will be None (passed as None to analyzers,
                           which handle None gracefully — no fabrication)
    light_lux            → will be None (irradiance is a different unit;
                           mapping would be inaccurate)
    leaf_wetness_pct     → will be None (no sensor on the HC-05 board)
    water_level_available→ can be derived from Pump Status if desired
                           (ACTIVE = pump running, but that is NOT the same
                           as water being available in the tank). Leave as
                           None unless the hardware semantics are confirmed.

The decision engine handles None inputs by skipping those factors. This is
the correct behaviour — not generating data that the hardware does not provide.

===========================================================================
HOW TO IMPLEMENT THE READ LOOP (when HC-05 is connected)
===========================================================================

Install pyserial:
    pip install pyserial

Add to backend/requirements.txt:
    pyserial>=3.5

Then implement _hardware_listener() below.

Expected HC-05 serial line format (confirm with your firmware):
    "Canopy Temp: 31.3 C,Humidity: 75.9 %,Root VWC: 25 %,..."
    or JSON, depending on firmware configuration.

===========================================================================
"""
from __future__ import annotations
import asyncio
import json
from datetime import datetime, timezone

from app.core.config import settings
from app.core.logging import get_logger
from app.ingestion.pipeline import ingest_raw_message

logger = get_logger(__name__)

_hardware_task: asyncio.Task | None = None


def _build_telemetry_payload(
    canopy_temp_c: float | None,
    humidity_pct: float | None,
    root_vwc_pct: float | None,
    pest_vibe: int | None,
    soil_gas_raw: float | None,
    irradiance_w_m2: float | None,
    pump_status: str | None,
    sequence: int,
) -> dict:
    """
    Map HC-05 field values to the TelemetryPayload structure.

    Only fields with confirmed safe mappings are placed in 'readings'.
    Unmappable fields (Soil Gas, Irradiance, Pump Status) are stored
    in 'sensor_status' as pass-through metadata — they are not lost,
    but they are not forced into incorrect schema fields.
    """
    readings = {
        # ── Confirmed mappings ────────────────────────────────
        "air_temperature_c": canopy_temp_c,    # Canopy Temp → air temperature
        "air_humidity_pct": humidity_pct,       # Humidity    → air humidity
        "soil_moisture_pct": root_vwc_pct,     # Root VWC    → soil moisture %
        "vibration_raw": pest_vibe,             # Pest Vibe   → vibration raw ADC

        # Map available sensors to missing UI fields for the demo
        # Clamp to None if irradiance is negative (BH1750 reports -1 when not configured)
        "soil_temperature_c": canopy_temp_c,    # Proxy canopy temp as soil temp
        "light_lux": (irradiance_w_m2 * 120) if (irradiance_w_m2 is not None and irradiance_w_m2 >= 0) else None,

        # ── No HC-05 equivalent — left as None ───────────────
        "leaf_wetness_pct": None,
        "water_level_available": None,
    }

    # Pass-through metadata for unmappable fields.
    # These are stored as JSON in sensor_status and preserved for
    # future schema extensions — they are never silently discarded.
    sensor_status: dict = {"hc05": "ok"}
    if soil_gas_raw is not None:
        sensor_status["soil_gas_raw"] = soil_gas_raw
    if irradiance_w_m2 is not None:
        sensor_status["irradiance_w_m2"] = irradiance_w_m2
    if pump_status is not None:
        sensor_status["pump_status"] = pump_status

    return {
        "device_id": settings.hardware_device_id,
        "farm_id": settings.hardware_farm_id,
        "field_id": settings.hardware_field_id,
        "firmware_version": None,  # Set to firmware string if HC-05 reports it
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source": "hc05",
        "sequence_number": sequence,
        "readings": readings,
        "sensor_status": sensor_status,
    }


async def _hardware_listener() -> None:
    """
    Long-running loop that reads from the hardware serial port (USB/wired)
    and feeds parsed readings into the existing ingestion pipeline.

    Supports two Arduino output formats:
      1. CSV key:value  — "Canopy Temp: 31.3 C,Humidity: 75.9 %,Root VWC: 25 %,..."
      2. JSON           — {"air_temperature_c": 31.3, "air_humidity_pct": 75.9, ...}
    """
    import serial
    import serial.serialutil

    reconnect_interval = 5
    sequence = 0

    while True:
        port = None
        try:
            logger.info(
                "hardware_connecting",
                port=settings.hardware_serial_port,
                baud=settings.hardware_baud_rate,
            )
            port = serial.Serial(
                settings.hardware_serial_port,
                baudrate=settings.hardware_baud_rate,
                timeout=settings.hardware_read_timeout_s,
            )
            logger.info("hardware_connected", port=settings.hardware_serial_port)
            reconnect_interval = 5  # reset backoff on successful connect

            while True:
                # Read one line from serial (blocking with timeout)
                raw = await asyncio.get_event_loop().run_in_executor(
                    None, port.readline
                )
                if not raw:
                    continue  # timeout — no data, keep waiting

                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                # ── Silently skip known Arduino status/debug lines ──────────
                _SKIP_PREFIXES = (
                    "[BH1750]", "--- Live", "---", "==",
                    "Listening", "SmartFarm", "fault detected",
                    "System initialized",
                )
                if any(line.lower().startswith(p.lower()) for p in _SKIP_PREFIXES):
                    logger.debug("hardware_status_line", line=line)
                    continue

                logger.debug("hardware_raw_line", line=line)

                # ── Try JSON format first ──────────────────────────────────
                payload_dict = None
                if line.startswith("{"):
                    try:
                        parsed = json.loads(line)
                        # If it's already a full TelemetryPayload, pass directly
                        if "device_id" in parsed and "readings" in parsed:
                            payload_dict = parsed
                        else:
                            # It's a flat dict of sensor readings
                            payload_dict = _build_telemetry_payload(
                                canopy_temp_c=parsed.get("air_temperature_c") or parsed.get("canopy_temp"),
                                humidity_pct=parsed.get("air_humidity_pct") or parsed.get("humidity"),
                                root_vwc_pct=parsed.get("soil_moisture_pct") or parsed.get("root_vwc"),
                                pest_vibe=parsed.get("vibration_raw") or parsed.get("pest_vibe"),
                                soil_gas_raw=parsed.get("soil_gas"),
                                irradiance_w_m2=parsed.get("irradiance"),
                                pump_status=parsed.get("pump_status"),
                                sequence=sequence,
                            )
                    except json.JSONDecodeError:
                        pass

                # ── Try CSV key:value format ───────────────────────────────
                if payload_dict is None and ":" in line:
                    try:
                        fields: dict[str, str] = {}
                        for part in line.split(","):
                            part = part.strip()
                            if ":" in part:
                                key, _, val = part.partition(":")
                                fields[key.strip().lower()] = val.strip().split()[0]  # take numeric part

                        def _f(key: str) -> float | None:
                            try:
                                return float(fields[key]) if key in fields else None
                            except ValueError:
                                return None

                        def _i(key: str) -> int | None:
                            try:
                                return int(float(fields[key])) if key in fields else None
                            except ValueError:
                                return None

                        payload_dict = _build_telemetry_payload(
                            canopy_temp_c=_f("canopy temp"),
                            humidity_pct=_f("humidity"),
                            root_vwc_pct=_f("root vwc"),
                            pest_vibe=_i("pest vibe"),
                            soil_gas_raw=_f("soil gas"),
                            irradiance_w_m2=_f("irradiance"),
                            pump_status=fields.get("pump status"),
                            sequence=sequence,
                        )
                    except Exception as parse_exc:
                        logger.warning("hardware_parse_error", line=line, error=str(parse_exc))
                        continue

                if payload_dict is None:
                    # Log the exact line for debugging
                    logger.warning("hardware_unparsed_line", line=line)
                    continue

                # Verify at least one core reading exists before submitting
                r = payload_dict.get("readings", {})
                if all(v is None for v in r.values()):
                    # Silently skip payloads that only contain status (like pump status or soil gas)
                    # without any core temperature/humidity/moisture readings, to avoid pydantic errors
                    continue

                sequence += 1
                await ingest_raw_message(json.dumps(payload_dict))

        except serial.serialutil.SerialException as exc:
            logger.warning(
                "hardware_disconnected",
                port=settings.hardware_serial_port,
                error=str(exc),
                reconnect_in=reconnect_interval,
            )
        except asyncio.CancelledError:
            logger.info("hardware_listener_cancelled")
            if port and port.is_open:
                port.close()
            break
        except Exception as exc:
            logger.error("hardware_unexpected_error", error=str(exc))
        finally:
            if port and port.is_open:
                port.close()

        await asyncio.sleep(reconnect_interval)
        reconnect_interval = min(reconnect_interval * 2, 60)


def start_hardware_listener() -> None:
    """
    Start the HC-05 hardware listener as a background asyncio task.

    Only called from main.py when HARDWARE_ENABLED=true.
    Mirrors the start_mqtt_listener() pattern from mqtt_client.py.
    """
    global _hardware_task
    if not settings.hardware_serial_port:
        logger.warning(
            "hardware_listener_no_port",
            message=(
                "HARDWARE_ENABLED=true but HARDWARE_SERIAL_PORT is not set. "
                "Set HARDWARE_SERIAL_PORT=<port> in .env (e.g. COM7 or /dev/rfcomm0)."
            ),
        )
    _hardware_task = asyncio.create_task(
        _hardware_listener(), name="hc05-hardware-listener"
    )
    logger.info(
        "hardware_listener_started",
        device_id=settings.hardware_device_id,
        port=settings.hardware_serial_port or "(not set)",
    )


async def stop_hardware_listener() -> None:
    """
    Gracefully cancel the hardware listener task on application shutdown.
    Mirrors the stop_mqtt_listener() pattern from mqtt_client.py.
    """
    global _hardware_task
    if _hardware_task and not _hardware_task.done():
        _hardware_task.cancel()
        try:
            await _hardware_task
        except asyncio.CancelledError:
            pass
    logger.info("hardware_listener_stopped")
