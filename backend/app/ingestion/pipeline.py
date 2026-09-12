"""
Telemetry Ingestion Pipeline.

Orchestrates the full path from a raw MQTT message to:
1. Pydantic parsing + validation
2. Device registration/lookup
3. Persistence to TimescaleDB
4. Decision engine analysis
5. Alert/recommendation persistence
6. WebSocket broadcast to connected frontend clients
"""
from __future__ import annotations
import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.telemetry import TelemetryPayload
from app.ingestion.validator import validate_telemetry
from app.models.telemetry import SensorReading
from app.models.device import Device
from app.models.field import Field
from app.models.farm import Farm
from app.services.decision_engine.orchestrator import analyze_field
from app.services.decision_engine.irrigation import IrrigationAnalyzer, CropThresholds
from app.services.decision_engine.stress import (
    HeatStressDetector, WaterStressDetector,
    ExcessMoistureDetector, WaterAvailabilityTracker,
    ActivitySignalAnalyzer,
)
from app.services.alert_service import (
    process_irrigation_alert, process_stress_alert, save_recommendation
)
from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger

logger = get_logger(__name__)

_irrigation_analyzer = IrrigationAnalyzer()
_heat_detector = HeatStressDetector()
_water_stress_detector = WaterStressDetector()
_excess_detector = ExcessMoistureDetector()
_water_avail_tracker = WaterAvailabilityTracker()
_activity_analyzer = ActivitySignalAnalyzer()


async def _analyze_and_broadcast_only(
    payload: TelemetryPayload,
    validation_flags: dict,
) -> None:
    """Run decision engine and broadcast live data without saving to DB."""
    r = payload.readings

    # Run decision engine with default crop thresholds (no DB to load specific crop)
    irrigation_result = _irrigation_analyzer.analyze(
        soil_moisture_pct=r.soil_moisture_pct,
        air_temperature_c=r.air_temperature_c,
        air_humidity_pct=r.air_humidity_pct,
        soil_temperature_c=r.soil_temperature_c,
        light_lux=r.light_lux,
        leaf_wetness_pct=r.leaf_wetness_pct,
        water_level_available=r.water_level_available,
        crop=None,
    )

    # ── WebSocket broadcast ──────────────────────────────────
    from app.websocket.manager import broadcast_field_update
    await broadcast_field_update(payload.field_id, {
        "event": "sensor_update",
        "field_id": payload.field_id,
        "irrigation_status": irrigation_result.decision.value,
        "irrigation_severity": irrigation_result.severity.value,
        "soil_moisture_pct": r.soil_moisture_pct,
        "air_temperature_c": r.air_temperature_c,
        "air_humidity_pct": r.air_humidity_pct,
        "water_level_available": r.water_level_available,
        "source": payload.source,
    })

    logger.info(
        "telemetry_processed_nodb",
        device=payload.device_id,
        field=payload.field_id,
        irrigation=irrigation_result.decision.value,
    )


async def ingest_raw_message(raw_payload: str | bytes) -> bool:
    """
    Entry point for MQTT messages.
    Parses, validates, persists, and triggers analysis.
    Returns True on success.
    """
    # ── 1. Parse ─────────────────────────────────────────────
    try:
        data = json.loads(raw_payload)
        payload = TelemetryPayload.model_validate(data)
    except Exception as exc:
        logger.error("telemetry_parse_error", error=str(exc), raw=str(raw_payload)[:200])
        return False

    logger.debug(
        "telemetry_received",
        device=payload.device_id,
        source=payload.source,
        field=payload.field_id,
    )

    # ── 2. Validate ──────────────────────────────────────────
    validation = validate_telemetry(payload)
    if not validation.is_valid:
        logger.warning("telemetry_invalid", device=payload.device_id, flags=validation.flags)
        return False

    # ── 3. Persist + Analyze ─────────────────────────────────
    import os
    db_available = os.environ.get("SMARTFARM_DB_AVAILABLE", "0") == "1"

    if db_available:
        async with AsyncSessionLocal() as db:
            try:
                await _persist_and_analyze(db, payload, validation.flags)
                await db.commit()
                return True
            except Exception as exc:
                await db.rollback()
                logger.error("telemetry_ingestion_error", error=str(exc), device=payload.device_id)
                return False
    else:
        # No-DB mode: run decision engine and broadcast without persistence
        try:
            await _analyze_and_broadcast_only(payload, validation.flags)
            return True
        except Exception as exc:
            logger.error("telemetry_nodb_error", error=str(exc), device=payload.device_id)
            return False


