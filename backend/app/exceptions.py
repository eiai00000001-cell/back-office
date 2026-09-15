"""Domain-level exceptions, mapped to HTTP responses in app.main."""


class DomainError(Exception):
    """Base class for all domain/service-layer errors."""


class ValidationFailedError(DomainError):
    """Maps to HTTP 400. Raised for business validation failures (8章参照)."""


class NotFoundError(DomainError):
    """Maps to HTTP 404."""


class ConflictError(DomainError):
    """Maps to HTTP 409."""
