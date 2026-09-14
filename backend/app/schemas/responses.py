"""Pydantic schemas for Alerts and Recommendations API responses."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel


# ── Alert ─────────────────────────────────────────────────────────────────────

class AlertRead(BaseModel):
    id: str
    field_id: str
    device_id: str | None
    alert_type: str
    severity: Literal["info", "warning", "critical"]
    title: str
    explanation: str
    recommended_action: str | None
    contributing_factors: dict[str, Any] | None
    status: Literal["active", "acknowledged", "resolved", "expired"]
    created_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class AlertAcknowledge(BaseModel):
    alert_id: str


# ── Recommendation ────────────────────────────────────────────────────────────

class RecommendationRead(BaseModel):
    id: str
    field_id: str
    recommendation_type: str
    decision: str
    severity: str
    reasoning: str
    contributing_factors: dict[str, Any] | None
    generated_by: str
    confidence_pct: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Device ────────────────────────────────────────────────────────────────────

class DeviceRead(BaseModel):
    id: str
    field_id: str
    device_identifier: str
    source_type: str
    firmware_version: str | None
    last_seen_at: datetime | None
    is_active: bool
    connectivity_status: str  # "live" | "stale" | "offline" | "never_seen"
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Sensor reading (API response) ─────────────────────────────────────────────

class SensorReadingRead(BaseModel):
    id: str
    device_id: str
    field_id: str
    received_at: datetime
    device_timestamp: datetime | None
    source: str
    air_temperature_c: float | None
    air_humidity_pct: float | None
    soil_moisture_pct: float | None
    soil_temperature_c: float | None
    light_lux: float | None
    leaf_wetness_pct: float | None
    vibration_raw: int | None
    water_level_available: bool | None
    is_validated: bool
    validation_flags: dict[str, Any] | None

    model_config = {"from_attributes": True}


# ── Dashboard summary ─────────────────────────────────────────────────────────

class FieldConditionSummary(BaseModel):
    """Complete current condition summary for a field — dashboard payload."""
    field_id: str
    field_name: str
    crop_name: str | None
    growth_stage: str | None
    data_source: str  # "simulation" | "esp32" | "no_data"
    last_updated: datetime | None

    # Latest sensor values (human-readable)
    air_temperature_c: float | None
    air_humidity_pct: float | None
    soil_moisture_pct: float | None
    soil_temperature_c: float | None
    light_lux: float | None
    leaf_wetness_pct: float | None
    vibration_raw: int | None
    soil_gas_raw: float | None
    water_level_available: bool | None

    # Conditions
    irrigation_status: str        # decision code
    irrigation_severity: str      # none|low|medium|high|critical
    irrigation_reasoning: str

    water_stress_level: str       # none|low|medium|high|critical
    heat_stress_level: str
    excess_moisture_level: str
    water_availability: str       # available|low|unavailable|unknown

    # Activity signal — explicitly NOT pest identification
    activity_signal: str          # normal|elevated

    # Active alert count
    active_alert_count: int

    # Device status
    device_status: str            # live|stale|offline|never_seen

    # Simple Rule-based Advice
    ai_advice: str | None = None


class WebSocketMessage(BaseModel):
    """Structure of messages pushed over WebSocket to the frontend."""
    event: str  # "sensor_update" | "new_alert" | "recommendation_update" | "device_status"
    field_id: str
    data: dict[str, Any]
    timestamp: datetime
