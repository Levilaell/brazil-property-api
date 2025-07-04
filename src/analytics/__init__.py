"""
Analytics module for the Brazil Property API.

This module provides:
- Analytics tracking and reporting
- Metrics collection and aggregation
- Health monitoring and checks
- Performance monitoring
"""

from .analytics import Analytics
from .metrics import MetricsCollector
from .health_check import HealthChecker, ComponentHealth
from .exceptions import (
    AnalyticsException,
    AnalyticsError,
    MetricsError,
    HealthCheckError,
    StorageError,
    ConfigurationError
)

__all__ = [
    'Analytics',
    'MetricsCollector',
    'HealthChecker',
    'ComponentHealth',
    'AnalyticsException',
    'AnalyticsError',
    'MetricsError',
    'HealthCheckError',
    'StorageError',
    'ConfigurationError'
]