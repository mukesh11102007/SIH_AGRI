"""
Application configuration using pydantic-settings.
All settings are loaded from environment variables with sensible defaults.
No secrets are hard-coded.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────
    app_env: str = "development"
    app_name: str = "Smart Farming Platform"
    app_version: str = "1.0.0"
    log_level: str = "INFO"
    secret_key: str = "changeme_at_least_32_char_secret_key_here"

    # ── Database ─────────────────────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "smartfarm"
    postgres_user: str = "farmuser"
    postgres_password: str = "changeme_strong_password"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """For Alembic (synchronous)."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── MQTT ─────────────────────────────────────────────────
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str = "farmdevice"
    mqtt_password: str = "changeme_mqtt_password"
    mqtt_client_id: str = "backend-ingest-01"

    # ── CORS ─────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ── Thresholds (defaults, overridable per crop) ──────────
    # Irrigation
    irrigation_critical_moisture_pct: float = 20.0
    irrigation_low_moisture_pct: float = 35.0
    irrigation_high_moisture_pct: float = 75.0
    # Heat stress
    heat_stress_moderate_c: float = 35.0
    heat_stress_high_c: float = 40.0
    # Device staleness
    device_stale_minutes: int = 5
    device_offline_minutes: int = 15

    # ── Hardware (HC-05 / future real sensors) ──────────────
    # HARDWARE_ENABLED must be explicitly set to true in .env when
    # physical hardware is physically connected and ready to use.
    # When false (the default), the hardware listener is never started
    # and the application runs normally using the simulator.
    hardware_enabled: bool = False

    # Identifies the HC-05 device in telemetry payloads and the database.
    # Change this if you have multiple hardware devices.
    hardware_device_id: str = "hc05-device-01"

    # Farm and field that HC-05 readings will be attributed to.
    # These must already exist in the database (seeded on startup).
    hardware_farm_id: str = "farm-001"
    hardware_field_id: str = "field-north-01"

    # Serial/Bluetooth port — DO NOT hard-code a specific port here.
    # Set HARDWARE_SERIAL_PORT=COM7 (Windows) or /dev/rfcomm0 (Linux)
    # in .env only when the HC-05 is physically paired and connected.
    hardware_serial_port: str = ""

    # Serial communication parameters — must match HC-05 firmware settings.
    hardware_baud_rate: int = 9600
    hardware_read_timeout_s: float = 2.0


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
