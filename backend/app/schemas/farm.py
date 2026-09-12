"""Pydantic schemas for Farm, Field, Crop API responses and requests."""
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field


# ── Crop ─────────────────────────────────────────────────────────────────────

class CropBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    variety: str | None = None
    optimal_moisture_min_pct: float = 40.0
    optimal_moisture_max_pct: float = 70.0
    critical_moisture_min_pct: float = 20.0
    optimal_temp_min_c: float = 15.0
    optimal_temp_max_c: float = 35.0
    heat_stress_c: float = 38.0
    optimal_humidity_min_pct: float = 40.0
    optimal_humidity_max_pct: float = 80.0


class CropCreate(CropBase):
    pass


class CropRead(CropBase):
    id: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Farm ─────────────────────────────────────────────────────────────────────

class FarmBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    location: str | None = None
    timezone: str = "Asia/Kolkata"


class FarmCreate(FarmBase):
    pass


class FarmRead(FarmBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FarmReadWithFields(FarmRead):
    fields: list["FieldRead"] = []


# ── Field ─────────────────────────────────────────────────────────────────────

class FieldBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    area_m2: float | None = None
    growth_stage: str | None = None


class FieldCreate(FieldBase):
    farm_id: str
    crop_id: str | None = None


class FieldUpdate(BaseModel):
    name: str | None = None
    crop_id: str | None = None
    growth_stage: str | None = None
    area_m2: float | None = None


class FieldRead(FieldBase):
    id: str
    farm_id: str
    crop_id: str | None
    created_at: datetime
    updated_at: datetime
    crop: CropRead | None = None

    model_config = {"from_attributes": True}


FarmReadWithFields.model_rebuild()
