<<<<<<< HEAD
"""WebSocket connection manager for real-time disaster alert broadcasting.

Only verified Admin connections are stored; NGO users are rejected
at the authentication layer before they ever reach this manager.
"""

from __future__ import annotations

import logging

=======
import logging
>>>>>>> 8ed4330a0f73be9ed7b8055a337a68b731e2b83a
from fastapi import WebSocket

logger = logging.getLogger(__name__)

<<<<<<< HEAD

class AdminAlertConnectionManager:
    """Tracks active admin WebSocket connections and broadcasts alert payloads."""

    def __init__(self) -> None:
        self.active_admin_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new admin connection."""
        await websocket.accept()
        self.active_admin_connections.append(websocket)
        logger.info(
            "Admin WS connected. Total active: %d",
            len(self.active_admin_connections),
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a disconnected admin connection from the pool."""
        if websocket in self.active_admin_connections:
            self.active_admin_connections.remove(websocket)
            logger.info(
                "Admin WS disconnected. Remaining: %d",
                len(self.active_admin_connections),
            )

    async def broadcast_alert(self, alert_data: dict) -> None:
        """Push a NEW_DISASTER_ALERT event to every connected admin client.

        Silently removes any connections that have gone dead.
        """
        dead_connections: list[WebSocket] = []

        for connection in self.active_admin_connections:
            try:
                await connection.send_json(
                    {
                        "event": "NEW_DISASTER_ALERT",
                        "data": alert_data,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to send to admin WS client, marking dead: %s", exc)
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)


# Singleton used by the REST endpoint and WebSocket route
admin_ws_manager = AdminAlertConnectionManager()
=======
class AlertConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Frontend client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("Frontend client disconnected.")

    async def broadcast_alert(self, alert_data: dict):
        """
        Sends the JSON payload to all connected frontend clients.
        """
        dead_connections = []
        for connection in self.active_connections:
            try:
                # Send the incoming payload exactly as received
                await connection.send_json({
                    "event": "NEW_DISASTER_ALERT",
                    "data": alert_data
                })
            except Exception as e:
                logger.error(f"Failed to send to a websocket client: {e}")
                dead_connections.append(connection)
        
        # Cleanup dead connections
        for dead in dead_connections:
            self.disconnect(dead)

ws_manager = AlertConnectionManager()
>>>>>>> 8ed4330a0f73be9ed7b8055a337a68b731e2b83a
