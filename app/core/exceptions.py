"""Domain exception hierarchy.

All exceptions raised in service layers inherit from these base classes.
Mapping to HTTP status codes happens ONLY in core/exception_handlers.py.
No exception class here references HTTP concepts.
"""


class AppException(Exception):
    """Base exception for all application domain errors."""

    def __init__(self, detail: str = "An unexpected error occurred") -> None:
        self.detail = detail
        super().__init__(self.detail)


class NotFoundException(AppException):
    """Raised when a requested resource does not exist."""

    def __init__(
        self,
        resource: str = "Resource",
        identifier: str = "",
    ) -> None:
        detail = f"{resource} not found"
        if identifier:
            detail = f"{resource} with identifier '{identifier}' not found"
        super().__init__(detail=detail)


class AlreadyExistsException(AppException):
    """Raised when a resource already exists (conflict)."""

    def __init__(
        self,
        resource: str = "Resource",
        identifier: str = "",
    ) -> None:
        detail = f"{resource} already exists"
        if identifier:
            detail = f"{resource} with identifier '{identifier}' already exists"
        super().__init__(detail=detail)


class UnauthorizedException(AppException):
    """Raised when authentication fails or credentials are invalid."""

    def __init__(self, detail: str = "Authentication required") -> None:
        super().__init__(detail=detail)


class ForbiddenException(AppException):
    """Raised when the user lacks permission for the action."""

    def __init__(self, detail: str = "Insufficient permissions") -> None:
        super().__init__(detail=detail)


class ValidationException(AppException):
    """Raised when business validation fails."""

    def __init__(self, detail: str = "Validation error") -> None:
        super().__init__(detail=detail)


class BadRequestException(AppException):
    """Raised when a client request is malformed or violates business rules."""

    def __init__(self, detail: str = "Bad request") -> None:
        super().__init__(detail=detail)
