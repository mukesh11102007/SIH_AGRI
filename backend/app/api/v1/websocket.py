"""WebSocket route — real-time farm updates to dashboard clients."""
from __future__ import annotations
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket.manager import get_manager
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.websocket("/ws/farm/{farm_id}")
async def websocket_farm_updates(websocket: WebSocket, farm_id: str) -> None:
    """
    WebSocket endpoint for real-time farm updates.

    Client connects to: ws://host:8000/ws/farm/{farm_id}

    Messages pushed:
    - sensor_update: new validated reading processed
    - new_alert: alert created or updated
    - device_status: device connectivity change
    """
    manager = get_manager()
    await manager.connect(websocket, farm_id)
    try:
        # Send initial connection acknowledgement
        await websocket.send_json({
            "event": "connected",
            "farm_id": farm_id,
            "message": "Real-time farm updates active.",
        })
        # Keep connection alive — the manager broadcasts to us
        while True:
            # Receive any client messages (e.g. ping/pong)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, farm_id)
    except Exception as exc:
        logger.error("websocket_error", farm=farm_id, error=str(exc))
        manager.disconnect(websocket, farm_id)
