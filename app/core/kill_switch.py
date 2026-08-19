"""Granular Kill Switches for API Route Isolation.

This dependency determines if a specific module is active based on
global environment configuration. If a module is deactivated, the router
intercepts ALL underlying network requests and instantly throws 503.

This future-proofs the platform for seamless Microservice transitions, 
where legacy HTTP routes can be deactivated on specific cluster nodes.
"""

import logging
from typing import Callable

from fastapi import HTTPException
from fastapi.requests import Request

from app.core.config import settings

logger = logging.getLogger(__name__)

def require_module_active(module_name: str) -> Callable:
    """Dependency injection factory for modular route gating."""
    
    async def _dependency(request: Request) -> None:
        # We assume the config object has a dict mapping module status
        # Example: settings.ACTIVE_MODULES = {"auth": True, "admin": True, "social": False}
        
        is_active = getattr(settings, f"MODULE_{module_name.upper()}_ENABLED", True)
        
        if not is_active:
            logger.warning(f"Blocked access to deactivated module '{module_name}' | Endpoint: {request.url.path}")
            raise HTTPException(
                status_code=503,
                detail=f"The '{module_name}' service is currently disabled or has been scaled down.",
                headers={"Retry-After": "300"}
            )
            
    return _dependency
