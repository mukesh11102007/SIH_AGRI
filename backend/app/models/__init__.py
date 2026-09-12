"""Import all ORM models so Alembic and SQLAlchemy can discover them."""
from app.models.farm import Farm
from app.models.field import Field
from app.models.crop import Crop
from app.models.device import Device
from app.models.telemetry import SensorReading
from app.models.alert import Alert
from app.models.recommendation import Recommendation
from app.models.ml_prediction import MLPrediction

__all__ = [
    "Farm", "Field", "Crop", "Device",
    "SensorReading", "Alert", "Recommendation", "MLPrediction",
]
