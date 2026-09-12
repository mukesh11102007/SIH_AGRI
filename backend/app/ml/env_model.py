import os
import joblib
import pandas as pd
from typing import Any

from app.ml.base import MLModel, MLPredictionResult
from app.core.logging import get_logger

logger = get_logger(__name__)


class EnvRiskPredictor(MLModel):
    def __init__(self) -> None:
        self._model = None
        self._expected_columns = None
        self._load_model()

    def _load_model(self) -> None:
        try:
            # Paths relative to backend root
            model_path = os.path.join("ml_models", "env_model.pkl")
            cols_path = os.path.join("ml_models", "expected_columns.pkl")
            
            if os.path.exists(model_path) and os.path.exists(cols_path):
                self._model = joblib.load(model_path)
                self._expected_columns = joblib.load(cols_path)
                logger.info("env_risk_model_loaded", path=model_path)
            else:
                logger.warning("env_risk_model_not_found", path=model_path)
        except Exception as e:
            logger.error("env_risk_model_load_failed", error=str(e))

    @property
    def model_name(self) -> str:
        return "Environmental Risk Random Forest"

    @property
    def model_version(self) -> str:
        return "1.0.0"

    @property
    def prediction_type(self) -> str:
        return "env_risk"

    def is_available(self) -> bool:
        return self._model is not None and self._expected_columns is not None

    async def predict(self, inputs: dict[str, Any]) -> MLPredictionResult:
        if not self.is_available():
            return MLPredictionResult(
                model_name=self.model_name,
                model_version=self.model_version,
                prediction_type=self.prediction_type,
                prediction={"error": "Model not loaded"},
                confidence=None,
                is_stub=True,
            )

        # Expected inputs:
        # crop_type, temp, hum, sm, pressure, solar, organic_gas, pest_vib
        try:
            input_data = pd.DataFrame([{
                'Crop_Type': inputs.get('crop_type', 'Wheat'),
                'Temperature_C': inputs.get('temp', 25.0),
                'Humidity_pct': inputs.get('hum', 50.0),
                'Soil_Moisture_pct': inputs.get('sm', 50.0),
                'Atmospheric_Pressure_hPa': inputs.get('pressure', 1013.25),
                'Solar_Irradiance_W_m2': inputs.get('solar', 0.5),
                'Organic_Gas': inputs.get('organic_gas', 150),
                'Pest_Vibration': inputs.get('pest_vib', 50)
            }])

            # Preprocess identically to training
            input_encoded = pd.get_dummies(input_data, columns=['Crop_Type'])

            # Align columns
            for col in self._expected_columns:
                if col not in input_encoded.columns:
                    input_encoded[col] = 0
            input_encoded = input_encoded[self._expected_columns]

            # Predict
            prediction_idx = self._model.predict(input_encoded)[0]
            probabilities = self._model.predict_proba(input_encoded)[0]
            
            # Find the max probability
            max_prob = max(probabilities)

            return MLPredictionResult(
                model_name=self.model_name,
                model_version=self.model_version,
                prediction_type=self.prediction_type,
                prediction={"label": prediction_idx, "risk_level": prediction_idx},
                confidence=float(max_prob),
                is_stub=False,
            )
        except Exception as e:
            logger.error("env_risk_prediction_failed", error=str(e))
            return MLPredictionResult(
                model_name=self.model_name,
                model_version=self.model_version,
                prediction_type=self.prediction_type,
                prediction={"error": "Prediction failed"},
                confidence=None,
                is_stub=True,
            )
