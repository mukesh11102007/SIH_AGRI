"""
FastAPI Application Factory.

Wires together:
- Database connection
- MQTT listener (background task)
- Hardware listener (background task — only when HARDWARE_ENABLED=true)
- All API routers
- WebSocket endpoints
- CORS middleware
- Startup data seeding

Hardware integration:
  The HC-05 hardware listener is conditionally started based on the
  HARDWARE_ENABLED setting. When false (the default), the application
  runs exactly as before — no Bluetooth hardware is required.
  See backend/app/hardware/hc05_adapter.py for the integration point.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.database import engine, Base, AsyncSessionLocal
from app.ingestion.mqtt_client import start_mqtt_listener, stop_mqtt_listener
from app.ml.registry import setup_registry

# SQLAlchemy imports
from sqlalchemy import select, text, inspect
from sqlalchemy.exc import OperationalError, ProgrammingError

# Models
from app.models.crop import Crop
from app.models.farm import Farm
from app.models.field import Field
import app.models  # noqa — ensures all models are registered
import os

# API routers
from app.api.v1.farms import router as farms_router
from app.api.v1.telemetry import router as telemetry_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.devices import router as devices_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.websocket import router as ws_router
from app.api.v1.vision import router as vision_router

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("app_starting", env=settings.app_env, version=settings.app_version)

    # Try to connect to the database; run in no-DB mode if unavailable
    db_available = False
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        db_available = True
        logger.info("database_connected")
        await _seed_default_data()
    except Exception as db_exc:
        logger.warning(
            "database_unavailable",
            error=str(db_exc),
            note="Running in NO-DB mode. Live hardware data will be streamed but not persisted.",
        )
    # Store DB availability for the ingestion pipeline
    os.environ["SMARTFARM_DB_AVAILABLE"] = "1" if db_available else "0"

    # Initialize ML model registry
    setup_registry()

    # Start MQTT listener as background task (simulator / existing hardware sources)
    start_mqtt_listener()

    # Start HC-05 hardware listener — only when explicitly enabled.
    if settings.hardware_enabled:
        from app.hardware.hc05_adapter import (
            start_hardware_listener,
            stop_hardware_listener as _stop_hw,
        )
        start_hardware_listener()
        logger.info(
            "hardware_listener_enabled",
            device_id=settings.hardware_device_id,
            port=settings.hardware_serial_port or "(not set)",
        )
    else:
        logger.info(
            "hardware_listener_disabled",
            note="Set HARDWARE_ENABLED=true in .env to enable HC-05 integration.",
        )
        _stop_hw = None  # type: ignore[assignment]

    logger.info("app_ready", db_available=db_available)

    yield  # Application runs here

    # Shutdown — stop hardware listener if it was started
    if settings.hardware_enabled and _stop_hw is not None:
        await _stop_hw()

    await stop_mqtt_listener()
    if db_available:
        await engine.dispose()
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Smart Farming Decision-Support Platform API. "
            "Provides real-time sensor monitoring, irrigation recommendations, "
            "environmental stress analysis, and ML-ready infrastructure."
        ),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS — allow frontend dev server and production frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    PREFIX = "/api/v1"
    app.include_router(farms_router, prefix=PREFIX)
    app.include_router(telemetry_router, prefix=PREFIX)
    app.include_router(alerts_router, prefix=PREFIX)
    app.include_router(devices_router, prefix=PREFIX)
    app.include_router(analytics_router, prefix=PREFIX)
    app.include_router(vision_router, prefix=PREFIX)

    # WebSocket (no prefix — uses its own path)
    app.include_router(ws_router)

    # Health check
    @app.get("/api/v1/health", tags=["System"])
    async def health() -> dict:
        return {
            "status": "ok",
            "version": settings.app_version,
            "env": settings.app_env,
        }

    return app


async def _seed_default_data() -> None:
    """Seed the database with default farms, fields, and crops if empty."""
    # ── Ensure TimescaleDB extension exists (best-effort) ───────────────────
    async with engine.begin() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
        except Exception as exc:
            logger.warning("timescaledb_extension_skipped", reason=str(exc))

    # ── Safety fallback: create tables if alembic hasn't run ─────────────────
    # In production, alembic upgrade head runs first. This is a dev safety net.
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("db_tables_ensured")
        except Exception as exc:
            logger.error("db_create_all_failed", error=str(exc))
            return

    async with AsyncSessionLocal() as db:
        # Check if already seeded
        try:
            existing_crops = await db.execute(select(Crop).limit(1))
            if existing_crops.scalar_one_or_none():
                logger.info("seed_data_already_exists")
                return
        except (OperationalError, ProgrammingError) as exc:
            logger.error("seed_check_failed", error=str(exc))
            return

        # Default crops
        crops = [
            Crop(
                id="crop-rice",
                name="Rice (Paddy)",
                variety="Common",
                optimal_moisture_min_pct=55.0,
                optimal_moisture_max_pct=80.0,
                critical_moisture_min_pct=30.0,
                optimal_temp_min_c=20.0,
                optimal_temp_max_c=35.0,
                heat_stress_c=40.0,
                optimal_humidity_min_pct=50.0,
                optimal_humidity_max_pct=90.0,
            ),
            Crop(
                id="crop-maize",
                name="Maize (Corn)",
                variety="Common",
                optimal_moisture_min_pct=40.0,
                optimal_moisture_max_pct=70.0,
                critical_moisture_min_pct=20.0,
                optimal_temp_min_c=18.0,
                optimal_temp_max_c=32.0,
                heat_stress_c=38.0,
                optimal_humidity_min_pct=40.0,
                optimal_humidity_max_pct=80.0,
            ),
            Crop(
                id="crop-tomato",
                name="Tomato",
                variety="Common",
                optimal_moisture_min_pct=45.0,
                optimal_moisture_max_pct=65.0,
                critical_moisture_min_pct=25.0,
                optimal_temp_min_c=18.0,
                optimal_temp_max_c=30.0,
                heat_stress_c=35.0,
                optimal_humidity_min_pct=45.0,
                optimal_humidity_max_pct=75.0,
            ),
        ]

        for crop in crops:
            db.add(crop)

        # Default farm — use the same IDs the simulator will publish
        farm_id = os.getenv("SIMULATOR_FARM_ID", "farm-001")
        field_id = os.getenv("SIMULATOR_FIELD_ID", "field-north-01")

        farm = Farm(
            id=farm_id,
            name="Demo Farm",
            location="Tamil Nadu, India",
            timezone="Asia/Kolkata",
        )
        db.add(farm)

        field = Field(
            id=field_id,
            farm_id=farm_id,
            crop_id="crop-maize",
            name="North Field",
            area_m2=5000.0,
            growth_stage="vegetative",
        )
        db.add(field)

        try:
            await db.commit()
            logger.info("seed_data_created", crops=len(crops), farms=1, fields=1)
        except Exception as exc:
            await db.rollback()
            logger.warning("seed_data_failed", error=str(exc))


app = create_app()
