"""Dependency injection functions for admin workflow module.

This module provides FastAPI dependencies for:
- Agent API key authentication
- JWT token authentication
- Database session management
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_db
from app.core.security import decode_token
from app.modules.admin_workflow.models import AdminUser

logger = logging.getLogger(__name__)


# ============================================================================
# Task 9.1: Agent API Key Authentication
# ============================================================================


def verify_agent_api_key(authorization: str = Header(..., alias="Authorization")) -> None:
    """Verify agent API key from Authorization header.
    
    Extracts the API key from the Authorization header and compares it
    with the configured AGENT_API_KEY. Raises 401 Unauthorized if invalid.
    
    Args:
        authorization: Authorization header value (format: "Agent_API_Key <key>")
        
    Raises:
        HTTPException: 401 Unauthorized if API key is invalid or missing
        
    Requirements: 3.2, 3.3, 12.2, 12.4, 12.7
    """
    # Extract API key from header
    # Expected format: "Agent_API_Key <key>"
    if not authorization:
        logger.warning("Agent API key authentication failed - missing header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Agent API key",
        )
    
    # Parse the header
    parts = authorization.split()
    if len(parts) != 2 or parts[0] != "Agent_API_Key":
        logger.warning(
            "Agent API key authentication failed - invalid format",
            extra={"authorization": authorization[:20] + "..."},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Agent API key format",
        )
    
    provided_key = parts[1]
    
    # Compare with configured key
    if provided_key != settings.AGENT_API_KEY:
        logger.warning(
            "Agent API key authentication failed - invalid key",
            extra={"provided_key": provided_key[:10] + "..."},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Agent API key",
        )
    
    logger.debug("Agent API key authentication successful")


# ============================================================================
# JWT Token Authentication (Task 19.1)
# ============================================================================


async def get_current_admin_user(
    authorization: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db),
) -> AdminUser:
    """Extract and validate JWT token, return admin user.
    
    Args:
        authorization: Authorization header value (format: "Bearer <token>")
        db: Database session
        
    Returns:
        Authenticated AdminUser instance
        
    Raises:
        HTTPException: 401 Unauthorized if token is invalid or user not found
        
    Requirements: 12.1, 12.3, 12.5, 12.6
    """
    try:
        # Extract token from Bearer header
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format",
            )
        
        token = authorization.replace("Bearer ", "")
        
        # Decode token
        payload = decode_token(token)
        user_id = UUID(payload["sub"])
        
        # Query user from database
        user = db.query(AdminUser).filter(AdminUser.user_id == user_id).first()
        
        if not user:
            logger.warning(
                "JWT authentication failed - user not found",
                extra={"user_id": str(user_id)},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        if not user.is_active:
            logger.warning(
                "JWT authentication failed - inactive user",
                extra={"user_id": str(user_id)},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
            )
        
        return user
        
    except ValueError as e:
        logger.warning(
            "JWT authentication failed - invalid token",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    except Exception as e:
        logger.error(
            "JWT authentication failed - unexpected error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


# Type aliases for dependency injection
AgentApiKeyDep = Annotated[None, Depends(verify_agent_api_key)]
CurrentAdminUser = Annotated[AdminUser, Depends(get_current_admin_user)]
