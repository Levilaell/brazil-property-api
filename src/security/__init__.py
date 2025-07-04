"""
Security module for the Brazil Property API.

This module provides:
- Rate limiting functionality
- API key authentication
- Input validation and sanitization
- Security middleware
- Exception handling for security violations
"""

from .rate_limiting import RateLimiter, APIKeyManager, get_client_ip, extract_api_key
from .input_validation import InputValidator, SecurityValidator
from .middleware import SecurityMiddleware, require_api_key, rate_limit
from .exceptions import (
    SecurityException,
    RateLimitExceeded,
    InvalidAPIKey,
    SecurityViolation,
    InvalidInput,
    AccessDenied,
    SuspiciousActivity
)

__all__ = [
    'RateLimiter',
    'APIKeyManager',
    'InputValidator',
    'SecurityValidator',
    'SecurityMiddleware',
    'get_client_ip',
    'extract_api_key',
    'require_api_key',
    'rate_limit',
    'SecurityException',
    'RateLimitExceeded',
    'InvalidAPIKey',
    'SecurityViolation',
    'InvalidInput',
    'AccessDenied',
    'SuspiciousActivity'
]