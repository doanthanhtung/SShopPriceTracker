class AppError(Exception):
    """Base exception for application-level errors."""


class ExternalServiceError(AppError):
    """Raised when an upstream service cannot be reached or parsed."""

