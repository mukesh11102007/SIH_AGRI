"""
Tests for the Decision Engine — irrigation, stress detectors, and edge cases.
These tests do NOT use mocks; they test real logic directly.
"""
import pytest
from datetime import datetime, timezone
from app.services.decision_engine.irrigation import (
    IrrigationAnalyzer, IrrigationDecision, CropThresholds, Severity
)
from app.services.decision_engine.stress import (
    HeatStressDetector, WaterStressDetector,
    ExcessMoistureDetector, WaterAvailabilityTracker,
    ActivitySignalAnalyzer,
)

analyzer = IrrigationAnalyzer()
heat_detector = HeatStressDetector()
water_stress_detector = WaterStressDetector()
excess_detector = ExcessMoistureDetector()
water_tracker = WaterAvailabilityTracker()
activity_analyzer = ActivitySignalAnalyzer()
default_crop = CropThresholds()


class TestIrrigationAnalyzer:

    def test_normal_conditions(self):
        result = analyzer.analyze(
            soil_moisture_pct=60.0, air_temperature_c=25.0,
            air_humidity_pct=65.0, soil_temperature_c=22.0,
            light_lux=30000, leaf_wetness_pct=10.0,
            water_level_available=True, crop=default_crop,
        )
        assert result.decision == IrrigationDecision.NORMAL
        assert result.severity == Severity.NONE

    def test_critical_soil_moisture_triggers_recommendation(self):
        result = analyzer.analyze(
            soil_moisture_pct=15.0,  # Below critical threshold (20%)
            air_temperature_c=36.0,
            air_humidity_pct=30.0,
            soil_temperature_c=32.0,
            light_lux=60000,
            leaf_wetness_pct=5.0,
            water_level_available=True,
            crop=default_crop,
        )
        assert result.decision == IrrigationDecision.IRRIGATION_RECOMMENDED
        assert result.severity in (Severity.HIGH, Severity.CRITICAL)

    def test_water_unavailable_blocks_irrigation(self):
        result = analyzer.analyze(
            soil_moisture_pct=10.0,  # Critically low
            air_temperature_c=40.0,
            air_humidity_pct=20.0,
            soil_temperature_c=35.0,
            light_lux=80000,
            leaf_wetness_pct=0.0,
            water_level_available=False,  # No water
            crop=default_crop,
        )
        assert result.decision == IrrigationDecision.IRRIGATION_BLOCKED

    def test_excess_moisture_prevents_irrigation(self):
        result = analyzer.analyze(
            soil_moisture_pct=85.0,  # Very wet
            air_temperature_c=25.0,
            air_humidity_pct=80.0,
            soil_temperature_c=22.0,
            light_lux=10000,
            leaf_wetness_pct=80.0,
            water_level_available=True,
            crop=default_crop,
        )
        assert result.decision == IrrigationDecision.EXCESS_MOISTURE

    def test_monitor_state_for_borderline_moisture(self):
        result = analyzer.analyze(
            soil_moisture_pct=32.0,  # Below optimal (40%) but above critical (20%)
            air_temperature_c=28.0,
            air_humidity_pct=55.0,
            soil_temperature_c=25.0,
            light_lux=40000,
            leaf_wetness_pct=5.0,
            water_level_available=True,
            crop=default_crop,
        )
        assert result.decision == IrrigationDecision.MONITOR

    def test_zero_soil_moisture_critical(self):
        result = analyzer.analyze(
            soil_moisture_pct=0.0,
            air_temperature_c=35.0,
            air_humidity_pct=25.0,
            soil_temperature_c=30.0,
            light_lux=70000,
            leaf_wetness_pct=0.0,
            water_level_available=True,
            crop=default_crop,
        )
        assert result.decision == IrrigationDecision.IRRIGATION_RECOMMENDED
        assert result.severity == Severity.CRITICAL

    def test_leaf_wetness_reduces_urgency(self):
        """High leaf wetness should reduce the irrigation score slightly."""
        result_wet = analyzer.analyze(
            soil_moisture_pct=32.0, air_temperature_c=28.0,
            air_humidity_pct=55.0, soil_temperature_c=25.0,
            light_lux=40000, leaf_wetness_pct=80.0,  # Very wet leaves
            water_level_available=True, crop=default_crop,
        )
        result_dry = analyzer.analyze(
            soil_moisture_pct=32.0, air_temperature_c=28.0,
            air_humidity_pct=55.0, soil_temperature_c=25.0,
            light_lux=40000, leaf_wetness_pct=0.0,  # Dry leaves
            water_level_available=True, crop=default_crop,
        )
        # Wet leaves should produce lower or equal score
        assert result_wet.score <= result_dry.score

    def test_custom_crop_thresholds(self):
        rice = CropThresholds(
            optimal_moisture_min_pct=55.0,
            optimal_moisture_max_pct=80.0,
            critical_moisture_min_pct=30.0,
        )
        # 35% moisture: below rice minimum but above default minimum
        result_rice = analyzer.analyze(
            soil_moisture_pct=35.0, air_temperature_c=26.0,
            air_humidity_pct=70.0, soil_temperature_c=24.0,
            light_lux=40000, leaf_wetness_pct=10.0,
            water_level_available=True, crop=rice,
        )
        result_default = analyzer.analyze(
            soil_moisture_pct=35.0, air_temperature_c=26.0,
            air_humidity_pct=70.0, soil_temperature_c=24.0,
            light_lux=40000, leaf_wetness_pct=10.0,
            water_level_available=True, crop=default_crop,
        )
        # Rice needs more water — should have higher urgency
        assert result_rice.score >= result_default.score

    def test_reasoning_is_not_empty(self):
        result = analyzer.analyze(
            soil_moisture_pct=18.0, air_temperature_c=39.0,
            air_humidity_pct=22.0, soil_temperature_c=33.0,
            light_lux=75000, leaf_wetness_pct=2.0,
            water_level_available=True, crop=default_crop,
        )
        assert result.reasoning
        assert len(result.reasoning) > 20

    def test_contributing_factors_present(self):
        result = analyzer.analyze(
            soil_moisture_pct=20.0, air_temperature_c=37.0,
            air_humidity_pct=28.0, soil_temperature_c=30.0,
            light_lux=65000, leaf_wetness_pct=5.0,
            water_level_available=True, crop=default_crop,
        )
        assert "soil_moisture_pct" in result.contributing_factors

    def test_all_none_readings(self):
        """System should handle None readings gracefully."""
        result = analyzer.analyze(
            soil_moisture_pct=None, air_temperature_c=None,
            air_humidity_pct=None, soil_temperature_c=None,
            light_lux=None, leaf_wetness_pct=None,
            water_level_available=None, crop=default_crop,
        )
        # Should not crash; should produce a reasonable state
        assert result.decision is not None


