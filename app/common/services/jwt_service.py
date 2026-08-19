"""System-wide JSON Web Token management."""

import uuid
from typing import Mapping, Any
from app.core.security import create_access_token, create_refresh_token

class JwtService:
    """Consolidated signature rules ensuring identical token math across Admins & NGOs."""

    @staticmethod
    def generate_tokens(user_id: uuid.UUID, role: str) -> tuple[str, str]:
        """Create JWT access and refresh token pair globally."""
        subject = str(user_id)
        # Pack strictly typed claims
        claims = {"role": role}
        
        access = create_access_token(subject, claims)
        refresh = create_refresh_token(subject)
        
        return access, refresh
