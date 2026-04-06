"""
Example: Custom Middleware
===========================
Reference implementation of custom middleware including request ID tracking,
timing, CORS configuration, and rate limiting setup.

Location: app/core/middleware.py
"""

import logging
import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.config import settings

logger = logging.getLogger(__name__)


# ─── Middleware Registration ─────────────────────────────────────────────────


def register_middleware(app: FastAPI) -> None:
    """Register all middleware on the application.

    Order matters:
    - First registered = outermost (processes request first, response last).
    - CORS must be outermost for preflight requests to work.
    - Request ID should be early so all downstream middleware can use it.
    - Timing should be innermost to measure actual processing time.
    """

    # 1. CORS — outermost
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
        expose_headers=["X-Request-ID", "X-Process-Time-Ms"],
    )

    # 2. Trusted Hosts — production only
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=getattr(settings, "ALLOWED_HOSTS", ["*"]),
        )

    # 3. Security Headers
    app.add_middleware(SecurityHeadersMiddleware)

    # 4. Request ID
    app.add_middleware(RequestIdMiddleware)

    # 5. Request Timing — innermost
    app.add_middleware(TimingMiddleware)


# ─── Request ID Middleware ───────────────────────────────────────────────────


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request/response.

    - Reads existing X-Request-ID from incoming request headers (for tracing).
    - Generates a new UUID4 if none is provided.
    - Stores on request.state.request_id for use in logging and dependencies.
    - Includes X-Request-ID in response headers for client correlation.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ─── Timing Middleware ───────────────────────────────────────────────────────


class TimingMiddleware(BaseHTTPMiddleware):
    """Measure and log request processing time.

    - Uses perf_counter for high-resolution timing.
    - Logs method, path, status code, and duration.
    - Includes X-Process-Time-Ms in response headers.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        # Log at appropriate level based on duration
        log_fn = logger.warning if duration_ms > 1000 else logger.info
        log_fn(
            "%s %s → %d (%.2fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
        return response


# ─── Security Headers Middleware ─────────────────────────────────────────────


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security-related headers to all responses.

    Headers:
    - X-Content-Type-Options: Prevent MIME sniffing
    - X-Frame-Options: Prevent clickjacking
    - X-XSS-Protection: Enable browser XSS filter
    - Strict-Transport-Security: Force HTTPS
    - Content-Security-Policy: Restrict resource loading
    - Referrer-Policy: Control referer header leaks
    - Permissions-Policy: Restrict browser features
    """

    SECURITY_HEADERS: dict[str, str] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }

    # Only in production (requires HTTPS)
    PRODUCTION_HEADERS: dict[str, str] = {
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'",
    }

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        for header, value in self.SECURITY_HEADERS.items():
            response.headers[header] = value

        if settings.is_production:
            for header, value in self.PRODUCTION_HEADERS.items():
                response.headers[header] = value

        return response


# ─── Rate Limiting Middleware (Example with in-memory store) ─────────────────


class RateLimitMiddleware:
    """Simple in-memory rate limiter.

    NOTE: For production, use Redis-backed solutions like slowapi or
    a reverse proxy (nginx, Cloudflare) instead of in-memory storage.
    In-memory only works for single-process deployments.

    Usage:
        app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)
    """

    def __init__(
        self,
        app: ASGIApp,
        max_requests: int = 100,
        window_seconds: int = 60,
    ) -> None:
        self.app = app
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        client_ip = request.client.host if request.client else "unknown"

        now = time.time()
        # Clean old entries
        if client_ip in self._requests:
            self._requests[client_ip] = [
                t for t in self._requests[client_ip]
                if now - t < self.window_seconds
            ]
        else:
            self._requests[client_ip] = []

        if len(self._requests[client_ip]) >= self.max_requests:
            response = Response(
                content='{"error":{"code":"RATE_LIMITED","message":"Too many requests"}}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(self.window_seconds)},
            )
            await response(scope, receive, send)
            return

        self._requests[client_ip].append(now)
        await self.app(scope, receive, send)
