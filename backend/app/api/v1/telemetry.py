"""Telemetry, Dashboard, and Field Condition API routes."""
from __future__ import annotations
import os
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.models.telemetry import SensorReading
from app.models.field import Field
from app.models.device import Device
from app.schemas.responses import SensorReadingRead, FieldConditionSummary
from app.services.decision_engine.orchestrator import analyze_field
from app.core.config import settings

router = APIRouter()

_DB_AVAILABLE = lambda: os.environ.get("SMARTFARM_DB_AVAILABLE", "0") == "1"


def _no_db_condition(field_id: str) -> dict:
    """Return a minimal dashboard stub when DB is unavailable."""
    return {
        "field_id": field_id,
        "field_name": "North Field",
        "farm_id": settings.hardware_farm_id if hasattr(settings, "hardware_farm_id") else "farm-001",
        "crop_name": None,
        "growth_stage": None,
        "last_updated": None,
        "latest_reading": None,
        "irrigation": {
            "decision": "UNKNOWN",
            "severity": "INFO",
            "confidence": 0.0,
            "reasons": ["Database unavailable — live hardware data streams via WebSocket"],
            "recommended_duration_min": None,
        },
        "stress_events": [],
        "device": None,
        "data_source": "no_db_mode",
    }


@router.get(
    "/fields/{field_id}/readings",
    response_model=list[SensorReadingRead],
    tags=["Telemetry"],
    summary="Historical sensor readings for a field",
)
async def get_field_readings(
    field_id: str,
    hours: int = Query(24, ge=1, le=720, description="Hours of history to return"),
    limit: int = Query(500, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
) -> list[SensorReading]:
    if not _DB_AVAILABLE():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = await db.execute(
        select(SensorReading)
        .where(
            SensorReading.field_id == field_id,
            SensorReading.received_at >= cutoff,
            SensorReading.is_validated == True,
        )
        .order_by(desc(SensorReading.received_at))
        .limit(limit)
    )
    return result.scalars().all()


@router.get(
    "/fields/{field_id}/readings/latest",
    tags=["Telemetry"],
    summary="Most recent validated sensor reading for a field",
)
async def get_latest_reading(
    field_id: str,
    db: AsyncSession = Depends(get_db),
):
    if not _DB_AVAILABLE():
        return None
    result = await db.execute(
        select(SensorReading)
        .where(
            SensorReading.field_id == field_id,
            SensorReading.is_validated == True,
        )
        .order_by(desc(SensorReading.received_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.get(
    "/fields/{field_id}/condition",
    tags=["Dashboard"],
    summary="Complete current condition summary for a field — powers the dashboard",
)
async def get_field_condition(
    field_id: str,
    db: AsyncSession = Depends(get_db),
):
    if not _DB_AVAILABLE():
        return _no_db_condition(field_id)

    # Load field with crop
    field_result = await db.execute(
        select(Field)
        .options(selectinload(Field.crop))
        .where(Field.id == field_id)
    )
    field = field_result.scalar_one_or_none()
    if not field:
        return _no_db_condition(field_id)

    # Latest reading
    reading_result = await db.execute(
        select(SensorReading)
        .where(SensorReading.field_id == field_id, SensorReading.is_validated == True)
        .order_by(desc(SensorReading.received_at))
        .limit(1)
    )
    latest = reading_result.scalar_one_or_none()

    # Primary device
    device_result = await db.execute(
        select(Device)
        .where(Device.field_id == field_id, Device.is_active == True)
        .order_by(desc(Device.last_seen_at))
        .limit(1)
    )
    device = device_result.scalar_one_or_none()

    return await analyze_field(db, field, latest, device)


@router.get(
    "/farms/{farm_id}/dashboard",
    tags=["Dashboard"],
    summary="Dashboard summaries for all fields in a farm",
)
async def get_farm_dashboard(
    farm_id: str,
    db: AsyncSession = Depends(get_db),
):
    if not _DB_AVAILABLE():
        return [_no_db_condition("field-north-01")]

    fields_result = await db.execute(
        select(Field)
        .options(selectinload(Field.crop))
        .where(Field.farm_id == farm_id)
    )
    fields = fields_result.scalars().all()

    if not fields:
        return [_no_db_condition("field-north-01")]

    summaries = []
    for field in fields:
        reading_result = await db.execute(
            select(SensorReading)
            .where(SensorReading.field_id == field.id, SensorReading.is_validated == True)
            .order_by(desc(SensorReading.received_at))
            .limit(1)
        )
        latest = reading_result.scalar_one_or_none()

        device_result = await db.execute(
            select(Device)
            .where(Device.field_id == field.id, Device.is_active == True)
            .order_by(desc(Device.last_seen_at))
            .limit(1)
        )
        device = device_result.scalar_one_or_none()

        summaries.append(await analyze_field(db, field, latest, device))

    return summaries

