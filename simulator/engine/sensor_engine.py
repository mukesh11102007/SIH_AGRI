"""
Realistic Sensor Simulation Engine.

Models correlated agricultural sensor readings with:
- Time-of-day variation (day/night cycles)
- Scenario overlays (water stress, heat, etc.)
- Natural noise and gradual drift
- Inter-sensor correlations (humidity inversely related to temp, etc.)

This simulator only generates raw sensor values.
It NEVER injects recommendations, conditions, or analysis results.
Those are produced by the backend decision engine.

The data flows through exactly the same pipeline as real hardware.
"""
from __future__ import annotations
import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class SimulatorState:
    """Mutable state that persists between readings to enable realistic drift."""
    soil_moisture_pct: float = 60.0
    sequence_number: int = 0
    water_consumed_liters: float = 0.0
    last_update_time: float = field(default_factory=time.time)
    scenario: str = "NORMAL"

    # Scenario-specific state
    water_tank_available: bool = True
    activity_event_active: bool = False
    activity_event_remaining: int = 0  # readings remaining in event


class SensorEngine:
    """
    Generates one complete sensor reading per call.
    
    Maintains internal state for realistic time-series behavior.
    All values are physically plausible — no impossible readings.
    """

    def __init__(self) -> None:
        self.state = SimulatorState()

    def set_scenario(self, scenario: str) -> None:
        """Apply a scenario overlay. Only changes raw sensor values."""
        self.state.scenario = scenario
        if scenario == "LOW_WATER":
            self.state.water_tank_available = False
        elif scenario == "NORMAL":
            self.state.water_tank_available = True
            self.state.activity_event_active = False

    def generate(self) -> dict[str, Any]:
        """Generate a complete set of correlated sensor readings."""
        now = datetime.now(timezone.utc)
        hour = now.hour + now.minute / 60.0  # Fractional hour 0–24

        s = self.state
        s.sequence_number += 1

        # ── Time-of-day base curves ──────────────────────────
        # Temperature: peaks ~14:00, minimum ~05:00
        temp_cycle = math.sin(math.pi * (hour - 5) / 14) if 5 <= hour <= 19 else 0
        temp_cycle = max(0.0, temp_cycle)

        # Light: follows a bell curve centered on midday
        if 6 <= hour <= 18:
            light_angle = math.pi * (hour - 6) / 12
            light_cycle = math.sin(light_angle)
        else:
            light_cycle = 0.0

        scenario = s.scenario

        # ── Base air temperature ─────────────────────────────
        base_temp = 22.0 + 12.0 * temp_cycle
        if scenario == "HEAT_STRESS":
            base_temp += 8.0  # Significantly hotter
        elif scenario == "EXCESS_MOISTURE":
            base_temp -= 3.0  # Cooler, cloudier conditions
        air_temp = base_temp + self._noise(0.5)

        # ── Air humidity — inversely correlated with temp ────
        base_humidity = 75.0 - 30.0 * temp_cycle
        if scenario == "HEAT_STRESS":
            base_humidity -= 20.0  # Hot + dry
        elif scenario == "EXCESS_MOISTURE":
            base_humidity = min(95.0, base_humidity + 20.0)
        elif scenario == "WATER_STRESS":
            base_humidity -= 10.0
        air_humidity = self._clamp(base_humidity + self._noise(3.0), 15.0, 99.0)

        # ── Soil moisture — drifts over time ─────────────────
        # Natural evapotranspiration: ~0.5%/reading faster when hot
        et_rate = 0.3 + (air_temp / 40.0) * 0.4
        if scenario == "WATER_STRESS":
            et_rate *= 2.5  # Rapid moisture loss
        elif scenario == "EXCESS_MOISTURE":
            et_rate = -0.5  # Moisture increasing (rain/overwatering)
        elif scenario == "NORMAL" and s.soil_moisture_pct < 40:
            et_rate = -0.3  # Simulate natural recovery

        s.soil_moisture_pct = self._clamp(
            s.soil_moisture_pct - et_rate + self._noise(0.3),
            5.0, 100.0,
        )

        # ── Soil temperature — follows air temp with lag ─────
        soil_temp = air_temp - 3.0 + self._noise(0.5)
        if scenario == "HEAT_STRESS":
            soil_temp += 3.0

        # ── Light intensity ───────────────────────────────────
        max_lux = 75000.0
        if scenario == "EXCESS_MOISTURE":
            max_lux = 20000.0  # Overcast
        elif scenario == "HEAT_STRESS":
            max_lux = 95000.0  # Intense sun
        light_lux = self._clamp(max_lux * light_cycle + self._noise(2000.0), 0.0, 120000.0)

        # ── Leaf wetness ──────────────────────────────────────
        # High when humidity high, dew at night/morning
        dew_factor = 1.0 if (hour < 8 or hour > 21) and air_humidity > 75 else 0.0
        base_wetness = dew_factor * 60.0 + (air_humidity - 60.0) * 0.4
        if scenario == "EXCESS_MOISTURE":
            base_wetness = 80.0
        elif scenario == "HEAT_STRESS":
            base_wetness = max(0.0, base_wetness - 30.0)
        leaf_wetness = self._clamp(base_wetness + self._noise(5.0), 0.0, 100.0)

        # ── Vibration — activity signal ───────────────────────
        # Normally low, occasionally elevated, much higher during activity event
        base_vibration = 15
        if scenario == "ACTIVITY_EVENT":
            if not s.activity_event_active:
                s.activity_event_active = True
                s.activity_event_remaining = random.randint(5, 15)
            if s.activity_event_remaining > 0:
                base_vibration = random.randint(600, 1200)
                s.activity_event_remaining -= 1
            else:
                s.activity_event_active = False
                base_vibration = 15
        elif random.random() < 0.05:
            base_vibration = random.randint(200, 400)

        vibration_raw = max(0, int(base_vibration + self._noise(5.0)))

        # ── Water level ───────────────────────────────────────
        if scenario == "LOW_WATER":
            water_available = False
        elif scenario == "WATER_STRESS":
            # Occasionally toggle to simulate marginal supply
            water_available = random.random() > 0.1
        else:
            water_available = s.water_tank_available

        return {
            "air_temperature_c": round(air_temp, 1),
            "air_humidity_pct": round(air_humidity, 1),
            "soil_moisture_pct": round(s.soil_moisture_pct, 1),
            "soil_temperature_c": round(soil_temp, 1),
            "light_lux": round(light_lux, 0),
            "leaf_wetness_pct": round(leaf_wetness, 1),
            "vibration_raw": vibration_raw,
            "water_level_available": water_available,
        }

    @staticmethod
    def _noise(magnitude: float) -> float:
        """Gaussian noise for realistic sensor variation."""
        return random.gauss(0, magnitude * 0.5)

    @staticmethod
    def _clamp(value: float, min_v: float, max_v: float) -> float:
        return max(min_v, min(max_v, value))
