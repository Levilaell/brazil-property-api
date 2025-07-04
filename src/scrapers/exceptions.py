"""
Scraper-related exceptions.
"""


class ScraperError(Exception):
    """Base exception for scraper errors."""
    pass


class ScraperConnectionError(ScraperError):
    """Raised when scraper connection fails."""
    pass


class ScraperParsingError(ScraperError):
    """Raised when parsing fails."""
    pass


class ScraperRateLimitError(ScraperError):
    """Raised when rate limit is exceeded."""
    pass


class ScraperBlockedError(ScraperError):
    """Raised when scraper is blocked by website."""
    pass


class ScraperTimeoutError(ScraperError):
    """Raised when request times out."""
    pass


class ScraperDataError(ScraperError):
    """Raised when data validation fails."""
    pass