class TestHeatStressDetector:

    def test_no_stress_normal_temp(self):
        result = heat_detector.analyze(
            air_temperature_c=28.0, soil_temperature_c=24.0,
            air_humidity_pct=60.0, light_lux=30000,
        )
        assert result.severity == Severity.NONE

    def test_high_stress_extreme_temp(self):
        result = heat_detector.analyze(
            air_temperature_c=43.0, soil_temperature_c=38.0,
            air_humidity_pct=18.0, light_lux=90000,
        )
        assert result.severity in (Severity.HIGH, Severity.CRITICAL)

    def test_all_none_no_crash(self):
        result = heat_detector.analyze(
            air_temperature_c=None, soil_temperature_c=None,
            air_humidity_pct=None, light_lux=None,
        )
        assert result.severity == Severity.NONE


class TestWaterStressDetector:

    def test_critical_low_moisture_high_temp(self):
        result = water_stress_detector.analyze(
            soil_moisture_pct=10.0, air_temperature_c=40.0,
            air_humidity_pct=20.0,
        )
        assert result.severity in (Severity.HIGH, Severity.CRITICAL)

    def test_no_stress_adequate_moisture(self):
        result = water_stress_detector.analyze(
            soil_moisture_pct=65.0, air_temperature_c=26.0,
            air_humidity_pct=60.0,
        )
        assert result.severity == Severity.NONE

    def test_none_moisture_returns_no_data(self):
        result = water_stress_detector.analyze(
            soil_moisture_pct=None, air_temperature_c=30.0,
            air_humidity_pct=50.0,
        )
        assert "unavailable" in result.explanation.lower()


class TestWaterAvailability:

    def test_available(self):
        result = water_tracker.analyze(True)
        assert result.severity == Severity.NONE

    def test_unavailable(self):
        result = water_tracker.analyze(False)
        assert result.severity == Severity.CRITICAL

    def test_unknown(self):
        result = water_tracker.analyze(None)
        assert result.severity == Severity.LOW


class TestActivitySignal:

    def test_normal_vibration(self):
        result = activity_analyzer.analyze(vibration_raw=50)
        assert result.severity == Severity.NONE

    def test_elevated_vibration(self):
        result = activity_analyzer.analyze(vibration_raw=800)
        assert result.severity == Severity.LOW
        # Must NOT claim to identify a specific pest
        assert "pest" not in result.explanation.lower() or "does not identify" in result.explanation.lower()

    def test_none_vibration(self):
        result = activity_analyzer.analyze(vibration_raw=None)
        assert result is not None


class TestTelemetryValidation:

    def test_valid_payload(self):
        from datetime import timezone
        from app.schemas.telemetry import TelemetryPayload, SensorReadings, SensorStatus
        from app.ingestion.validator import validate_telemetry

        payload = TelemetryPayload(
            device_id="test-device-01",
            farm_id="farm-001",
            field_id="field-001",
            timestamp_utc=datetime.now(timezone.utc),
            source="simulator",
            sequence_number=1,
            readings=SensorReadings(
                air_temperature_c=28.0,
                air_humidity_pct=65.0,
                soil_moisture_pct=50.0,
            ),
            sensor_status=SensorStatus(),
        )
        result = validate_telemetry(payload)
        assert result.is_valid

    def test_sensor_error_flagged(self):
        from datetime import timezone
        from app.schemas.telemetry import TelemetryPayload, SensorReadings, SensorStatus
        from app.ingestion.validator import validate_telemetry

        payload = TelemetryPayload(
            device_id="test-device-01",
            farm_id="farm-001",
            field_id="field-001",
            timestamp_utc=datetime.now(timezone.utc),
            source="simulator",
            sequence_number=2,
            readings=SensorReadings(air_temperature_c=28.0),
            sensor_status=SensorStatus(dht22="error"),
        )
        result = validate_telemetry(payload)
        assert result.is_valid  # Still valid — just flagged
        assert "dht22" in result.flags
