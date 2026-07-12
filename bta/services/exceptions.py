class ServiceError(Exception):
    """Base service-layer error."""


class AnalyzeServiceError(ServiceError):
    """Raised when issue analysis fails."""


class ScanServiceError(ServiceError):
    """Raised when repository scanning fails."""


class DedupeServiceError(ServiceError):
    """Raised when duplicate detection fails."""


class FixServiceError(ServiceError):
    """Raised when patch generation or verification fails."""


class PublishServiceError(ServiceError):
    """Raised when draft PR publication fails."""


class StatusServiceError(ServiceError):
    """Raised when readiness checks fail unexpectedly."""


class EvalServiceError(ServiceError):
    """Raised when evaluation service execution fails."""
