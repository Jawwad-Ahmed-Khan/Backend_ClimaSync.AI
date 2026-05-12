import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)

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
