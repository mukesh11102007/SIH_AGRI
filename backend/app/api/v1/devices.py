"""Devices and Simulator control API routes."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.api.deps import get_db
from app.models.device import Device
from app.schemas.responses import DeviceRead
from app.core.config import settings

router = APIRouter()

ScenarioName = Literal[
    "NORMAL", "WATER_STRESS", "HEAT_STRESS",
    "EXCESS_MOISTURE", "LOW_WATER", "ACTIVITY_EVENT"
]


def _device_connectivity_status(device: Device) -> str:
    if not device.last_seen_at:
        return "never_seen"
    minutes_ago = (datetime.now(timezone.utc) - device.last_seen_at).total_seconds() / 60
    if minutes_ago <= settings.device_stale_minutes:
        return "live"
    elif minutes_ago <= settings.device_offline_minutes:
        return "stale"
    return "offline"


@router.get("/devices", response_model=list[DeviceRead], tags=["Devices"])
async def list_devices(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        select(Device).where(Device.is_active == True).order_by(desc(Device.last_seen_at))
    )
    devices = result.scalars().all()
    return [
        DeviceRead(
            **{c.name: getattr(d, c.name) for c in Device.__table__.columns},
            connectivity_status=_device_connectivity_status(d),
        )
        for d in devices
    ]


@router.get("/fields/{field_id}/devices", response_model=list[DeviceRead], tags=["Devices"])
async def get_field_devices(
    field_id: str, db: AsyncSession = Depends(get_db)
) -> list[dict]:
    result = await db.execute(
        select(Device).where(Device.field_id == field_id, Device.is_active == True)
    )
    devices = result.scalars().all()
    return [
        DeviceRead(
            **{c.name: getattr(d, c.name) for c in Device.__table__.columns},
            connectivity_status=_device_connectivity_status(d),
        )
        for d in devices
    ]


# ── Simulator control ─────────────────────────────────────────────────────────

class ScenarioRequest(BaseModel):
    scenario: ScenarioName
    device_id: str | None = None  # If None, applies to all simulator devices


class ScenarioResponse(BaseModel):
    scenario: str
    applied_to: str
    message: str


# In-memory scenario state — the simulator polls this endpoint
_current_scenario: str = "NORMAL"
_scenario_device_target: str | None = None


@router.post(
    "/simulator/scenario",
    response_model=ScenarioResponse,
    tags=["Simulator"],
    summary="Change the active simulation scenario",
)
async def set_scenario(body: ScenarioRequest) -> ScenarioResponse:
    global _current_scenario, _scenario_device_target
    _current_scenario = body.scenario
    _scenario_device_target = body.device_id
    return ScenarioResponse(
        scenario=body.scenario,
        applied_to=body.device_id or "all_simulators",
        message=f"Scenario changed to {body.scenario}. Simulator will apply on next cycle.",
    )


@router.get(
    "/simulator/scenario",
    tags=["Simulator"],
    summary="Get the current simulation scenario",
)
async def get_scenario() -> dict:
    return {
        "scenario": _current_scenario,
        "device_target": _scenario_device_target,
    }
