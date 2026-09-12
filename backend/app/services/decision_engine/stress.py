"""
Environmental Stress Detectors — Heat Stress, Water Stress, Excess Moisture,
Water Availability, and Activity Signal.

Each detector is self-contained and returns a structured result
with severity and plain-English explanation.

Important: The activity signal from the vibration sensor is treated
as an environmental signal only — NOT as a pest identification system.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from app.services.decision_engine.irrigation import Severity
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class StressResult:
    condition: str      # "heat_stress" | "water_stress" | "excess_moisture" | ...
    severity: Severity
    title: str
    explanation: str
    contributing_factors: dict[str, Any] = field(default_factory=dict)
    recommended_action: str | None = None


class HeatStressDetector:
    """
    Detects heat stress based on air temperature, soil temperature, humidity, and light.
    All thresholds are configurable via crop parameters.
    """

    def analyze(
        self,
        air_temperature_c: float | None,
        soil_temperature_c: float | None,
        air_humidity_pct: float | None,
        light_lux: float | None,
        heat_stress_threshold_c: float = 38.0,
        high_temp_threshold_c: float = 35.0,
    ) -> StressResult:
        factors: dict[str, Any] = {}
        score = 0.0

        if air_temperature_c is not None:
            factors["air_temperature_c"] = air_temperature_c
            if air_temperature_c >= heat_stress_threshold_c:
                score += 50
            elif air_temperature_c >= high_temp_threshold_c:
                score += 25

        if soil_temperature_c is not None:
            factors["soil_temperature_c"] = soil_temperature_c
            if soil_temperature_c >= 35.0:
                score += 20
            elif soil_temperature_c >= 30.0:
                score += 10

        # Low humidity amplifies heat stress
        if air_humidity_pct is not None:
            factors["air_humidity_pct"] = air_humidity_pct
            if air_humidity_pct < 25:
                score += 20
            elif air_humidity_pct < 40:
                score += 10

        # Intense light amplifies canopy heat
        if light_lux is not None:
            factors["light_lux"] = light_lux
            if light_lux > 80000:
                score += 10

        if score >= 60:
            severity = Severity.CRITICAL
            title = "Severe Heat Stress"
            explanation = (
                f"Air temperature is critically high at {air_temperature_c:.1f}°C"
                if air_temperature_c else "Temperature conditions are dangerously elevated."
            )
            if air_humidity_pct and air_humidity_pct < 40:
                explanation += f" Combined with low humidity ({air_humidity_pct:.1f}%), evapotranspiration demand is very high."
            action = "Provide shade if possible, increase irrigation frequency, and monitor closely."
        elif score >= 35:
            severity = Severity.HIGH
            title = "Heat Stress Detected"
            explanation = (
                f"Temperature is elevated at {air_temperature_c:.1f}°C, "
                "which may cause increased water demand and canopy stress."
                if air_temperature_c else "Elevated temperature conditions detected."
            )
            action = "Monitor crop condition closely. Consider irrigation if soil moisture is low."
        elif score >= 15:
            severity = Severity.MEDIUM
            title = "Moderate Heat Conditions"
            explanation = (
                f"Temperature is above optimal levels at {air_temperature_c:.1f}°C. "
                "Monitor for signs of water stress."
                if air_temperature_c else "Temperature is above optimal levels."
            )
            action = "Continue monitoring. Ensure adequate soil moisture."
        else:
            severity = Severity.NONE
            title = "No Heat Stress"
            explanation = "Temperature conditions are within acceptable range."
            action = None

        return StressResult(
            condition="heat_stress",
            severity=severity,
            title=title,
            explanation=explanation,
            contributing_factors=factors,
            recommended_action=action,
        )


class WaterStressDetector:
    """
    Detects water/drought stress from soil moisture and environmental conditions.
    Distinct from irrigation recommendation — this is about crop stress state.
    """

    def analyze(
        self,
        soil_moisture_pct: float | None,
        air_temperature_c: float | None,
        air_humidity_pct: float | None,
        critical_moisture_min_pct: float = 20.0,
        optimal_moisture_min_pct: float = 40.0,
    ) -> StressResult:
        factors: dict[str, Any] = {}
        score = 0.0

        if soil_moisture_pct is None:
            return StressResult(
                condition="water_stress",
                severity=Severity.NONE,
                title="No Data",
                explanation="Soil moisture data is unavailable.",
                contributing_factors={},
            )

        factors["soil_moisture_pct"] = soil_moisture_pct

        if soil_moisture_pct <= critical_moisture_min_pct:
            score += 60
        elif soil_moisture_pct <= optimal_moisture_min_pct:
            score += 30

        if air_temperature_c is not None:
            factors["air_temperature_c"] = air_temperature_c
            if air_temperature_c >= 38:
                score += 25
            elif air_temperature_c >= 33:
                score += 12

        if air_humidity_pct is not None:
            factors["air_humidity_pct"] = air_humidity_pct
            if air_humidity_pct < 30:
                score += 15
            elif air_humidity_pct < 45:
                score += 7

        if score >= 65:
            severity = Severity.CRITICAL
            title = "Severe Water Stress"
            explanation = (
                f"Soil moisture is critically low at {soil_moisture_pct:.1f}%."
            )
            if air_temperature_c and air_temperature_c >= 35:
                explanation += f" High temperature ({air_temperature_c:.1f}°C) is compounding water loss."
            action = "Irrigate as soon as possible. Delay may cause irreversible crop damage."
        elif score >= 40:
            severity = Severity.HIGH
            title = "Water Stress Detected"
            explanation = (
                f"Low soil moisture ({soil_moisture_pct:.1f}%) combined with environmental "
                "conditions indicates significant water stress."
            )
            action = "Irrigation is recommended promptly."
        elif score >= 20:
            severity = Severity.MEDIUM
            title = "Moderate Water Stress"
            explanation = f"Soil moisture is below optimal at {soil_moisture_pct:.1f}%. Monitor closely."
            action = "Consider irrigation within the next few hours."
        else:
            severity = Severity.NONE
            title = "No Water Stress"
            explanation = "Soil moisture is within an acceptable range."
            action = None

        return StressResult(
            condition="water_stress",
            severity=severity,
            title=title,
            explanation=explanation,
            contributing_factors=factors,
            recommended_action=action,
        )


class ExcessMoistureDetector:
    """
    Detects excessively wet conditions that may indicate overwatering,
    poor drainage, or flood risk.
    """

    def analyze(
        self,
        soil_moisture_pct: float | None,
        leaf_wetness_pct: float | None,
        air_humidity_pct: float | None,
        light_lux: float | None,
        optimal_moisture_max_pct: float = 70.0,
    ) -> StressResult:
        factors: dict[str, Any] = {}
        score = 0.0

        if soil_moisture_pct is not None:
            factors["soil_moisture_pct"] = soil_moisture_pct
            if soil_moisture_pct >= 90:
                score += 50
            elif soil_moisture_pct >= optimal_moisture_max_pct:
                score += 25

        if leaf_wetness_pct is not None and leaf_wetness_pct > 60:
            factors["leaf_wetness_pct"] = leaf_wetness_pct
            score += 15

        if air_humidity_pct is not None and air_humidity_pct > 85:
            factors["air_humidity_pct"] = air_humidity_pct
            score += 10

        # Low light + high moisture = disease-risk context (NOT diagnosis)
        if light_lux is not None and light_lux < 5000 and score > 20:
            factors["light_lux"] = light_lux
            score += 10

        if score >= 55:
            severity = Severity.HIGH
            title = "Excess Moisture — Potential Flood Risk"
            explanation = (
                f"Soil moisture is very high at {soil_moisture_pct:.1f}%. "
                "Root damage or anaerobic conditions may develop."
                if soil_moisture_pct else "Excessively wet conditions detected."
            )
            action = "Check drainage. Avoid irrigation. Inspect field for waterlogging."
        elif score >= 30:
            severity = Severity.MEDIUM
            title = "Excess Moisture"
            explanation = (
                f"Soil moisture is above optimal at {soil_moisture_pct:.1f}%. "
                "Irrigation should be delayed."
                if soil_moisture_pct else "Above-optimal moisture conditions."
            )
            action = "Delay irrigation. Monitor drainage."
        else:
            severity = Severity.NONE
            title = "Moisture Normal"
            explanation = "Soil moisture is within acceptable limits."
            action = None

        return StressResult(
            condition="excess_moisture",
            severity=severity,
            title=title,
            explanation=explanation,
            contributing_factors=factors,
            recommended_action=action,
        )


class WaterAvailabilityTracker:
    """Tracks water source availability from the float switch."""

    def analyze(self, water_level_available: bool | None) -> StressResult:
        if water_level_available is True:
            return StressResult(
                condition="water_availability",
                severity=Severity.NONE,
                title="Water Available",
                explanation="The water source/tank reports adequate water level.",
            )
        elif water_level_available is False:
            return StressResult(
                condition="water_availability",
                severity=Severity.CRITICAL,
                title="Water Unavailable",
                explanation="The water level sensor indicates the water source is empty or below threshold.",
                recommended_action="Refill the water tank or check the supply line before irrigating.",
            )
        else:
            return StressResult(
                condition="water_availability",
                severity=Severity.LOW,
                title="Water Status Unknown",
                explanation="Water level sensor data is unavailable.",
                recommended_action="Check the float switch sensor connection.",
            )


class ActivitySignalAnalyzer:
    """
    Analyzes the vibration sensor signal.

    IMPORTANT: This does NOT identify specific pests.
    The vibration sensor is a generic activity signal.
    Elevated readings only indicate that unusual vibration/movement
    was detected in the field at the time of measurement.
    """

    ELEVATED_THRESHOLD = 500  # Raw ADC — calibrate per installation

    def analyze(
        self,
        vibration_raw: int | None,
        light_lux: float | None = None,
    ) -> StressResult:
        if vibration_raw is None:
            return StressResult(
                condition="activity_signal",
                severity=Severity.NONE,
                title="Activity Signal Unavailable",
                explanation="Vibration sensor data is not available.",
            )

        if vibration_raw >= self.ELEVATED_THRESHOLD:
            return StressResult(
                condition="activity_signal",
                severity=Severity.LOW,
                title="Activity Signal Elevated",
                explanation=(
                    f"The vibration sensor detected elevated activity "
                    f"(signal: {vibration_raw}). This may indicate movement in the field "
                    "and warrants a physical inspection. "
                    "This signal alone does not identify a specific cause."
                ),
                contributing_factors={"vibration_raw": vibration_raw, "light_lux": light_lux},
                recommended_action="Conduct a field inspection to determine the cause of activity.",
            )

        return StressResult(
            condition="activity_signal",
            severity=Severity.NONE,
            title="Activity Normal",
            explanation=f"Vibration sensor readings are within normal range (signal: {vibration_raw}).",
        )
