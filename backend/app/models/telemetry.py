from __future__ import annotations
"""
SensorReading ORM model — the TimescaleDB hypertable for all sensor telemetry.

This is the central time-series store. TimescaleDB will partition this table
by `received_at` for efficient time-range queries and aggregations.

Validation flags are stored as JSON so we can record exactly which sensors
had issues without adding dozens of boolean columns.
"""
import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import (
    String, DateTime, Float, Boolean, Integer,
    ForeignKey, JSON, func, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Foreign keys
    device_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("devices.id", ondelete="SET NULL"), nullable=False
    )
    field_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("fields.id", ondelete="SET NULL"), nullable=False
    )

    # ── Timestamps ──────────────────────────────────────────
    # received_at: when the backend received and stored this reading
    # device_timestamp: the timestamp the device reported (may differ due to clock drift)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    device_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Source ──────────────────────────────────────────────
    source: Mapped[str] = mapped_column(
        String(32), default="simulator", nullable=False
    )  # "simulator" | "esp32" | "esp32-cam-node" | "hc05"
    sequence_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── DHT22: Air temperature + humidity ───────────────────
    air_temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    air_humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── DS18B20: Soil temperature ────────────────────────────
    soil_temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Capacitive: Soil moisture ────────────────────────────
    soil_moisture_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── BH1750: Light ────────────────────────────────────────
    light_lux: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Leaf wetness ─────────────────────────────────────────
    leaf_wetness_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Vibration ────────────────────────────────────────────
    # Raw signal — NOT interpreted as a specific pest
    vibration_raw: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Float switch: water level/availability ───────────────
    water_level_available: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # ── Data quality ─────────────────────────────────────────
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_flags: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )  # e.g. {"air_temperature_c": "out_of_range", "dht22": "sensor_error"}

    # ── Sensor status (from device) ──────────────────────────
    sensor_status: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="sensor_readings")
    field: Mapped["Field"] = relationship("Field", back_populates="sensor_readings")

    # ── Indexes ─────────────────────────────────────────────
    __table_args__ = (
        # Primary query patterns: field + time range
        Index("ix_sensor_readings_field_received", "field_id", "received_at"),
        Index("ix_sensor_readings_device_received", "device_id", "received_at"),
        Index("ix_sensor_readings_received_at", "received_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<SensorReading id={self.id} field={self.field_id} "
            f"received_at={self.received_at} source={self.source}>"
        )
