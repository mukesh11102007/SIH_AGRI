"""
WebSocket Connection Manager.

Manages all connected frontend clients and broadcasts real-time
updates when new sensor readings arrive.

Clients subscribe by farm_id — they receive updates for all fields in that farm.
"""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        # farm_id → set of connected WebSockets
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, farm_id: str) -> None:
        await websocket.accept()
        if farm_id not in self._connections:
            self._connections[farm_id] = set()
        self._connections[farm_id].add(websocket)
        logger.info("ws_client_connected", farm=farm_id, total=len(self._connections[farm_id]))

    def disconnect(self, websocket: WebSocket, farm_id: str) -> None:
        if farm_id in self._connections:
            self._connections[farm_id].discard(websocket)
            if not self._connections[farm_id]:
                del self._connections[farm_id]
        logger.info("ws_client_disconnected", farm=farm_id)

    async def broadcast_to_farm(self, farm_id: str, data: dict[str, Any]) -> None:
        """Send a message to all clients subscribed to a farm."""
        if farm_id not in self._connections:
            return

        message = {**data, "server_timestamp": datetime.now(timezone.utc).isoformat()}
        dead: set[WebSocket] = set()

        for ws in list(self._connections[farm_id]):
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)

        for ws in dead:
            self._connections[farm_id].discard(ws)

    def connection_count(self) -> int:
        return sum(len(v) for v in self._connections.values())


# Singleton manager
_manager = ConnectionManager()


def get_manager() -> ConnectionManager:
    return _manager


async def broadcast_field_update(field_id: str, data: dict[str, Any]) -> None:
    """
    Broadcast a field update to all farms that contain this field.
    Called from the ingestion pipeline after each reading is processed.
    """
    # For simplicity we broadcast to all farms — in production,
    # look up the farm_id for this field_id
    for farm_id, connections in list(_manager._connections.items()):
        if connections:
            await _manager.broadcast_to_farm(farm_id, {**data, "field_id": field_id})
