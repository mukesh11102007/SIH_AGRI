"""
ML Model Registry — manages all registered models.

Models register themselves here. The application code calls
registry.get_model("irrigation") without knowing the implementation.

Adding a new model requires only:
1. Implement MLModel
2. Register it here
No other code changes required.
"""
from __future__ import annotations
from typing import Any

from app.ml.base import MLModel, MLPredictionResult
from app.ml.stubs import IrrigationPredictorStub, StressPredictorStub, VisionServiceStub
from app.ml.env_model import EnvRiskPredictor
from app.core.logging import get_logger

logger = get_logger(__name__)


class MLRegistry:
    def __init__(self) -> None:
        self._models: dict[str, MLModel] = {}

    def register(self, model: MLModel) -> None:
        self._models[model.prediction_type] = model
        logger.info("ml_model_registered", name=model.model_name, type=model.prediction_type)

    def get_model(self, prediction_type: str) -> MLModel | None:
        return self._models.get(prediction_type)

    async def predict(
        self, prediction_type: str, inputs: dict[str, Any]
    ) -> MLPredictionResult | None:
        model = self.get_model(prediction_type)
        if model is None:
            logger.warning("ml_model_not_found", type=prediction_type)
            return None
        if not model.is_available():
            logger.warning("ml_model_unavailable", name=model.model_name)
            return None
        return await model.predict(inputs)

    def list_models(self) -> list[dict[str, Any]]:
        return [
            {
                "prediction_type": t,
                "model_name": m.model_name,
                "model_version": m.model_version,
                "is_available": m.is_available(),
                "is_stub": getattr(m, 'is_stub', False) or isinstance(m, (IrrigationPredictorStub, StressPredictorStub, VisionServiceStub)),
            }
            for t, m in self._models.items()
        ]


# Singleton registry
_registry = MLRegistry()


def get_registry() -> MLRegistry:
    return _registry


def setup_registry() -> None:
    """Register all available models on application startup."""
    _registry.register(IrrigationPredictorStub())
    _registry.register(StressPredictorStub())
    _registry.register(VisionServiceStub())
    
    # Register the real environment risk model
    _registry.register(EnvRiskPredictor())
    
    logger.info("ml_registry_initialized", model_count=len(_registry._models))
