# SmartFarm — AI-Powered Smart Farming Decision-Support Platform

> **Qualcomm Problem Statement 26180** — Field-deployable, edge-first agricultural decision support system.

---

## Overview

SmartFarm converts raw IoT sensor data into clear, actionable farming decisions.
Instead of displaying numbers, the system tells farmers: **whether to irrigate, where stress is occurring, and what action to take**.

The system is **hardware-agnostic by design** — it operates identically with the built-in simulator and real ESP32 hardware.

---

## System Architecture

```
[ESP32 / Simulator] → MQTT → [Ingest Service] → [Telemetry Validator]
                                                       ↓
                                              [TimescaleDB Hypertable]
                                                       ↓
                                           [Decision Engine]
                                           ├── Irrigation Analyzer
                                           ├── Heat Stress Detector
                                           ├── Water Stress Detector
                                           ├── Excess Moisture Detector
                                           ├── Water Availability Tracker
                                           └── Activity Signal Analyzer
                                                       ↓
                                     [Alert Service] + [Recommendation Store]
                                                       ↓
                              [REST API] + [WebSocket Broadcast] → [Dashboard]
```

---

## What the System Provides

| Feature | Description |
|---|---|
| **Irrigation Decision** | Multi-factor analysis: soil moisture, temperature, humidity, leaf wetness, water availability |
| **Water Stress Detection** | Soil moisture + environmental conditions → stress severity |
| **Heat Stress Detection** | Temperature + humidity + light → crop canopy stress level |
| **Excess Moisture Detection** | Overwatering / flood risk from soil + surface sensors |
| **Water Availability Tracking** | Float switch → irrigation gate status |
| **Activity Signal** | Vibration sensor → generic field activity (NOT pest identification) |
| **Historical Analytics** | TimescaleDB time-series with statistical summaries |
| **Real-time Dashboard** | WebSocket push updates, no polling needed |
| **ML Architecture** | Abstract model registry, pluggable models, stubs ready for real models |

---

## Sensors

| Sensor | Hardware | Measures |
|---|---|---|
| DHT22 | Temperature & Humidity | Air temperature (°C), Air humidity (%) |
| DS18B20 | Waterproof Probe | Soil temperature (°C) |
| Capacitive Soil Moisture | Analog | Volumetric soil moisture (%) |
| BH1750 | Light Sensor | Illuminance (lux) |
| Leaf Wetness Sensor | Resistive | Leaf surface wetness (%) |
| SW-420 Vibration | Analog | Field activity signal (raw ADC) |
| Float Switch | Digital | Water tank/source level (boolean) |

---

## Quick Start

### Prerequisites
- Docker Desktop
- Docker Compose v2

### 1. Configure environment

```bash
# The .env file is already populated with development defaults.
# In production, change all passwords.
cp .env.example .env    # if .env doesn't exist
```

### 2. Launch the stack

```bash
docker compose up -d
```

Services started:
| Service | Port | Description |
|---|---|---|
| Frontend | 3000 | React dashboard |
| Backend API | 8000 | FastAPI + REST + WebSocket |
| Mosquitto MQTT | 1883 | MQTT broker |
| PostgreSQL + TimescaleDB | 5432 | Primary database |
| Simulator | — | Realistic sensor data generator |

### 3. Open the dashboard

http://localhost:3000

API docs: http://localhost:8000/api/docs

### 4. Simulate field scenarios

From the dashboard **Simulation Control** panel, or via API:

```bash
# Apply water stress scenario
curl -X POST http://localhost:8000/api/v1/simulator/scenario \
  -H "Content-Type: application/json" \
  -d '{"scenario": "WATER_STRESS"}'
```

Available scenarios: `NORMAL` | `WATER_STRESS` | `HEAT_STRESS` | `EXCESS_MOISTURE` | `LOW_WATER` | `ACTIVITY_EVENT`

---

## Connecting a Real ESP32

1. Set MQTT credentials in `mosquitto/config/passwd`
2. Flash your ESP32 to publish telemetry to:
   ```
   farm/farm-001/field/field-north-01/device/YOUR_DEVICE_ID/telemetry
   ```
