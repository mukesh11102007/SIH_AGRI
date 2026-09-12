"""Field ORM model — a managed area within a farm with a specific crop."""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Field(Base):
    __tablename__ = "fields"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    farm_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False
    )
    crop_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("crops.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    growth_stage: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # e.g. "seedling", "vegetative", "flowering", "harvest"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    farm: Mapped["Farm"] = relationship("Farm", back_populates="fields")
    crop: Mapped["Crop | None"] = relationship("Crop", back_populates="fields")
    devices: Mapped[list["Device"]] = relationship(
        "Device", back_populates="field", cascade="all, delete-orphan"
    )
    sensor_readings: Mapped[list["SensorReading"]] = relationship(
        "SensorReading", back_populates="field"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert", back_populates="field", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        "Recommendation", back_populates="field", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Field id={self.id} name={self.name!r} farm_id={self.farm_id}>"
