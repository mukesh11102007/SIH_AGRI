"""
Decision Engine Orchestrator — coordinates all analyzers and produces
a unified FieldConditionSummary.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.telemetry import SensorReading
from app.models.crop import Crop
from app.models.field import Field
from app.models.device import Device
from app.models.recommendation import Recommendation
from app.models.alert import Alert
from app.schemas.responses import FieldConditionSummary
from app.services.decision_engine.irrigation import (
    IrrigationAnalyzer, IrrigationDecision, CropThresholds, Severity
)
from app.services.decision_engine.stress import (
    HeatStressDetector, WaterStressDetector,
    ExcessMoistureDetector, WaterAvailabilityTracker,
    ActivitySignalAnalyzer,
)
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Instantiate analyzers (stateless — safe to share)
_irrigation = IrrigationAnalyzer()
_heat = HeatStressDetector()
_water_stress = WaterStressDetector()
_excess_moisture = ExcessMoistureDetector()
_water_avail = WaterAvailabilityTracker()
_activity = ActivitySignalAnalyzer()


async def get_moisture_trend(
    db: AsyncSession,
    field_id: str,
    hours: int = 3,
) -> float | None:
    """
    Calculates soil moisture change rate (%/hour) over the last N hours.
    Positive = getting wetter, Negative = drying.
    Returns None if insufficient data (< 3 readings).
    """
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Get first and last reading in the window (time-ordered)
    result_first = await db.execute(
        select(SensorReading.soil_moisture_pct, SensorReading.received_at)
        .where(
            SensorReading.field_id == field_id,
            SensorReading.received_at >= cutoff,
            SensorReading.soil_moisture_pct.is_not(None),
            SensorReading.is_validated == True,
        )
        .order_by(SensorReading.received_at.asc())
        .limit(1)
    )
    first_row = result_first.one_or_none()

    result_last = await db.execute(
        select(SensorReading.soil_moisture_pct, SensorReading.received_at)
        .where(
            SensorReading.field_id == field_id,
            SensorReading.received_at >= cutoff,
            SensorReading.soil_moisture_pct.is_not(None),
            SensorReading.is_validated == True,
        )
        .order_by(SensorReading.received_at.desc())
        .limit(1)
    )
    last_row = result_last.one_or_none()

    # Count readings to ensure enough data
    count_result = await db.execute(
        select(func.count())
        .where(
            SensorReading.field_id == field_id,
            SensorReading.received_at >= cutoff,
            SensorReading.soil_moisture_pct.is_not(None),
            SensorReading.is_validated == True,
        )
    )
    count = count_result.scalar() or 0

    if count < 3 or first_row is None or last_row is None:
        return None

    duration_hours = (last_row[1] - first_row[1]).total_seconds() / 3600
    if duration_hours < 0.05:  # Less than 3 minutes
        return None

    # Positive = wetter, Negative = drying
    return (last_row[0] - first_row[0]) / duration_hours


async def analyze_field(
    db: AsyncSession,
    field: Field,
    latest_reading: SensorReading | None,
    device: Device | None,
) -> FieldConditionSummary:
    """
    Full field analysis: takes the latest sensor reading and produces
    a complete condition summary with all stress/risk evaluations.
    """
    # ── Crop thresholds ──────────────────────────────────────
    crop_thresholds = None
    crop_name = None
    if field.crop:
        c = field.crop
        crop_name = c.name
        crop_thresholds = CropThresholds(
            optimal_moisture_min_pct=c.optimal_moisture_min_pct,
            optimal_moisture_max_pct=c.optimal_moisture_max_pct,
            critical_moisture_min_pct=c.critical_moisture_min_pct,
            optimal_temp_max_c=c.optimal_temp_max_c,
            heat_stress_c=c.heat_stress_c,
            optimal_humidity_min_pct=c.optimal_humidity_min_pct,
        )

    # ── Device status ────────────────────────────────────────
    device_status = "never_seen"
    data_source = "no_data"
    last_updated = None

    if device and device.last_seen_at:
        now = datetime.now(timezone.utc)
        minutes_ago = (now - device.last_seen_at).total_seconds() / 60
        if minutes_ago <= settings.device_stale_minutes:
            device_status = "live"
        elif minutes_ago <= settings.device_offline_minutes:
            device_status = "stale"
        else:
            device_status = "offline"
        last_updated = device.last_seen_at

    if latest_reading:
        data_source = latest_reading.source
        if not last_updated:
            last_updated = latest_reading.received_at

    # ── No data case ─────────────────────────────────────────
    if latest_reading is None:
        return FieldConditionSummary(
            field_id=field.id,
            field_name=field.name,
            crop_name=crop_name,
            growth_stage=field.growth_stage,
            data_source=data_source,
            last_updated=last_updated,
            air_temperature_c=None,
            air_humidity_pct=None,
            soil_moisture_pct=None,
            soil_temperature_c=None,
            light_lux=None,
            leaf_wetness_pct=None,
            water_level_available=None,
            irrigation_status=IrrigationDecision.NORMAL.value,
            irrigation_severity=Severity.NONE.value,
            irrigation_reasoning="No sensor data available yet.",
            water_stress_level=Severity.NONE.value,
            heat_stress_level=Severity.NONE.value,
            excess_moisture_level=Severity.NONE.value,
            water_availability="unknown",
            activity_signal="normal",
            active_alert_count=0,
            device_status=device_status,
        )

    r = latest_reading

    # ── Moisture trend ───────────────────────────────────────
    trend = await get_moisture_trend(db, field.id)

    # ── Run all analyzers ────────────────────────────────────
    irrigation_result = _irrigation.analyze(
        soil_moisture_pct=r.soil_moisture_pct,
        air_temperature_c=r.air_temperature_c,
        air_humidity_pct=r.air_humidity_pct,
        soil_temperature_c=r.soil_temperature_c,
        light_lux=r.light_lux,
        leaf_wetness_pct=r.leaf_wetness_pct,
        water_level_available=r.water_level_available,
        crop=crop_thresholds,
        recent_trend=trend,
    )

    heat_result = _heat.analyze(
        air_temperature_c=r.air_temperature_c,
        soil_temperature_c=r.soil_temperature_c,
        air_humidity_pct=r.air_humidity_pct,
        light_lux=r.light_lux,
        heat_stress_threshold_c=crop_thresholds.heat_stress_c if crop_thresholds else 38.0,
    )

    water_stress_result = _water_stress.analyze(
        soil_moisture_pct=r.soil_moisture_pct,
        air_temperature_c=r.air_temperature_c,
        air_humidity_pct=r.air_humidity_pct,
        critical_moisture_min_pct=crop_thresholds.critical_moisture_min_pct if crop_thresholds else 20.0,
        optimal_moisture_min_pct=crop_thresholds.optimal_moisture_min_pct if crop_thresholds else 40.0,
    )

    excess_result = _excess_moisture.analyze(
        soil_moisture_pct=r.soil_moisture_pct,
        leaf_wetness_pct=r.leaf_wetness_pct,
        air_humidity_pct=r.air_humidity_pct,
        light_lux=r.light_lux,
    )

    water_avail_result = _water_avail.analyze(r.water_level_available)
    activity_result = _activity.analyze(r.vibration_raw, r.light_lux)

    # ── Water availability label ─────────────────────────────
    if r.water_level_available is True:
        water_availability = "available"
    elif r.water_level_available is False:
        water_availability = "unavailable"
    else:
        water_availability = "unknown"

    # ── Active alert count ───────────────────────────────────
    alert_count_result = await db.execute(
        select(func.count(Alert.id)).where(
            Alert.field_id == field.id,
            Alert.status == "active",
        )
    )
    active_alert_count = alert_count_result.scalar() or 0

    return FieldConditionSummary(
        field_id=field.id,
        field_name=field.name,
        crop_name=crop_name,
        growth_stage=field.growth_stage,
        data_source=data_source,
        last_updated=last_updated,
        air_temperature_c=r.air_temperature_c,
        air_humidity_pct=r.air_humidity_pct,
        soil_moisture_pct=r.soil_moisture_pct,
        soil_temperature_c=r.soil_temperature_c,
        light_lux=r.light_lux,
        leaf_wetness_pct=r.leaf_wetness_pct,
        water_level_available=r.water_level_available,
        irrigation_status=irrigation_result.decision.value,
        irrigation_severity=irrigation_result.severity.value,
        irrigation_reasoning=irrigation_result.reasoning,
        water_stress_level=water_stress_result.severity.value,
        heat_stress_level=heat_result.severity.value,
        excess_moisture_level=excess_result.severity.value,
        water_availability=water_availability,
        activity_signal="elevated" if activity_result.severity != Severity.NONE else "normal",
        active_alert_count=active_alert_count,
        device_status=device_status,
    )
