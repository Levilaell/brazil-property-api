"""
Advanced scraper with anti-detection capabilities for bypassing website protections.
"""
import time
import random
import logging
from typing import Dict, List, Any, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import undetected_chromedriver as uc
from fake_useragent import UserAgent
import cloudscraper
import requests_html
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from .exceptions import ScraperBlockedError, ScraperConnectionError

logger = logging.getLogger(__name__)


class AdvancedScraper(BaseScraper):
    """
    Advanced scraper with multiple bypass techniques:
    - Undetected Chrome with stealth mode
    - CloudScraper for Cloudflare bypass
    - Rotating user agents
    - JavaScript rendering
    - Human-like behavior simulation
    """
    
    def __init__(self, config):
        """Initialize advanced scraper."""
        super().__init__(config)
        self.name = "AdvancedScraper"
        
        # Initialize user agent generator
        self.ua = UserAgent()
        
        # Initialize CloudScraper session
        self.cloud_scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        
        # Browser instance (lazy initialized)
        self.driver = None
        self.requests_session = None
        
        # Success rates for method selection
        self.method_success_rates = {
            'cloudscraper': 0.8,
            'selenium': 0.9,
            'requests_html': 0.6,
            'basic_requests': 0.3
        }
        
        logger.info("Initialized Advanced Scraper with anti-detection capabilities")
    
    def _init_selenium_driver(self) -> webdriver.Chrome:
        """Initialize undetected Chrome driver."""
        try:
            options = uc.ChromeOptions()
            
            # Stealth options
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-images')  # Faster loading
            options.add_argument('--disable-javascript')  # Only when not needed
            options.add_argument('--window-size=1920,1080')
            
            # Randomize user agent
            options.add_argument(f'--user-agent={self.ua.random}')
            
            # Prefs for better stealth
            prefs = {
                "profile.default_content_setting_values": {
                    "notifications": 2,
                    "media_stream": 2,
                },
                "profile.managed_default_content_settings": {
                    "images": 2  # Block images for faster loading
                }
            }
            options.add_experimental_option("prefs", prefs)
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Initialize driver
            driver = uc.Chrome(options=options, version_main=None)
            
            # Execute stealth scripts
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": self.ua.random
            })
            
            return driver
            
        except Exception as e:
            logger.error(f"Failed to initialize Selenium driver: {e}")
            return None
    
    def _init_requests_html_session(self):
        """Initialize requests-html session."""
        try:
            from requests_html import HTMLSession
            session = HTMLSession()
            session.headers.update({
                'User-Agent': self.ua.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            })
            return session
        except Exception as e:
            logger.error(f"Failed to initialize requests-html session: {e}")
            return None
    
    def _scrape_with_cloudscraper(self, url: str) -> Optional[BeautifulSoup]:
        """Scrape using CloudScraper (Cloudflare bypass)."""
        try:
            logger.info(f"Attempting CloudScraper for: {url}")
            
            # Add random delay
            time.sleep(random.uniform(1, 3))
            
            response = self.cloud_scraper.get(url, timeout=30)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                logger.info("CloudScraper successful")
                return soup
            else:
                logger.warning(f"CloudScraper returned status {response.status_code}")
                return None
                
        except Exception as e:
            logger.warning(f"CloudScraper failed: {e}")
            return None
    
    def _scrape_with_selenium(self, url: str) -> Optional[BeautifulSoup]:
        """Scrape using Selenium with stealth mode."""
        try:
            logger.info(f"Attempting Selenium for: {url}")
            
            if not self.driver:
                self.driver = self._init_selenium_driver()
                if not self.driver:
                    return None
            
            # Navigate to page
            self.driver.get(url)
            
            # Wait for page load and simulate human behavior
            time.sleep(random.uniform(2, 5))
            
            # Random scrolling to simulate human behavior
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
            time.sleep(random.uniform(1, 2))
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(random.uniform(1, 2))
            
            # Wait for content to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                logger.warning("Selenium timeout waiting for page load")
            
            # Get page source
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            logger.info("Selenium scraping successful")
            return soup
            
        except Exception as e:
            logger.warning(f"Selenium scraping failed: {e}")
            return None
    
    def _scrape_with_requests_html(self, url: str) -> Optional[BeautifulSoup]:
        """Scrape using requests-html with JavaScript rendering."""
        try:
            logger.info(f"Attempting requests-html for: {url}")
            
            if not self.requests_session:
                self.requests_session = self._init_requests_html_session()
                if not self.requests_session:
                    return None
            
            # Add random delay
            time.sleep(random.uniform(1, 3))
            
            response = self.requests_session.get(url, timeout=30)
            
            # Render JavaScript
            response.html.render(timeout=20, wait=2)
            
            soup = BeautifulSoup(response.html.html, 'html.parser')
            logger.info("Requests-html scraping successful")
            return soup
            
        except Exception as e:
            logger.warning(f"Requests-html scraping failed: {e}")
            return None
    
    def scrape_with_bypass(self, url: str, max_attempts: int = 3) -> Optional[BeautifulSoup]:
        """
        Scrape URL using multiple bypass techniques in order of success rate.
        
        Args:
            url: URL to scrape
            max_attempts: Maximum attempts per method
            
        Returns:
            BeautifulSoup object or None if all methods fail
        """
        methods = [
            ('selenium', self._scrape_with_selenium),
            ('cloudscraper', self._scrape_with_cloudscraper),
            ('requests_html', self._scrape_with_requests_html),
        ]
        
        # Sort by success rate
        methods.sort(key=lambda x: self.method_success_rates.get(x[0], 0), reverse=True)
        
        for method_name, method_func in methods:
            logger.info(f"Trying {method_name} for {url}")
            
            for attempt in range(max_attempts):
                try:
                    result = method_func(url)
                    if result:
                        # Update success rate
                        self.method_success_rates[method_name] = min(
                            self.method_success_rates[method_name] + 0.1, 1.0
                        )
                        logger.info(f"Successfully scraped with {method_name}")
                        return result
                        
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} with {method_name} failed: {e}")
                    
                # Wait between attempts
                if attempt < max_attempts - 1:
                    wait_time = random.uniform(2, 5) * (attempt + 1)
                    logger.info(f"Waiting {wait_time:.1f}s before retry")
                    time.sleep(wait_time)
            
            # Reduce success rate on failure
            self.method_success_rates[method_name] = max(
                self.method_success_rates[method_name] - 0.1, 0.1
            )
        
        logger.error(f"All scraping methods failed for {url}")
        return None
    
    def close(self):
        """Clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                
            if self.requests_session:
                self.requests_session.close()
                self.requests_session = None
                
            if self.cloud_scraper:
                self.cloud_scraper.close()
                
        except Exception as e:
            logger.error(f"Error closing advanced scraper: {e}")
        
        super().close()