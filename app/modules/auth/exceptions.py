"""Auth-specific domain exceptions.

These map to HTTP codes solely through core/exception_handlers.py.
"""

from app.core.exceptions import (
    AlreadyExistsException,
    ForbiddenException,
    UnauthorizedException,
    ValidationException,
)


class EmailAlreadyRegisteredException(AlreadyExistsException):
    """Raised when a verified user with this email already exists."""

    def __init__(self) -> None:
        super().__init__(resource="Email", identifier="already registered")


class OtpExpiredException(ValidationException):
    """Raised when the OTP has passed its expiry time."""

    def __init__(self) -> None:
        super().__init__(detail="OTP has expired. Please request a new one.")


class OtpInvalidException(UnauthorizedException):
    """Raised when the submitted OTP does not match."""

    def __init__(self) -> None:
        super().__init__(detail="Invalid OTP code")


class OtpMaxAttemptsException(ForbiddenException):
    """Raised when the maximum number of OTP attempts is reached."""

    def __init__(self) -> None:
        super().__init__(detail="Too many failed attempts. Request a new OTP.")


class OtpRateLimitException(ForbiddenException):
    """Raised when too many OTPs have been requested recently."""

    def __init__(self) -> None:
        super().__init__(detail="OTP rate limit exceeded. Try again later.")


class NoPendingVerificationException(ValidationException):
    """Raised when no open verification token exists for this email."""

    def __init__(self) -> None:
        super().__init__(detail="No pending verification found for this email")


class EmailAlreadyVerifiedException(ValidationException):
    """Raised when trying to resend OTP for an already-verified email."""

    def __init__(self) -> None:
        super().__init__(detail="Email is already verified")
