"""
Database module for the Brazil Property API.
"""
from .mongodb_handler import MongoDBHandler
from .exceptions import (
    DatabaseConnectionError,
    DatabaseOperationError,
    ValidationError,
    DuplicateEntryError
)


__all__ = [
    'MongoDBHandler',
    'DatabaseConnectionError',
    'DatabaseOperationError',
    'ValidationError',
    'DuplicateEntryError'
]