"""
Custom exception hierarchy for the Finance Tracker API.

Every error raised in the service layer is a subclass of AppError.
The global handler in main.py catches AppError and converts it to
a consistent JSON response - no HTTP details leak into business logic.
"""
from typing import Optional


class AppError(Exception):
    """Base exception. All custom errors inherit from this."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


class NotFoundError(AppError):
    """Resource does not exist."""

    status_code = 404
    code = "NOT_FOUND"


class BadRequestError(AppError):
    """Request is structurally valid but violates a business rule."""

    status_code = 400
    code = "BAD_REQUEST"


class UnauthorizedError(AppError):
    """Caller is not authenticated."""

    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    """Caller is authenticated but lacks the required role."""

    status_code = 403
    code = "FORBIDDEN"


class ConflictError(AppError):
    """Resource already exists (e.g. duplicate email)."""

    status_code = 409
    code = "CONFLICT"
