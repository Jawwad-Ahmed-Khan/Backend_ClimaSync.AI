"""Middleware stack registration.

All middleware is registered here through register_middleware().
Order matters: first registered = outermost (CORS first, then logging).
"""

import logging
import time

from fastapi import FastAPI, Request, Response
from starlette.middleware.cors import CORSMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


async def _request_logging_middleware(
    request: Request,
    call_next: object,
) -> Response:
    """Log method, path, status code, and duration for every request."""
    start_time = time.perf_counter()
    response: Response = await call_next(request)  # type: ignore[misc]
    duration_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "%s %s → %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    response.headers["X-Process-Time-Ms"] = f"{duration_ms:.1f}"
    return response


def register_middleware(app: FastAPI) -> None:
    """Register all middleware on the application (outermost first)."""
    # CORS — must be outermost
    cors_origins = settings.CORS_ORIGINS
    if settings.is_production and "*" in cors_origins:
        msg = "CORS allow_origins=['*'] is forbidden in production"
        raise ValueError(msg)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging
    app.middleware("http")(_request_logging_middleware)
