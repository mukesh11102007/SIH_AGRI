"""
MLPrediction ORM model — stores predictions from ML models.

Uncertainty is first-class: every prediction records confidence and
whether it came from a real model or a stub.

The application never presents an uncertain ML prediction as a confirmed fact.
"""
import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import String, DateTime, Float, Boolean, ForeignKey, JSON, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class MLPrediction(Base):
    __tablename__ = "ml_predictions"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    field_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("fields.id", ondelete="CASCADE"), nullable=False
    )

    # Model identity
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)

    # prediction_type: "irrigation" | "stress" | "disease" | "pest" | "yield_risk"
    prediction_type: Mapped[str] = mapped_column(String(32), nullable=False)

    # Prediction output (flexible JSON — varies by model type)
    prediction: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Confidence 0.0–1.0 (None if model doesn't provide it)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Whether this came from a real model or a stub/placeholder
    is_stub: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Reference to the input that triggered this prediction
    # (sensor_reading_id or image reference)
    input_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Additional model-specific extra metadata
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_ml_predictions_field_created", "field_id", "created_at"),
        Index("ix_ml_predictions_type", "prediction_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<MLPrediction model={self.model_name} type={self.prediction_type} "
            f"confidence={self.confidence} stub={self.is_stub}>"
        )
