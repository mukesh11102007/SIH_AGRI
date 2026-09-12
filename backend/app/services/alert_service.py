"""
Alert Service — creates and manages farm condition alerts.

Converts decision engine results into persistent Alert records.
Avoids duplicate active alerts for the same condition.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.alert import Alert
from app.models.recommendation import Recommendation
from app.services.decision_engine.irrigation import IrrigationDecision, IrrigationResult, Severity
from app.services.decision_engine.stress import StressResult
from app.core.logging import get_logger

logger = get_logger(__name__)


async def _get_active_alert(
    db: AsyncSession, field_id: str, alert_type: str
) -> Alert | None:
    result = await db.execute(
        select(Alert).where(
            Alert.field_id == field_id,
            Alert.alert_type == alert_type,
            Alert.status == "active",
        ).limit(1)
    )
    return result.scalars().first()


def _severity_to_db(severity: Severity) -> str:
    mapping = {
        Severity.NONE: "info",
        Severity.LOW: "info",
        Severity.MEDIUM: "warning",
        Severity.HIGH: "warning",
        Severity.CRITICAL: "critical",
    }
    return mapping.get(severity, "info")


async def process_irrigation_alert(
    db: AsyncSession,
    field_id: str,
    device_id: str | None,
    result: IrrigationResult,
) -> Alert | None:
    """Create/update irrigation alert based on decision engine result."""
    alert_type = "irrigation"

    # Resolve existing alert if conditions are normal
    if result.decision in (IrrigationDecision.NORMAL, IrrigationDecision.EXCESS_MOISTURE):
        existing = await _get_active_alert(db, field_id, alert_type)
        if existing:
            existing.status = "resolved"
            existing.resolved_at = datetime.now(timezone.utc)
            await db.flush()
        return None

    if result.severity in (Severity.NONE, Severity.LOW):
        return None  # Don't create alerts for low severity

    # Check for existing active alert of same type
    existing = await _get_active_alert(db, field_id, alert_type)
    if existing:
        # Update existing alert rather than creating duplicate
        existing.severity = _severity_to_db(result.severity)
        existing.explanation = result.reasoning
        existing.contributing_factors = result.contributing_factors
        await db.flush()
        return existing

    title_map = {
        IrrigationDecision.IRRIGATION_RECOMMENDED: "Irrigation Recommended",
        IrrigationDecision.IRRIGATION_BLOCKED: "Irrigation Blocked — Water Unavailable",
        IrrigationDecision.MONITOR: "Monitor Soil Moisture",
    }

    alert = Alert(
        field_id=field_id,
        device_id=device_id,
        alert_type=alert_type,
        severity=_severity_to_db(result.severity),
        title=title_map.get(result.decision, "Irrigation Alert"),
        explanation=result.reasoning,
        recommended_action=_get_irrigation_action(result.decision),
        contributing_factors=result.contributing_factors,
        status="active",
    )
    db.add(alert)
    await db.flush()
    logger.info("alert_created", type=alert_type, severity=alert.severity, field=field_id)
    return alert


async def process_stress_alert(
    db: AsyncSession,
    field_id: str,
    device_id: str | None,
    result: StressResult,
) -> Alert | None:
    """Create/update stress alert from a StressResult."""
    existing = await _get_active_alert(db, field_id, result.condition)

    if result.severity == Severity.NONE:
        if existing:
            existing.status = "resolved"
            existing.resolved_at = datetime.now(timezone.utc)
            await db.flush()
        return None

    if result.severity == Severity.LOW and result.condition != "water_availability":
        return None  # Skip low-severity stress alerts to avoid noise

    if existing:
        existing.severity = _severity_to_db(result.severity)
        existing.title = result.title
        existing.explanation = result.explanation
        existing.recommended_action = result.recommended_action
        existing.contributing_factors = result.contributing_factors
        await db.flush()
        return existing

    alert = Alert(
        field_id=field_id,
        device_id=device_id,
        alert_type=result.condition,
        severity=_severity_to_db(result.severity),
        title=result.title,
        explanation=result.explanation,
        recommended_action=result.recommended_action,
        contributing_factors=result.contributing_factors,
        status="active",
    )
    db.add(alert)
    await db.flush()
    logger.info("alert_created", type=result.condition, severity=alert.severity, field=field_id)
    return alert


RECOMMENDATION_DEDUP_MINUTES = 5  # Minimum gap between identical recommendations


async def save_recommendation(
    db: AsyncSession,
    field_id: str,
    result: IrrigationResult,
) -> Recommendation | None:
    """
    Persist an irrigation recommendation with deduplication.

    Only creates a new record if:
    - The decision changed from the previous recommendation, OR
    - More than RECOMMENDATION_DEDUP_MINUTES have passed since the last one.

    This prevents flooding the table with identical records every sensor cycle.
    """
    from datetime import timedelta
    from sqlalchemy import desc

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=RECOMMENDATION_DEDUP_MINUTES)

    # Check most recent recommendation for this field
    recent_result = await db.execute(
        select(Recommendation)
        .where(
            Recommendation.field_id == field_id,
            Recommendation.recommendation_type == "irrigation",
        )
        .order_by(desc(Recommendation.created_at))
        .limit(1)
    )
    recent = recent_result.scalars().first()

    if recent:
        # Skip if same decision AND within dedup window
        if recent.decision == result.decision.value and recent.created_at >= cutoff:
            return None

    rec = Recommendation(
        field_id=field_id,
        recommendation_type="irrigation",
        decision=result.decision.value,
        severity=result.severity.value,
        reasoning=result.reasoning,
        contributing_factors=result.contributing_factors,
        generated_by="rule_engine",
    )
    db.add(rec)
    await db.flush()
    return rec


def _get_irrigation_action(decision: IrrigationDecision) -> str | None:
    actions = {
        IrrigationDecision.IRRIGATION_RECOMMENDED: (
            "Irrigate the field. Prioritize fields with the highest stress levels."
        ),
        IrrigationDecision.IRRIGATION_BLOCKED: (
            "Refill the water tank or check the supply line before irrigating."
        ),
        IrrigationDecision.MONITOR: (
            "Continue monitoring soil moisture. Prepare for possible irrigation."
        ),
    }
    return actions.get(decision)
