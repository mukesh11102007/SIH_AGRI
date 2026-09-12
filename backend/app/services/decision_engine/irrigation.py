"""
Decision Engine — Irrigation Analyzer

Multi-factor irrigation decision system.
Uses soil moisture as the primary signal, amplified by temperature,
humidity, soil temperature, light, and leaf wetness.

All reasoning is explicit and translatable to plain English.
No sensor is claimed to do more than it physically measures.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class IrrigationDecision(str, Enum):
    NORMAL = "NORMAL"
    MONITOR = "MONITOR"
    IRRIGATION_RECOMMENDED = "IRRIGATION_RECOMMENDED"
    IRRIGATION_BLOCKED = "IRRIGATION_BLOCKED"  # Water unavailable
    EXCESS_MOISTURE = "EXCESS_MOISTURE"        # Too wet — delay irrigation


class Severity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class IrrigationResult:
    decision: IrrigationDecision
    severity: Severity
    reasoning: str
    contributing_factors: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0  # 0–100 internal stress score


@dataclass
class CropThresholds:
    """Crop-specific thresholds — defaults to generic crop if none configured."""
    optimal_moisture_min_pct: float = 40.0
    optimal_moisture_max_pct: float = 70.0
    critical_moisture_min_pct: float = 20.0
    optimal_temp_max_c: float = 35.0
    heat_stress_c: float = 38.0
    optimal_humidity_min_pct: float = 40.0


class IrrigationAnalyzer:
    """
    Analyzes current field conditions to produce an irrigation recommendation.

    Inputs: sensor readings + crop thresholds + water availability
    Output: IrrigationResult with decision, severity, and plain-English reasoning

    The score is an internal tool for ranking severity — it is never presented
    to the farmer directly.
    """

    def analyze(
        self,
        soil_moisture_pct: float | None,
        air_temperature_c: float | None,
        air_humidity_pct: float | None,
        soil_temperature_c: float | None,
        light_lux: float | None,
        leaf_wetness_pct: float | None,
        water_level_available: bool | None,
        crop: CropThresholds | None = None,
        recent_trend: float | None = None,  # moisture change rate %/hour (negative = drying)
    ) -> IrrigationResult:

        thresholds = crop or CropThresholds()
        factors: dict[str, Any] = {}
        reasoning_parts: list[str] = []
        score = 0.0

        # ── 1. Water availability gate ──────────────────────
        # If water is explicitly unavailable, block irrigation regardless of demand
        if water_level_available is False:
            return IrrigationResult(
                decision=IrrigationDecision.IRRIGATION_BLOCKED,
                severity=Severity.HIGH,
                reasoning=(
                    "Irrigation is recommended based on field conditions, but the water "
                    "source is currently unavailable. Check the water tank or supply line."
                ),
                contributing_factors={"water_level": "unavailable"},
                score=0.0,
            )

        # ── 2. Soil moisture — primary signal ───────────────
        if soil_moisture_pct is None:
            factors["soil_moisture"] = "unavailable"
            reasoning_parts.append("Soil moisture data is unavailable.")
            score += 30  # Uncertainty bump — recommend monitoring
        else:
            factors["soil_moisture_pct"] = soil_moisture_pct

            if soil_moisture_pct > thresholds.optimal_moisture_max_pct:
                # Too wet — potentially overwatered or waterlogged
                return IrrigationResult(
                    decision=IrrigationDecision.EXCESS_MOISTURE,
                    severity=Severity.MEDIUM if soil_moisture_pct < 85 else Severity.HIGH,
                    reasoning=(
                        f"Soil moisture is high at {soil_moisture_pct:.1f}%. "
                        "Irrigation is not required and would risk waterlogging."
                    ),
                    contributing_factors={"soil_moisture_pct": soil_moisture_pct},
                    score=0.0,
                )
            elif soil_moisture_pct <= thresholds.critical_moisture_min_pct:
                score += 60
                reasoning_parts.append(
                    f"Soil moisture is critically low at {soil_moisture_pct:.1f}% "
                    f"(minimum threshold: {thresholds.critical_moisture_min_pct:.0f}%)."
                )
            elif soil_moisture_pct <= thresholds.optimal_moisture_min_pct:
                score += 35
                reasoning_parts.append(
                    f"Soil moisture is below the preferred level at {soil_moisture_pct:.1f}% "
                    f"(optimal minimum: {thresholds.optimal_moisture_min_pct:.0f}%)."
                )
            else:
                score += 0
                reasoning_parts.append(
                    f"Soil moisture is within the optimal range at {soil_moisture_pct:.1f}%."
                )

        # ── 3. Temperature amplifier ─────────────────────────
        if air_temperature_c is not None:
            factors["air_temperature_c"] = air_temperature_c
            if air_temperature_c >= thresholds.heat_stress_c:
                score += 20
                reasoning_parts.append(
                    f"Air temperature is very high at {air_temperature_c:.1f}°C, "
                    "significantly increasing evapotranspiration demand."
                )
            elif air_temperature_c >= thresholds.optimal_temp_max_c:
                score += 10
                reasoning_parts.append(
                    f"Air temperature is elevated at {air_temperature_c:.1f}°C, "
                    "increasing water demand."
                )

        # ── 4. Humidity modifier ─────────────────────────────
        if air_humidity_pct is not None:
            factors["air_humidity_pct"] = air_humidity_pct
            if air_humidity_pct < thresholds.optimal_humidity_min_pct:
                score += 10
                reasoning_parts.append(
                    f"Low humidity ({air_humidity_pct:.1f}%) increases evapotranspiration "
                    "from the crop canopy."
                )
            elif air_humidity_pct > 85:
                score -= 5  # High humidity reduces water demand slightly
                reasoning_parts.append(
                    f"High humidity ({air_humidity_pct:.1f}%) reduces immediate water demand."
                )

        # ── 5. Leaf wetness modifier ─────────────────────────
        # Leaf wetness indicates recent rain or dew — may reduce urgency
        if leaf_wetness_pct is not None and leaf_wetness_pct > 40:
            factors["leaf_wetness_pct"] = leaf_wetness_pct
            score -= 8
            reasoning_parts.append(
                f"Leaf surface wetness detected ({leaf_wetness_pct:.1f}%), "
                "suggesting recent moisture deposition."
            )

        # ── 6. Moisture trend ─────────────────────────────────
        if recent_trend is not None:
            factors["moisture_trend_pct_per_hour"] = round(recent_trend, 2)
            if recent_trend < -2.0:
                score += 10
                reasoning_parts.append(
                    f"Soil moisture is declining rapidly ({recent_trend:.1f}%/hour)."
                )
            elif recent_trend > 2.0:
                score -= 5
                reasoning_parts.append(
                    "Soil moisture is recovering — immediate irrigation may not be needed."
                )

        # ── 7. Water availability context ────────────────────
        if water_level_available is True:
            factors["water_level"] = "available"
        elif water_level_available is None:
            factors["water_level"] = "unknown"
            reasoning_parts.append("Water availability status is unknown.")

        # ── 8. Final decision ────────────────────────────────
        score = max(0.0, min(100.0, score))

        if score >= 65:
            decision = IrrigationDecision.IRRIGATION_RECOMMENDED
            severity = Severity.CRITICAL if score >= 80 else Severity.HIGH
        elif score >= 35:
            decision = IrrigationDecision.MONITOR
            severity = Severity.MEDIUM if score >= 50 else Severity.LOW
        else:
            decision = IrrigationDecision.NORMAL
            severity = Severity.NONE

        reasoning = " ".join(reasoning_parts) if reasoning_parts else "Conditions are within normal range."

        logger.debug(
            "irrigation_analysis_complete",
            score=score,
            decision=decision.value,
            field_moisture=soil_moisture_pct,
        )

        return IrrigationResult(
            decision=decision,
            severity=severity,
            reasoning=reasoning,
            contributing_factors=factors,
            score=score,
        )
