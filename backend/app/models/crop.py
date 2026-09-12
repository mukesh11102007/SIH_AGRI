"""Crop ORM model — stores crop-specific thresholds used by the decision engine."""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Crop(Base):
    __tablename__ = "crops"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    variety: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Soil moisture thresholds (%)
    optimal_moisture_min_pct: Mapped[float] = mapped_column(Float, default=40.0)
    optimal_moisture_max_pct: Mapped[float] = mapped_column(Float, default=70.0)
    critical_moisture_min_pct: Mapped[float] = mapped_column(Float, default=20.0)

    # Temperature thresholds (°C)
    optimal_temp_min_c: Mapped[float] = mapped_column(Float, default=15.0)
    optimal_temp_max_c: Mapped[float] = mapped_column(Float, default=35.0)
    heat_stress_c: Mapped[float] = mapped_column(Float, default=38.0)

    # Humidity thresholds (%)
    optimal_humidity_min_pct: Mapped[float] = mapped_column(Float, default=40.0)
    optimal_humidity_max_pct: Mapped[float] = mapped_column(Float, default=80.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    fields: Mapped[list["Field"]] = relationship("Field", back_populates="crop")

    def __repr__(self) -> str:
        return f"<Crop name={self.name!r}>"
