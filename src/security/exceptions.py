"""
Security-related exceptions for the Brazil Property API.
"""


class SecurityException(Exception):
    """Base exception for security-related errors."""
    pass


class RateLimitExceeded(SecurityException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message="Rate limit exceeded", retry_after=3600):
        super().__init__(message)
        self.retry_after = retry_after


class InvalidAPIKey(SecurityException):
    """Raised when API key is invalid."""
    pass


class SecurityViolation(SecurityException):
    """Raised when a security violation is detected."""
    pass


class InvalidInput(SecurityException):
    """Raised when input validation fails."""
    pass


class AccessDenied(SecurityException):
    """Raised when access is denied."""
    pass


class SuspiciousActivity(SecurityException):
    """Raised when suspicious activity is detected."""
    pass