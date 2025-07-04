"""
Scrapers module for the Brazil Property API.
"""
from .base_scraper import BaseScraper
from .zap_scraper import ZapScraper
from .vivareal_scraper import VivaRealScraper
from .coordinator import ScraperCoordinator
from .exceptions import (
    ScraperError,
    ScraperConnectionError,
    ScraperParsingError,
    ScraperRateLimitError,
    ScraperBlockedError,
    ScraperTimeoutError,
    ScraperDataError
)


__all__ = [
    'BaseScraper',
    'ZapScraper',
    'VivaRealScraper',
    'ScraperCoordinator',
    'ScraperError',
    'ScraperConnectionError',
    'ScraperParsingError',
    'ScraperRateLimitError',
    'ScraperBlockedError',
    'ScraperTimeoutError',
    'ScraperDataError'
]