3. Use the telemetry payload format (see below)
4. The device appears in the **Devices** page automatically

### Telemetry payload format

```json
{
  "device_id": "esp32-field-01",
  "farm_id": "farm-001",
  "field_id": "field-north-01",
  "firmware_version": "1.0.0",
  "timestamp_utc": "2026-09-01T12:00:00Z",
  "source": "esp32",
  "sequence_number": 1,
  "readings": {
    "air_temperature_c": 28.5,
    "air_humidity_pct": 65.0,
    "soil_moisture_pct": 42.0,
    "soil_temperature_c": 24.0,
    "light_lux": 35000,
    "leaf_wetness_pct": 15.0,
    "vibration_raw": 20,
    "water_level_available": true
  },
  "sensor_status": {
    "dht22": "ok",
    "ds18b20": "ok",
    "soil_moisture": "ok",
    "bh1750": "ok",
    "leaf_wetness": "ok",
    "vibration": "ok",
    "float_switch": "ok"
  }
}
```

---

## Backend Development

```bash
cd backend
pip install -r requirements.txt

# Run locally (requires .env with working DB + MQTT)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest tests/ -v
```

---

## ML Model Integration

The ML registry accepts any model implementing the `MLModel` abstract interface:

```python
# backend/app/ml/your_model.py
from app.ml.base import MLModel, MLPredictionResult

class MyIrrigationModel(MLModel):
    @property
    def model_name(self): return "my_irrigation_model_v1"
    @property
    def model_version(self): return "1.0.0"
    @property
    def prediction_type(self): return "irrigation"

    def is_available(self) -> bool:
        return True  # your model loaded check

    async def predict(self, inputs: dict) -> MLPredictionResult:
        # your inference here
        ...
```

Register it in `backend/app/ml/registry.py`:
```python
_registry.register(MyIrrigationModel())
```

**No other code changes required.**

Training data is continuously collected in TimescaleDB and accessible via:
```sql
SELECT * FROM sensor_readings WHERE received_at > NOW() - INTERVAL '30 days';
```

---

## Project Structure

```
Farm Project/
├── backend/
│   ├── app/
│   │   ├── core/           # Config, logging, database
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic validation schemas
│   │   ├── ingestion/      # MQTT client + telemetry pipeline
│   │   ├── services/
│   │   │   └── decision_engine/  # Irrigation, stress, risk analyzers
│   │   ├── api/v1/         # REST API routes
│   │   ├── websocket/      # Real-time WebSocket manager
│   │   └── ml/             # ML model registry + stubs
│   ├── tests/              # Decision engine tests
│   └── alembic/            # Database migrations
├── simulator/
│   ├── engine/             # Realistic sensor simulation engine
│   └── simulator.py        # MQTT publishing loop
├── frontend/
│   └── src/
│       ├── api/            # HTTP client + WebSocket hook
│       ├── components/     # UI components
│       ├── pages/          # Dashboard, Monitor, Irrigation, ...
│       └── types/          # TypeScript type definitions
├── mosquitto/              # MQTT broker config
├── docker-compose.yml
└── .env
```

---

## Design Decisions

| Decision | Rationale |
|---|---|
| **FastAPI + async** | Simultaneous MQTT, WebSocket, and REST without threads |
| **TimescaleDB** | Hypertable time-series with automatic partitioning |
| **MQTT (Mosquitto)** | Standard IoT protocol, QoS 1 guaranteed delivery |
| **Rule-based decision engine** | Deterministic, auditable, no training data required |
| **ML registry pattern** | Models pluggable without application code changes |
| **Simulator** | Identical data path as real hardware — no code branches |
| **React Query** | Automatic cache invalidation + background refresh |

---

## What the System Does NOT Claim

- ❌ The vibration sensor does **not** identify specific pests
- ❌ The sensor array does **not** diagnose crop diseases
- ❌ Environmental conditions indicate **risk contexts**, not confirmed disease presence
- ✅ All recommendations include explicit reasoning and contributing factors
- ✅ ML models are clearly marked as stubs until trained models are integrated

---

*Built for Qualcomm Problem Statement 26180 — Field-Deployable AI-Powered Smart Farming Assistant*
