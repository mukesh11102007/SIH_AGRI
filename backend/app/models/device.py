from __future__ import annotations
"""Device ORM model — represents a physical or simulated field device (ESP32, etc.)."""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    field_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("fields.id", ondelete="CASCADE"), nullable=False
    )

    # The identifier that the device uses in MQTT topics and telemetry payloads
    device_identifier: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True
    )

    # "simulator" | "esp32" | "esp32-cam-node" | "hc05"
    source_type: Mapped[str] = mapped_column(String(32), default="simulator", nullable=False)
    firmware_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Connectivity tracking
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    field: Mapped["Field"] = relationship("Field", back_populates="devices")
    sensor_readings: Mapped[list["SensorReading"]] = relationship(
        "SensorReading", back_populates="device"
    )

    def __repr__(self) -> str:
        return f"<Device id={self.id} identifier={self.device_identifier!r} source={self.source_type}>"
