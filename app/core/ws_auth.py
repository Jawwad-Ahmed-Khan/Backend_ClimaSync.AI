"""WebSocket authentication dependency.

Validates JWT tokens passed as query parameters during the WebSocket
handshake and enforces that only admin / super_admin roles are allowed.

Browser WebSocket clients cannot send custom headers, so the JWT is
passed in the URL query string:
    ws://host/ws/alerts?token=<access_jwt>
"""

from __future__ import annotations

import logging

from fastapi import Query, WebSocket, WebSocketException, status
from jose import JWTError

from app.core.security import decode_token

logger = logging.getLogger(__name__)

_ADMIN_ROLES = frozenset({"admin", "super_admin"})


async def verify_admin_ws_token(
    websocket: WebSocket,
    token: str | None = Query(default=None),
) -> dict:
    """FastAPI dependency that validates the WS JWT and enforces admin role.

    Closes the connection with WS_1008_POLICY_VIOLATION if:
    - No token is supplied
    - The token is invalid or expired
    - The token's role is not 'admin' or 'super_admin'

    Returns the decoded JWT payload on success so the endpoint can
    read claims (sub, role, etc.) if needed.
    """
    if token is None:
        logger.warning("WS connection rejected: missing token")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication token is required",
        )

    try:
        payload = decode_token(token)
    except JWTError:
        logger.warning("WS connection rejected: invalid or expired JWT")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or expired token",
        )

    # Ensure the token is an access token (not a refresh token)
    if payload.get("type") != "access":
        logger.warning("WS connection rejected: non-access token type")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Access token required",
        )

    user_role = payload.get("role", "")
    if user_role not in _ADMIN_ROLES:
        logger.warning(
            "WS connection rejected: unauthorised role '%s'", user_role
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Admin access required",
        )

    return payload
