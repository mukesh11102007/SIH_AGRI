"""
Telemetry contract schemas — the normalized format that BOTH the simulator
and real ESP32 must produce.

Pydantic validates every incoming reading before it reaches the database.
This is the hardware abstraction boundary: source of data doesn't matter
as long as it conforms to this schema.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class SensorReadings(BaseModel):
    """Raw sensor values from the field device."""
    air_temperature_c: float | None = Field(None, ge=-40.0, le=80.0)
    air_humidity_pct: float | None = Field(None, ge=0.0, le=100.0)
    soil_moisture_pct: float | None = Field(None, ge=0.0, le=100.0)
    soil_temperature_c: float | None = Field(None, ge=-10.0, le=80.0)
    light_lux: float | None = Field(None, ge=0.0, le=150000.0)
    leaf_wetness_pct: float | None = Field(None, ge=0.0, le=100.0)
    vibration_raw: int | None = Field(None, ge=0, le=4095)
    water_level_available: bool | None = None


class SensorStatus(BaseModel):
    """Per-sensor status reported by the device firmware."""
    dht22: str = "ok"
    ds18b20: str = "ok"
    soil_moisture: str = "ok"
    bh1750: str = "ok"
    leaf_wetness: str = "ok"
    vibration: str = "ok"
    float_switch: str = "ok"


class TelemetryPayload(BaseModel):
    """
    The telemetry contract — the single normalized format for all data sources.

    Both simulator and ESP32 publish this structure to MQTT.
    The backend never needs to know which device produced the data
    beyond what is explicitly encoded here.
    """
    device_id: str = Field(..., min_length=1, max_length=128)
    farm_id: str = Field(..., min_length=1, max_length=64)
    field_id: str = Field(..., min_length=1, max_length=64)
    firmware_version: str | None = None
    timestamp_utc: datetime
    # "hc05" is reserved for future HC-05 Bluetooth hardware integration.
    # Add other hardware source identifiers here as they are introduced.
    source: Literal["simulator", "esp32", "esp32-cam-node", "hc05"] = "simulator"
    sequence_number: int | None = Field(None, ge=0)
    readings: SensorReadings
    sensor_status: SensorStatus = Field(default_factory=SensorStatus)

    @field_validator("device_id", "farm_id", "field_id")
    @classmethod
    def no_whitespace(cls, v: str) -> str:
        if " " in v:
            raise ValueError("IDs must not contain spaces")
        return v

    @model_validator(mode="after")
    def validate_readings_not_all_none(self) -> "TelemetryPayload":
        """Reject payloads where every sensor reading is None."""
        r = self.readings
        values = [
            r.air_temperature_c, r.air_humidity_pct, r.soil_moisture_pct,
            r.soil_temperature_c, r.light_lux, r.leaf_wetness_pct,
            r.vibration_raw, r.water_level_available,
        ]
        if all(v is None for v in values):
            raise ValueError("Telemetry payload must contain at least one sensor reading")
        return self


class ValidationResult(BaseModel):
    """Result of the telemetry validation pipeline."""
    is_valid: bool
    flags: dict[str, str] = Field(default_factory=dict)
    # flags example: {"air_temperature_c": "out_of_range", "dht22": "sensor_error"}

    @property
    def has_warnings(self) -> bool:
        return bool(self.flags)
