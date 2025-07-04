"""
Base scraper class for web scraping functionality.
"""
import time
import random
import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .exceptions import (
    ScraperConnectionError, ScraperParsingError, ScraperRateLimitError,
    ScraperBlockedError, ScraperTimeoutError, ScraperDataError
)


logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Base scraper class providing common functionality for web scraping.
    All specific scrapers should inherit from this class.
    """
    
    def __init__(self, config):
        """
        Initialize base scraper.
        
        Args:
            config: Configuration object with scraper settings
        """
        self.config = config
        self.name = self.__class__.__name__
        self.base_url = ""
        self.delay_range = (2, 5)  # Increased delay to be more respectful
        self.max_retries = 5  # More retries for better success rate
        self.timeout = 45  # Increased timeout
        
        # Initialize session
        self.session = self._create_session()
        
        # Statistics tracking
        self.stats = {
            'requests_made': 0,
            'properties_found': 0,
            'errors_count': 0,
            'start_time': datetime.utcnow()
        }
        
        logger.info(f"Initialized {self.name} scraper")
    
    def _create_session(self) -> requests.Session:
        """
        Create and configure HTTP session.
        
        Returns:
            Configured requests session
        """
        session = requests.Session()
        
        # Random user agents to avoid detection
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        
        # Set headers to mimic a real browser
        session.headers.update({
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Cache-Control': 'max-age=0',
            'DNT': '1'
        })
        
        return session
    
    def _apply_rate_limit(self):
        """Apply rate limiting delay."""
        delay = random.uniform(*self.delay_range)
        logger.debug(f"Applying rate limit delay: {delay:.2f}s")
        time.sleep(delay)
    
    def _retry_request(self, request_func, *args, **kwargs):
        """
        Retry request with exponential backoff.
        
        Args:
            request_func: Function to retry
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of successful request
            
        Raises:
            ScraperConnectionError: If all retries fail
            ScraperTimeoutError: If all retries failed due to timeout
        """
        last_exception = None
        timeout_count = 0
        
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    # Exponential backoff
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Retrying request (attempt {attempt + 1}/{self.max_retries}) after {delay:.2f}s")
                    time.sleep(delay)
                
                return request_func(*args, **kwargs)
                
            except requests.Timeout as e:
                last_exception = e
                timeout_count += 1
                self.update_stats('errors_count')
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries - 1:
                    self._apply_rate_limit()
                    
            except requests.ConnectionError as e:
                last_exception = e
                self.update_stats('errors_count')
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries - 1:
                    self._apply_rate_limit()
        
        # Raise specific exception based on failure type
        if timeout_count == self.max_retries:
            raise ScraperTimeoutError(f"Request timed out after {self.max_retries} attempts: {last_exception}")
        else:
            raise ScraperConnectionError(f"Failed after {self.max_retries} attempts: {last_exception}")
    
    def make_request(self, url: str, **kwargs) -> requests.Response:
        """
        Make HTTP request with error handling and retries.
        
        Args:
            url: URL to request
            **kwargs: Additional arguments for requests
            
        Returns:
            HTTP response object
            
        Raises:
            ScraperTimeoutError: If request times out
            ScraperConnectionError: If connection fails
            ScraperRateLimitError: If rate limited
            ScraperBlockedError: If blocked by website
        """
        try:
            def _make_request():
                self.update_stats('requests_made')
                
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    **kwargs
                )
                
                # Check for rate limiting or blocking
                if response.status_code == 429:
                    raise ScraperRateLimitError(f"Rate limited by {urlparse(url).netloc}")
                elif response.status_code == 403:
                    raise ScraperBlockedError(f"Blocked by {urlparse(url).netloc}")
                elif response.status_code >= 400:
                    response.raise_for_status()
                
                return response
            
            self._apply_rate_limit()
            return self._retry_request(_make_request)
            
        except ScraperTimeoutError:
            self.update_stats('errors_count')
            raise
        except ScraperRateLimitError:
            self.update_stats('errors_count')
            raise
        except ScraperBlockedError:
            self.update_stats('errors_count')
            raise
        except ScraperConnectionError:
            self.update_stats('errors_count')
            raise
        except Exception as e:
            self.update_stats('errors_count')
            logger.error(f"Unexpected error for {url}: {e}")
            raise ScraperConnectionError(f"Unexpected error: {e}")
    
    def parse_html(self, html_content: str) -> BeautifulSoup:
        """
        Parse HTML content using BeautifulSoup.
        
        Args:
            html_content: HTML content to parse
            
        Returns:
            BeautifulSoup object
            
        Raises:
            ScraperParsingError: If parsing fails
        """
        try:
            if html_content is None:
                raise ScraperParsingError("HTML content is None")
            
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup
            
        except Exception as e:
            raise ScraperParsingError(f"Failed to parse HTML: {e}")
    
    def validate_property_data(self, property_data: Dict[str, Any]) -> bool:
        """
        Validate scraped property data.
        
        Args:
            property_data: Property data dictionary
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check required fields
            required_fields = ['id', 'title', 'price', 'city']
            for field in required_fields:
                if field not in property_data or not property_data[field]:
                    logger.warning(f"Property missing required field: {field}")
                    return False
            
            # Validate price is numeric
            price = property_data.get('price')
            if not isinstance(price, (int, float)):
                try:
                    float(price)
                except (ValueError, TypeError):
                    logger.warning(f"Property price is not numeric: {price}")
                    return False
            
            # Check price is positive
            if float(price) <= 0:
                logger.warning(f"Property price must be positive: {price}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating property data: {e}")
            return False
    
    def clean_text(self, text: str) -> str:
        """
        Clean text by removing extra whitespace.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        return ' '.join(text.strip().split())
    
    def extract_number(self, text: str) -> Optional[Union[int, float]]:
        """
        Extract number from text string.
        
        Args:
            text: Text containing number
            
        Returns:
            Extracted number or None if not found
        """
        if not text:
            return None
        
        try:
            # Remove common currency symbols and units
            cleaned = re.sub(r'[R$\s.,m²]', '', str(text))
            
            # Extract digits
            numbers = re.findall(r'\d+', cleaned)
            if numbers:
                # Join all digits and convert to int
                number_str = ''.join(numbers)
                return int(number_str)
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to extract number from '{text}': {e}")
            return None
    
    def update_stats(self, stat_name: str, increment: int = 1):
        """
        Update scraper statistics.
        
        Args:
            stat_name: Name of the statistic to update
            increment: Amount to increment by
        """
        if stat_name in self.stats:
            self.stats[stat_name] += increment
        else:
            self.stats[stat_name] = increment
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get scraper statistics.
        
        Returns:
            Dictionary with statistics
        """
        current_time = datetime.utcnow()
        total_runtime = (current_time - self.stats['start_time']).total_seconds()
        
        stats = self.stats.copy()
        stats['total_runtime'] = total_runtime
        stats['current_time'] = current_time
        
        return stats
    
    def reset_stats(self):
        """Reset scraper statistics."""
        self.stats = {
            'requests_made': 0,
            'properties_found': 0,
            'errors_count': 0,
            'start_time': datetime.utcnow()
        }
    
    def close(self):
        """Close scraper and cleanup resources."""
        if hasattr(self, 'session') and self.session:
            self.session.close()
        logger.info(f"Closed {self.name} scraper")
    
    # Abstract methods that must be implemented by subclasses
    @abstractmethod
    def extract_property_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract property data from parsed HTML.
        
        Args:
            soup: BeautifulSoup object with property page HTML
            
        Returns:
            Dictionary with property data
        """
        raise NotImplementedError("Subclasses must implement extract_property_data")
    
    @abstractmethod
    def build_search_url(self, search_params: Dict[str, Any]) -> str:
        """
        Build search URL from parameters.
        
        Args:
            search_params: Search parameters dictionary
            
        Returns:
            Complete search URL
        """
        raise NotImplementedError("Subclasses must implement build_search_url")
    
    @abstractmethod
    def scrape_properties(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape properties based on search parameters.
        
        Args:
            search_params: Search parameters dictionary
            
        Returns:
            List of property data dictionaries
        """
        raise NotImplementedError("Subclasses must implement scrape_properties")
    
    @abstractmethod
    def get_total_pages(self, search_params: Dict[str, Any]) -> int:
        """
        Get total number of pages for search results.
        
        Args:
            search_params: Search parameters dictionary
            
        Returns:
            Total number of pages
        """
        raise NotImplementedError("Subclasses must implement get_total_pages")