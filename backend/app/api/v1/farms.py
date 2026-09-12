"""Farms, Fields, and Crops REST API routes."""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.models.farm import Farm
from app.models.field import Field
from app.models.crop import Crop
from app.schemas.farm import (
    FarmCreate, FarmRead, FarmReadWithFields,
    FieldCreate, FieldRead, FieldUpdate,
    CropCreate, CropRead,
)

router = APIRouter()


# ── Crops ─────────────────────────────────────────────────────────────────────

@router.get("/crops", response_model=list[CropRead], tags=["Crops"])
async def list_crops(db: AsyncSession = Depends(get_db)) -> list[Crop]:
    result = await db.execute(select(Crop).order_by(Crop.name))
    return result.scalars().all()


@router.post("/crops", response_model=CropRead, status_code=status.HTTP_201_CREATED, tags=["Crops"])
async def create_crop(body: CropCreate, db: AsyncSession = Depends(get_db)) -> Crop:
    existing = await db.execute(select(Crop).where(Crop.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Crop '{body.name}' already exists")
    crop = Crop(**body.model_dump())
    db.add(crop)
    await db.commit()
    await db.refresh(crop)
    return crop


@router.get("/crops/{crop_id}", response_model=CropRead, tags=["Crops"])
async def get_crop(crop_id: str, db: AsyncSession = Depends(get_db)) -> Crop:
    crop = await db.get(Crop, crop_id)
    if not crop:
        raise HTTPException(status_code=404, detail="Crop not found")
    return crop


# ── Farms ─────────────────────────────────────────────────────────────────────

@router.get("/farms", response_model=list[FarmRead], tags=["Farms"])
async def list_farms(db: AsyncSession = Depends(get_db)) -> list[Farm]:
    result = await db.execute(select(Farm).order_by(Farm.name))
    return result.scalars().all()


@router.post("/farms", response_model=FarmRead, status_code=status.HTTP_201_CREATED, tags=["Farms"])
async def create_farm(body: FarmCreate, db: AsyncSession = Depends(get_db)) -> Farm:
    farm = Farm(**body.model_dump())
    db.add(farm)
    await db.commit()
    await db.refresh(farm)
    return farm


@router.get("/farms/{farm_id}", response_model=FarmReadWithFields, tags=["Farms"])
async def get_farm(farm_id: str, db: AsyncSession = Depends(get_db)) -> Farm:
    result = await db.execute(
        select(Farm)
        .options(selectinload(Farm.fields).selectinload(Field.crop))
        .where(Farm.id == farm_id)
    )
    farm = result.scalar_one_or_none()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    return farm


# ── Fields ─────────────────────────────────────────────────────────────────────

@router.get("/farms/{farm_id}/fields", response_model=list[FieldRead], tags=["Fields"])
async def list_fields(farm_id: str, db: AsyncSession = Depends(get_db)) -> list[Field]:
    result = await db.execute(
        select(Field)
        .options(selectinload(Field.crop))
        .where(Field.farm_id == farm_id)
        .order_by(Field.name)
    )
    return result.scalars().all()


@router.post("/fields", response_model=FieldRead, status_code=status.HTTP_201_CREATED, tags=["Fields"])
async def create_field(body: FieldCreate, db: AsyncSession = Depends(get_db)) -> Field:
    farm = await db.get(Farm, body.farm_id)
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    field = Field(**body.model_dump())
    db.add(field)
    await db.commit()
    await db.refresh(field)
    return field


@router.get("/fields/{field_id}", response_model=FieldRead, tags=["Fields"])
async def get_field(field_id: str, db: AsyncSession = Depends(get_db)) -> Field:
    result = await db.execute(
        select(Field).options(selectinload(Field.crop)).where(Field.id == field_id)
    )
    field = result.scalar_one_or_none()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    return field


@router.patch("/fields/{field_id}", response_model=FieldRead, tags=["Fields"])
async def update_field(
    field_id: str, body: FieldUpdate, db: AsyncSession = Depends(get_db)
) -> Field:
    result = await db.execute(
        select(Field).options(selectinload(Field.crop)).where(Field.id == field_id)
    )
    field = result.scalar_one_or_none()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(field, k, v)
    await db.commit()
    await db.refresh(field)
    return field
