"""
Example: Exception Hierarchy & Global Handlers
================================================
Reference implementation of a custom exception hierarchy with global
exception handlers that produce structured error responses (RFC 7807).

Location: app/core/exceptions.py
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTION HIERARCHY
# ═══════════════════════════════════════════════════════════════════════════════


class AppException(Exception):
    """Base exception for all application errors.

    All custom exceptions MUST extend this class.
    Services and repositories should raise AppException subclasses,
    NEVER HTTPException (that's for the router/dependency layer only).

    Attributes:
        message: Human-readable error message.
        status_code: HTTP status code (used by the global handler).
        error_code: Machine-readable error code for client consumption.
        details: Additional context (field errors, constraints, etc.).
    """

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


# ─── 4xx Client Errors ──────────────────────────────────────────────────────


class BadRequestError(AppException):
    """400 — The request was malformed or contains invalid data."""

    def __init__(
        self,
        message: str = "Bad request",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=400,
            error_code="BAD_REQUEST",
            details=details,
        )


class UnauthorizedError(AppException):
    """401 — Authentication is required or has failed."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(
            message=message,
            status_code=401,
            error_code="UNAUTHORIZED",
        )


class ForbiddenError(AppException):
    """403 — The authenticated user lacks permission."""

    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(
            message=message,
            status_code=403,
            error_code="FORBIDDEN",
        )


class NotFoundError(AppException):
    """404 — The requested resource does not exist."""

    def __init__(self, resource: str = "Resource", id: Any = None) -> None:
        detail = f"{resource} not found" + (f": {id}" if id else "")
        super().__init__(
            message=detail,
            status_code=404,
            error_code="NOT_FOUND",
        )


class ConflictError(AppException):
    """409 — The request conflicts with the current state (e.g., duplicate)."""

    def __init__(self, message: str = "Resource already exists") -> None:
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT",
        )


class ValidationError(AppException):
    """422 — Business rule validation failed (not schema validation)."""

    def __init__(
        self,
        message: str = "Validation failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class RateLimitError(AppException):
    """429 — Too many requests."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int = 60,
    ) -> None:
        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMITED",
            details={"retry_after_seconds": retry_after},
        )


# ─── 5xx Server Errors ──────────────────────────────────────────────────────


class ServiceUnavailableError(AppException):
    """503 — An upstream service or dependency is unavailable."""

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        service: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=503,
            error_code="SERVICE_UNAVAILABLE",
            details={"service": service} if service else {},
        )


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL EXCEPTION HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════


def _error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: dict[str, Any] | list | None = None,
) -> JSONResponse:
    """Create a standardized error response.

    Response format (RFC 7807 inspired):
    {
        "error": {
            "code": "NOT_FOUND",
            "message": "User not found: abc-123",
            "details": {}
        }
    }
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error_code,
                "message": message,
                "details": details or {},
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI app.

    Call this in create_app() before mounting routers.
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request, exc: AppException
    ) -> JSONResponse:
        """Handle all AppException subclasses."""
        log_fn = logger.error if exc.status_code >= 500 else logger.warning
        log_fn(
            "AppException: %s (code=%s, status=%d, path=%s)",
            exc.message,
            exc.error_code,
            exc.status_code,
            request.url.path,
        )
        return _error_response(
            status_code=exc.status_code,
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic/FastAPI request validation errors."""
        logger.warning(
            "Validation error on %s %s: %s",
            request.method,
            request.url.path,
            exc.errors(),
        )
        return _error_response(
            status_code=422,
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            details=exc.errors(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Handle Starlette/FastAPI HTTPExceptions (404 not found, etc.)."""
        return _error_response(
            status_code=exc.status_code,
            error_code="HTTP_ERROR",
            message=str(exc.detail),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Catch-all for unhandled exceptions.

        IMPORTANT: Never expose internal error details to clients.
        Always log the full exception for debugging.
        """
        logger.exception(
            "Unhandled exception on %s %s: %s",
            request.method,
            request.url.path,
            str(exc),
        )
        return _error_response(
            status_code=500,
            error_code="INTERNAL_ERROR",
            message="An internal server error occurred",
        )
