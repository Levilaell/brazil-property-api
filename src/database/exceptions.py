"""
Database-related exceptions.
"""


class DatabaseConnectionError(Exception):
    """Raised when database connection fails."""
    pass


class DatabaseOperationError(Exception):
    """Raised when database operation fails."""
    pass


class ValidationError(Exception):
    """Raised when data validation fails."""
    pass


class DuplicateEntryError(Exception):
    """Raised when duplicate entry is detected."""
    pass