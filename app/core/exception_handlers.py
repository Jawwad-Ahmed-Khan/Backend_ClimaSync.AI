"""Global exception handlers mapping domain exceptions to HTTP responses.

This is the ONLY place where domain exceptions are converted to HTTP
status codes. Controllers NEVER catch domain exceptions — they propagate
here automatically.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.extension import _rate_limit_exceeded_handler

from app.core.config import settings
from app.core.exceptions import (
    AlreadyExistsException,
    AppException,
    BadRequestException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)

logger = logging.getLogger(__name__)

_STATUS_NOT_FOUND = 404
_STATUS_UNAUTHORIZED = 401
_STATUS_FORBIDDEN = 403
_STATUS_CONFLICT = 409
_STATUS_BAD_REQUEST = 400
_STATUS_UNPROCESSABLE = 422
_STATUS_INTERNAL = 500


async def _not_found_handler(
    request: Request,
    exc: NotFoundException,
) -> JSONResponse:
    """Handle NotFoundException → 404."""
    logger.info("Not found: %s %s — %s", request.method, request.url.path, exc.detail)
    return JSONResponse(
        status_code=_STATUS_NOT_FOUND,
        content={"detail": exc.detail},
    )


async def _already_exists_handler(
    request: Request,
    exc: AlreadyExistsException,
) -> JSONResponse:
    """Handle AlreadyExistsException → 409."""
    logger.info("Conflict: %s %s — %s", request.method, request.url.path, exc.detail)
    return JSONResponse(
        status_code=_STATUS_CONFLICT,
        content={"detail": exc.detail},
    )


async def _unauthorized_handler(
    request: Request,
    exc: UnauthorizedException,
) -> JSONResponse:
    """Handle UnauthorizedException → 401."""
    logger.info(
        "Unauthorized: %s %s — %s", request.method, request.url.path, exc.detail,
    )
    return JSONResponse(
        status_code=_STATUS_UNAUTHORIZED,
        content={"detail": exc.detail},
    )


async def _forbidden_handler(
    request: Request,
    exc: ForbiddenException,
) -> JSONResponse:
    """Handle ForbiddenException → 403."""
    logger.info("Forbidden: %s %s — %s", request.method, request.url.path, exc.detail)
    return JSONResponse(
        status_code=_STATUS_FORBIDDEN,
        content={"detail": exc.detail},
    )


async def _bad_request_handler(
    request: Request,
    exc: BadRequestException,
) -> JSONResponse:
    """Handle BadRequestException → 400."""
    logger.info("Bad request: %s %s — %s", request.method, request.url.path, exc.detail)
    return JSONResponse(
        status_code=_STATUS_BAD_REQUEST,
        content={"detail": exc.detail},
    )


async def _validation_handler(
    request: Request,
    exc: ValidationException,
) -> JSONResponse:
    """Handle ValidationException → 422."""
    logger.info(
        "Validation: %s %s — %s", request.method, request.url.path, exc.detail,
    )
    return JSONResponse(
        status_code=_STATUS_UNPROCESSABLE,
        content={"detail": exc.detail},
    )


async def _app_exception_handler(
    request: Request,
    exc: AppException,
) -> JSONResponse:
    """Handle any unhandled AppException → 500."""
    logger.error(
        "Unhandled app error: %s %s — %s",
        request.method,
        request.url.path,
        exc.detail,
        exc_info=True,
    )
    detail = exc.detail if settings.is_development else "Internal server error"
    return JSONResponse(
        status_code=_STATUS_INTERNAL,
        content={"detail": detail},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all domain exception handlers on the FastAPI app."""
    app.add_exception_handler(NotFoundException, _not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(AlreadyExistsException, _already_exists_handler)  # type: ignore[arg-type]
    app.add_exception_handler(UnauthorizedException, _unauthorized_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ForbiddenException, _forbidden_handler)  # type: ignore[arg-type]
    app.add_exception_handler(BadRequestException, _bad_request_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ValidationException, _validation_handler)  # type: ignore[arg-type]
    app.add_exception_handler(AppException, _app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
