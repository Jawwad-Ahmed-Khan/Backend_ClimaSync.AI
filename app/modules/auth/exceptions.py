"""Auth-specific domain exceptions.

These map to HTTP codes solely through core/exception_handlers.py.
"""

from app.core.exceptions import (
    AlreadyExistsException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)


class EmailAlreadyRegisteredException(AlreadyExistsException):
    """Raised when a verified user with this email already exists."""

    def __init__(self) -> None:
        super().__init__(resource="Email", identifier="already registered")


class EmailDomainInvalidException(ValidationException):
    """Raised when the email domain is undeliverable or nonexistent."""

    def __init__(self) -> None:
        super().__init__(detail="The provided email domain does not exist or cannot receive mail.")



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


class InvalidCredentialsException(UnauthorizedException):
    """Raised when email/password do not match (generic — avoids user enumeration)."""

    def __init__(self) -> None:
        super().__init__(detail="Invalid email or password")


class AccountDisabledException(ForbiddenException):
    """Raised when the account is inactive / suspended."""

    def __init__(self) -> None:
        super().__init__(detail="Account is disabled. Please contact support.")


class EmailNotVerifiedException(ForbiddenException):
    """Raised when a user attempts to login before verifying their email."""

    def __init__(self) -> None:
        super().__init__(detail="Email address is not verified. Please check your inbox for the OTP.")


class PasswordMismatchException(ValidationException):
    """Raised when the current password does not match during password change."""

    def __init__(self) -> None:
        super().__init__(detail="Current password is incorrect")


class PasswordSameAsOldException(ValidationException):
    """Raised when the new password is the same as the current one."""

    def __init__(self) -> None:
        super().__init__(detail="New password must be different from the current password")


class InvalidRefreshTokenException(UnauthorizedException):
    """Raised when a refresh token is invalid, expired, or revoked."""

    def __init__(self) -> None:
        super().__init__(detail="Invalid or expired refresh token")


class NoProfileFoundException(NotFoundException):
    """Raised when no NGO profile exists for the authenticated user."""

    def __init__(self) -> None:
        super().__init__(resource="NGO profile", identifier="current user")

