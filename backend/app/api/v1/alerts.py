"""Alerts and Recommendations REST API routes."""
from __future__ import annotations
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update

from app.api.deps import get_db
from app.models.alert import Alert
from app.models.recommendation import Recommendation
from app.schemas.responses import AlertRead, RecommendationRead

router = APIRouter()


# ── Alerts ────────────────────────────────────────────────────────────────────

@router.get(
    "/fields/{field_id}/alerts",
    response_model=list[AlertRead],
    tags=["Alerts"],
)
async def get_field_alerts(
    field_id: str,
    status: str | None = Query(None, description="Filter by status: active|acknowledged|resolved"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[Alert]:
    q = select(Alert).where(Alert.field_id == field_id)
    if status:
        q = q.where(Alert.status == status)
    q = q.order_by(desc(Alert.created_at)).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/farms/{farm_id}/alerts", response_model=list[AlertRead], tags=["Alerts"])
async def get_farm_alerts(
    farm_id: str,
    status: str | None = Query("active"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[Alert]:
    from app.models.field import Field
    fields_result = await db.execute(
        select(Field.id).where(Field.farm_id == farm_id)
    )
    field_ids = [r[0] for r in fields_result.all()]
    if not field_ids:
        return []

    q = select(Alert).where(Alert.field_id.in_(field_ids))
    if status:
        q = q.where(Alert.status == status)
    q = q.order_by(desc(Alert.created_at)).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertRead, tags=["Alerts"])
async def acknowledge_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
) -> Alert:
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.post("/alerts/{alert_id}/resolve", response_model=AlertRead, tags=["Alerts"])
async def resolve_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
) -> Alert:
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = "resolved"
    alert.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    return alert


# ── Recommendations ───────────────────────────────────────────────────────────

@router.get(
    "/fields/{field_id}/recommendations",
    response_model=list[RecommendationRead],
    tags=["Recommendations"],
)
async def get_field_recommendations(
    field_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[Recommendation]:
    result = await db.execute(
        select(Recommendation)
        .where(Recommendation.field_id == field_id)
        .order_by(desc(Recommendation.created_at))
        .limit(limit)
    )
    return result.scalars().all()


@router.get(
    "/fields/{field_id}/recommendations/current",
    response_model=RecommendationRead | None,
    tags=["Recommendations"],
)
async def get_current_recommendation(
    field_id: str,
    db: AsyncSession = Depends(get_db),
) -> Recommendation | None:
    result = await db.execute(
        select(Recommendation)
        .where(
            Recommendation.field_id == field_id,
            Recommendation.recommendation_type == "irrigation",
        )
        .order_by(desc(Recommendation.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()
