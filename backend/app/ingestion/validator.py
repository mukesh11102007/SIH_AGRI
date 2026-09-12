"""
Telemetry Validation Pipeline.

Validates incoming telemetry payloads for:
- Range violations (impossible sensor values)
- Sensor-reported errors
- Stale timestamps
- Missing critical readings

Returns a ValidationResult with flags explaining every issue found.
This layer keeps raw and validated data clearly separated.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Any

from app.schemas.telemetry import TelemetryPayload, ValidationResult
from app.core.logging import get_logger

logger = get_logger(__name__)

# Maximum age of a telemetry reading before it is considered stale
MAX_READING_AGE_MINUTES = 10

# Sensor physical limits (beyond what Pydantic already catches)
SENSOR_RANGES = {
    "air_temperature_c": (-40.0, 80.0),
    "air_humidity_pct": (0.0, 100.0),
    "soil_moisture_pct": (0.0, 100.0),
    "soil_temperature_c": (-10.0, 80.0),
    "light_lux": (0.0, 150000.0),
    "leaf_wetness_pct": (0.0, 100.0),
    "vibration_raw": (0, 4095),
}

# Suspicious value combinations
SUSPICIOUS_COMBINATIONS = [
    # High humidity + very low leaf wetness might indicate sensor issue
    # (We flag these as warnings, not hard failures)
]


def validate_telemetry(payload: TelemetryPayload) -> ValidationResult:
    """
    Validates a parsed TelemetryPayload.

    Returns a ValidationResult with:
    - is_valid: False only for hard failures (no valid data at all)
    - flags: warnings and notes about specific sensor readings
    """
    flags: dict[str, str] = {}
    r = payload.readings
    ss = payload.sensor_status

    # ── 1. Timestamp staleness ───────────────────────────────
    now = datetime.now(timezone.utc)
    ts = payload.timestamp_utc
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age_seconds = (now - ts).total_seconds()
    if age_seconds > MAX_READING_AGE_MINUTES * 60 or age_seconds < -60:
        # Too old OR from the future (>1 minute ahead = clock drift)
        flags["timestamp"] = f"stale_or_future_{int(age_seconds)}s"
        logger.warning("telemetry_stale_timestamp", device=payload.device_id, age_seconds=age_seconds)

    # ── 2. Sensor status checks ──────────────────────────────
    sensor_status_map = {
        "dht22": ["air_temperature_c", "air_humidity_pct"],
        "ds18b20": ["soil_temperature_c"],
        "soil_moisture": ["soil_moisture_pct"],
        "bh1750": ["light_lux"],
        "leaf_wetness": ["leaf_wetness_pct"],
        "vibration": ["vibration_raw"],
        "float_switch": ["water_level_available"],
    }

    for sensor_name, reading_fields in sensor_status_map.items():
        sensor_st = getattr(ss, sensor_name, "ok")
        if sensor_st not in ("ok", "OK"):
            flags[sensor_name] = f"sensor_status_{sensor_st}"
            # Mark affected readings as flagged
            for rf in reading_fields:
                flags[rf] = "sensor_error"

    # ── 3. Range validation (secondary — Pydantic is primary) ──
    readings_dict: dict[str, Any] = {
        "air_temperature_c": r.air_temperature_c,
        "air_humidity_pct": r.air_humidity_pct,
        "soil_moisture_pct": r.soil_moisture_pct,
        "soil_temperature_c": r.soil_temperature_c,
        "light_lux": r.light_lux,
        "leaf_wetness_pct": r.leaf_wetness_pct,
        "vibration_raw": r.vibration_raw,
    }

    for field_name, value in readings_dict.items():
        if value is None or field_name in flags:
            continue
        min_val, max_val = SENSOR_RANGES[field_name]
        if not (min_val <= value <= max_val):
            flags[field_name] = "out_of_range"

    # ── 4. Hard failure — all readings None ──────────────────
    all_none = all(
        v is None for v in [
            r.air_temperature_c, r.air_humidity_pct, r.soil_moisture_pct,
            r.soil_temperature_c, r.light_lux, r.leaf_wetness_pct,
            r.vibration_raw, r.water_level_available,
        ]
    )
    if all_none:
        logger.error("telemetry_all_readings_none", device=payload.device_id)
        return ValidationResult(is_valid=False, flags={"all_readings": "all_none"})

    if flags:
        logger.debug("telemetry_validation_flags", device=payload.device_id, flags=flags)

    return ValidationResult(is_valid=True, flags=flags)
