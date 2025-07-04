"""
Analytics-related exceptions for the Brazil Property API.
"""


class AnalyticsException(Exception):
    """Base exception for analytics-related errors."""
    pass


class AnalyticsError(AnalyticsException):
    """Raised when analytics processing fails."""
    pass


class MetricsError(AnalyticsException):
    """Raised when metrics collection fails."""
    pass


class HealthCheckError(AnalyticsException):
    """Raised when health check fails."""
    pass


class StorageError(AnalyticsException):
    """Raised when analytics storage operations fail."""
    pass


class ConfigurationError(AnalyticsException):
    """Raised when analytics configuration is invalid."""
    pass