async def _persist_and_analyze(
    db: AsyncSession,
    payload: TelemetryPayload,
    validation_flags: dict,
) -> None:
    """Persist the reading and run the decision engine."""

    # ── Find or auto-register device ────────────────────────
    device_result = await db.execute(
        select(Device).where(Device.device_identifier == payload.device_id)
    )
    device = device_result.scalar_one_or_none()

    if device is None:
        # Auto-register unknown device — link to the field/farm from payload
        field = await _get_or_create_field(db, payload)
        device = Device(
            field_id=field.id,
            device_identifier=payload.device_id,
            source_type=payload.source,
            firmware_version=payload.firmware_version,
            last_seen_at=datetime.now(timezone.utc),
            is_active=True,
        )
        db.add(device)
        await db.flush()
        logger.info("device_auto_registered", identifier=payload.device_id, source=payload.source)
    else:
        device.last_seen_at = datetime.now(timezone.utc)
        device.source_type = payload.source
        if payload.firmware_version:
            device.firmware_version = payload.firmware_version
        await db.flush()

    # ── Persist reading ──────────────────────────────────────
    r = payload.readings
    reading = SensorReading(
        device_id=device.id,
        field_id=device.field_id,
        received_at=datetime.now(timezone.utc),
        device_timestamp=payload.timestamp_utc,
        source=payload.source,
        sequence_number=payload.sequence_number,
        air_temperature_c=r.air_temperature_c,
        air_humidity_pct=r.air_humidity_pct,
        soil_moisture_pct=r.soil_moisture_pct,
        soil_temperature_c=r.soil_temperature_c,
        light_lux=r.light_lux,
        leaf_wetness_pct=r.leaf_wetness_pct,
        vibration_raw=r.vibration_raw,
        water_level_available=r.water_level_available,
        is_validated=True,
        validation_flags=validation_flags if validation_flags else None,
        sensor_status=payload.sensor_status.model_dump(),
    )
    db.add(reading)
    await db.flush()

    # ── Load field with crop for decision engine ─────────────
    field_result = await db.execute(
        select(Field).where(Field.id == device.field_id)
    )
    field = field_result.scalar_one_or_none()
    if not field:
        return

    # Eager load crop
    from sqlalchemy.orm import selectinload
    field_with_crop = await db.execute(
        select(Field).options(selectinload(Field.crop)).where(Field.id == device.field_id)
    )
    field = field_with_crop.scalar_one_or_none()

    # ── Decision engine ──────────────────────────────────────
    crop_thresholds = None
    if field and field.crop:
        c = field.crop
        crop_thresholds = CropThresholds(
            optimal_moisture_min_pct=c.optimal_moisture_min_pct,
            optimal_moisture_max_pct=c.optimal_moisture_max_pct,
            critical_moisture_min_pct=c.critical_moisture_min_pct,
            optimal_temp_max_c=c.optimal_temp_max_c,
            heat_stress_c=c.heat_stress_c,
            optimal_humidity_min_pct=c.optimal_humidity_min_pct,
        )

    irrigation_result = _irrigation_analyzer.analyze(
        soil_moisture_pct=r.soil_moisture_pct,
        air_temperature_c=r.air_temperature_c,
        air_humidity_pct=r.air_humidity_pct,
        soil_temperature_c=r.soil_temperature_c,
        light_lux=r.light_lux,
        leaf_wetness_pct=r.leaf_wetness_pct,
        water_level_available=r.water_level_available,
        crop=crop_thresholds,
    )

    heat_result = _heat_detector.analyze(
        air_temperature_c=r.air_temperature_c,
        soil_temperature_c=r.soil_temperature_c,
        air_humidity_pct=r.air_humidity_pct,
        light_lux=r.light_lux,
    )

    water_stress_result = _water_stress_detector.analyze(
        soil_moisture_pct=r.soil_moisture_pct,
        air_temperature_c=r.air_temperature_c,
        air_humidity_pct=r.air_humidity_pct,
    )

    excess_result = _excess_detector.analyze(
        soil_moisture_pct=r.soil_moisture_pct,
        leaf_wetness_pct=r.leaf_wetness_pct,
        air_humidity_pct=r.air_humidity_pct,
        light_lux=r.light_lux,
    )

    water_avail_result = _water_avail_tracker.analyze(r.water_level_available)
    activity_result = _activity_analyzer.analyze(r.vibration_raw, r.light_lux)

    # ── Persist alerts ───────────────────────────────────────
    await process_irrigation_alert(db, device.field_id, device.id, irrigation_result)
    await process_stress_alert(db, device.field_id, device.id, heat_result)
    await process_stress_alert(db, device.field_id, device.id, water_stress_result)
    await process_stress_alert(db, device.field_id, device.id, excess_result)
    await process_stress_alert(db, device.field_id, device.id, water_avail_result)

    # ── Persist recommendation ───────────────────────────────
    await save_recommendation(db, device.field_id, irrigation_result)

    # ── WebSocket broadcast ──────────────────────────────────
    from app.websocket.manager import broadcast_field_update
    await broadcast_field_update(device.field_id, {
        "event": "sensor_update",
        "field_id": device.field_id,
        "irrigation_status": irrigation_result.decision.value,
        "irrigation_severity": irrigation_result.severity.value,
        "soil_moisture_pct": r.soil_moisture_pct,
        "air_temperature_c": r.air_temperature_c,
        "air_humidity_pct": r.air_humidity_pct,
        "water_level_available": r.water_level_available,
        "source": payload.source,
    })

    logger.info(
        "telemetry_processed",
        device=payload.device_id,
        field=device.field_id,
        irrigation=irrigation_result.decision.value,
    )


async def _get_or_create_field(db: AsyncSession, payload: TelemetryPayload) -> Field:
    """Find or create field based on payload IDs."""
    field_result = await db.execute(
        select(Field).where(Field.id == payload.field_id)
    )
    field = field_result.scalar_one_or_none()
    if field:
        return field

    # Ensure farm exists
    farm_result = await db.execute(select(Farm).where(Farm.id == payload.farm_id))
    farm = farm_result.scalar_one_or_none()
    if not farm:
        farm = Farm(id=payload.farm_id, name=f"Farm {payload.farm_id}", timezone="Asia/Kolkata")
        db.add(farm)
        await db.flush()

    field = Field(id=payload.field_id, farm_id=farm.id, name=f"Field {payload.field_id}")
    db.add(field)
    await db.flush()
    return field




