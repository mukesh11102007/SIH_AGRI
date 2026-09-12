"""
ML Model Stubs — placeholder implementations for models not yet trained.

These stubs are clearly marked as non-real models.
The UI will display "Model not yet available" rather than fabricating results.
Stubs exist to verify the ML interface plumbing works before real models are added.
"""
from __future__ import annotations
from typing import Any

from app.ml.base import MLModel, MLPredictionResult


class IrrigationPredictorStub(MLModel):
    """
    Placeholder for a future trained irrigation prediction model.
    Returns a clearly-marked stub result.
    Replace this class with a real model (e.g. scikit-learn, ONNX, TFLite)
    when training data is available.
    """

    @property
    def model_name(self) -> str:
        return "irrigation_predictor_stub"

    @property
    def model_version(self) -> str:
        return "0.0.0-stub"

    @property
    def prediction_type(self) -> str:
        return "irrigation"

    def is_available(self) -> bool:
        return True  # Stub is always "available" for interface testing

    async def predict(self, inputs: dict[str, Any]) -> MLPredictionResult:
        return MLPredictionResult(
            model_name=self.model_name,
            model_version=self.model_version,
            prediction_type=self.prediction_type,
            prediction={
                "label": "Stub — no trained model",
                "note": "Replace IrrigationPredictorStub with a trained model.",
            },
            confidence=None,
            is_stub=True,
            metadata={"inputs_received": list(inputs.keys())},
        )


class StressPredictorStub(MLModel):
    """
    Placeholder for a future crop stress prediction model.
    """

    @property
    def model_name(self) -> str:
        return "stress_predictor_stub"

    @property
    def model_version(self) -> str:
        return "0.0.0-stub"

    @property
    def prediction_type(self) -> str:
        return "stress"

    def is_available(self) -> bool:
        return True

    async def predict(self, inputs: dict[str, Any]) -> MLPredictionResult:
        return MLPredictionResult(
            model_name=self.model_name,
            model_version=self.model_version,
            prediction_type=self.prediction_type,
            prediction={
                "label": "Stub — no trained model",
                "note": "Replace StressPredictorStub with a trained model.",
            },
            confidence=None,
            is_stub=True,
        )


class VisionServiceStub(MLModel):
    """
    Placeholder for the future camera-based crop disease / pest detection service.

    The real implementation will:
    - Accept image data (path, URL, or base64)
    - Run a vision model (e.g. YOLOv8, EfficientNet, custom CNN)
    - Return disease/pest class + confidence + bounding boxes

    It must run on an appropriate edge device (Raspberry Pi, Jetson Nano)
    or cloud endpoint — NOT on the ESP32.
    """

    @property
    def model_name(self) -> str:
        return "vision_service_stub"

    @property
    def model_version(self) -> str:
        return "0.0.0-stub"

    @property
    def prediction_type(self) -> str:
        return "disease"

    def is_available(self) -> bool:
        return False  # Vision service requires camera hardware — unavailable as stub

    async def predict(self, inputs: dict[str, Any]) -> MLPredictionResult:
        return MLPredictionResult(
            model_name=self.model_name,
            model_version=self.model_version,
            prediction_type=self.prediction_type,
            prediction={
                "label": "Camera not connected",
                "note": "Connect camera and deploy vision model to enable crop image analysis.",
            },
            confidence=None,
            is_stub=True,
        )
