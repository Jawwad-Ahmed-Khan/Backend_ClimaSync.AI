"""FastAPI application factory.

Assembles middleware, exception handlers, and routers into the
application instance. Uses the lifespan context manager for
startup and shutdown lifecycle management.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import engine
from app.core.exception_handlers import register_exception_handlers
from app.core.middleware import register_middleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle."""
    logger.info("Starting %s v%s (%s)", settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT)
    yield
    await engine.dispose()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    _configure_logging()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    register_middleware(app)
    register_exception_handlers(app)
    _register_routers(app)

    # Attach slowapi limiter
    from app.core.limiter import limiter
    app.state.limiter = limiter

    return app


def _register_routers(app: FastAPI) -> None:
    """Mount all module routers with the API version prefix."""
    from app.modules.auth.controller import router as auth_router
    from app.modules.disasters.controller import router as disasters_router
    from app.modules.disasters.controller import alerts_router

    prefix = settings.API_V1_PREFIX

    app.include_router(auth_router, prefix=prefix)
    app.include_router(disasters_router, prefix=prefix)
    app.include_router(alerts_router, prefix=prefix)

    @app.get("/health", tags=["Health"])
    async def health_check() -> JSONResponse:
        """Health check endpoint — no version prefix."""
        return JSONResponse(
            content={
                "status": "healthy",
                "version": settings.APP_VERSION,
            },
        )


def _configure_logging() -> None:
    """Set up Python logging based on environment."""
    log_level = logging.DEBUG if settings.is_development else logging.INFO
    if settings.is_production:
        log_level = logging.WARNING

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
