"""Analytics API — historical summaries and trends."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.api.deps import get_db
from app.models.telemetry import SensorReading
from app.models.alert import Alert

router = APIRouter()


@router.get(
    "/fields/{field_id}/analytics/summary",
    tags=["Analytics"],
    summary="24h statistical summary for a field",
)
async def get_field_analytics(
    field_id: str,
    hours: int = Query(24, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    result = await db.execute(
        select(
            func.count(SensorReading.id).label("reading_count"),
            func.avg(SensorReading.air_temperature_c).label("avg_temp"),
            func.min(SensorReading.air_temperature_c).label("min_temp"),
            func.max(SensorReading.air_temperature_c).label("max_temp"),
            func.avg(SensorReading.air_humidity_pct).label("avg_humidity"),
            func.avg(SensorReading.soil_moisture_pct).label("avg_soil_moisture"),
            func.min(SensorReading.soil_moisture_pct).label("min_soil_moisture"),
            func.max(SensorReading.soil_moisture_pct).label("max_soil_moisture"),
            func.avg(SensorReading.light_lux).label("avg_light"),
            func.max(SensorReading.light_lux).label("max_light"),
        )
        .where(
            SensorReading.field_id == field_id,
            SensorReading.received_at >= cutoff,
            SensorReading.is_validated == True,
        )
    )
    row = result.one()

    # Alert counts
    alert_result = await db.execute(
        select(Alert.severity, func.count(Alert.id).label("count"))
        .where(Alert.field_id == field_id, Alert.created_at >= cutoff)
        .group_by(Alert.severity)
    )
    alert_counts = {r.severity: r.count for r in alert_result.all()}

    def _r(v: float | None, decimals: int = 1) -> float | None:
        return round(v, decimals) if v is not None else None

    return {
        "field_id": field_id,
        "period_hours": hours,
        "reading_count": row.reading_count or 0,
        "temperature": {
            "avg_c": _r(row.avg_temp),
            "min_c": _r(row.min_temp),
            "max_c": _r(row.max_temp),
        },
        "humidity": {
            "avg_pct": _r(row.avg_humidity),
        },
        "soil_moisture": {
            "avg_pct": _r(row.avg_soil_moisture),
            "min_pct": _r(row.min_soil_moisture),
            "max_pct": _r(row.max_soil_moisture),
        },
        "light": {
            "avg_lux": _r(row.avg_light, 0),
            "max_lux": _r(row.max_light, 0),
        },
        "alerts": {
            "critical": alert_counts.get("critical", 0),
            "warning": alert_counts.get("warning", 0),
            "info": alert_counts.get("info", 0),
            "total": sum(alert_counts.values()),
        },
    }


@router.get(
    "/fields/{field_id}/analytics/chart",
    tags=["Analytics"],
    summary="Time-series chart data for a field",
)
async def get_chart_data(
    field_id: str,
    hours: int = Query(24, ge=1, le=168),
    sensor: str = Query("soil_moisture_pct", description="Sensor field name"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Returns downsampled time-series data suitable for frontend charts."""
    ALLOWED_SENSORS = {
        "air_temperature_c", "air_humidity_pct", "soil_moisture_pct",
        "soil_temperature_c", "light_lux", "leaf_wetness_pct",
    }
    if sensor not in ALLOWED_SENSORS:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Sensor must be one of: {', '.join(ALLOWED_SENSORS)}")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    sensor_col = getattr(SensorReading, sensor)

    result = await db.execute(
        select(SensorReading.received_at, sensor_col)
        .where(
            SensorReading.field_id == field_id,
            SensorReading.received_at >= cutoff,
            SensorReading.is_validated == True,
            sensor_col.is_not(None),
        )
        .order_by(SensorReading.received_at)
        .limit(1000)
    )
    rows = result.all()

    return {
        "field_id": field_id,
        "sensor": sensor,
        "period_hours": hours,
        "points": [
            {"t": r[0].isoformat(), "v": round(r[1], 2)}
            for r in rows
        ],
    }


from pydantic import BaseModel

class EnvRiskRequest(BaseModel):
    crop_type: str
    temp: float
    hum: float
    sm: float
    pressure: float
    solar: float
    organic_gas: float
    pest_vib: float

@router.post(
    "/predict/env-risk",
    tags=["Analytics", "ML"],
    summary="Predict environmental risk based on sensor data",
)
async def predict_env_risk(
    req: EnvRiskRequest,
) -> dict[str, Any]:
    from app.ml.registry import get_registry
    registry = get_registry()
    
    result = await registry.predict("env_risk", req.model_dump())
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Environmental Risk model unavailable")
        
    return {
        "prediction": result.prediction,
        "confidence": result.confidence,
        "is_stub": result.is_stub,
    }
