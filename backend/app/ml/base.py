"""
ML Model Abstract Base — defines the interface every ML model must implement.

The backend uses only this interface. No code outside the ml/ package
should import a concrete model class directly.

This makes models replaceable without touching application logic.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MLPredictionResult:
    """Standardized result returned by every ML model."""
    model_name: str
    model_version: str
    prediction_type: str            # "irrigation" | "stress" | "disease" | "pest" | "yield_risk"
    prediction: dict[str, Any]      # Model-specific output
    confidence: float | None        # 0.0–1.0 (None if unavailable)
    is_stub: bool                   # True = placeholder, not a real trained model
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_display_label(self) -> str:
        """Human-readable prediction label for the UI."""
        if self.is_stub:
            return "Model not yet available"
        label = self.prediction.get("label", "Unknown")
        if self.confidence is not None:
            pct = int(self.confidence * 100)
            return f"{label} ({pct}% confidence)"
        return label


class MLModel(ABC):
    """Abstract base class for all ML models in the registry."""

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @property
    @abstractmethod
    def model_version(self) -> str: ...

    @property
    @abstractmethod
    def prediction_type(self) -> str: ...

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the model is loaded and ready for inference."""
        ...

    @abstractmethod
    async def predict(self, inputs: dict[str, Any]) -> MLPredictionResult:
        """Run inference on the given inputs."""
        ...
