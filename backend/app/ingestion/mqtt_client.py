"""
MQTT Client — subscribes to all farm telemetry topics and feeds
incoming messages into the ingestion pipeline.

Uses aiomqtt (async) so it runs alongside FastAPI without blocking.
The MQTT loop runs as a background asyncio task.
"""
from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiomqtt

from app.ingestion.pipeline import ingest_raw_message
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Topic pattern — subscribes to all device telemetry across all farms/fields
TELEMETRY_TOPIC = "farm/+/field/+/device/+/telemetry"
STATUS_TOPIC = "farm/+/field/+/device/+/status"


async def _mqtt_listener() -> None:
    """
    Long-running MQTT subscription loop.
    Reconnects automatically on disconnect.
    """
    reconnect_interval = 5  # seconds

    while True:
        try:
            logger.info(
                "mqtt_connecting",
                host=settings.mqtt_host,
                port=settings.mqtt_port,
                client_id=settings.mqtt_client_id,
            )
            async with aiomqtt.Client(
                hostname=settings.mqtt_host,
                port=settings.mqtt_port,
                username=settings.mqtt_username,
                password=settings.mqtt_password,
                identifier=settings.mqtt_client_id,
                keepalive=60,
            ) as client:
                logger.info("mqtt_connected", host=settings.mqtt_host)

                await client.subscribe(TELEMETRY_TOPIC, qos=1)
                await client.subscribe(STATUS_TOPIC, qos=0)
                logger.info("mqtt_subscribed", topics=[TELEMETRY_TOPIC, STATUS_TOPIC])

                async for message in client.messages:
                    topic = str(message.topic)
                    payload = message.payload

                    if "telemetry" in topic:
                        # Fire and forget — don't block the MQTT loop
                        asyncio.create_task(
                            _handle_telemetry(payload),
                            name=f"ingest-{topic}",
                        )
                    elif "status" in topic:
                        logger.debug("mqtt_device_status", topic=topic)

        except aiomqtt.MqttError as exc:
            logger.warning(
                "mqtt_disconnected",
                error=str(exc),
                reconnect_in=reconnect_interval,
            )
            await asyncio.sleep(reconnect_interval)
            reconnect_interval = min(reconnect_interval * 2, 60)  # Exponential backoff
        except asyncio.CancelledError:
            logger.info("mqtt_listener_cancelled")
            break
        except Exception as exc:
            logger.error("mqtt_unexpected_error", error=str(exc))
            await asyncio.sleep(reconnect_interval)


async def _handle_telemetry(payload: bytes) -> None:
    """Process a single telemetry message."""
    try:
        await ingest_raw_message(payload)
    except Exception as exc:
        logger.error("telemetry_handler_error", error=str(exc))


_mqtt_task: asyncio.Task | None = None


def start_mqtt_listener() -> None:
    """Start the MQTT listener as a background asyncio task."""
    global _mqtt_task
    _mqtt_task = asyncio.create_task(_mqtt_listener(), name="mqtt-listener")
    logger.info("mqtt_listener_started")


async def stop_mqtt_listener() -> None:
    """Gracefully cancel the MQTT listener task."""
    global _mqtt_task
    if _mqtt_task and not _mqtt_task.done():
        _mqtt_task.cancel()
        try:
            await _mqtt_task
        except asyncio.CancelledError:
            pass
    logger.info("mqtt_listener_stopped")
