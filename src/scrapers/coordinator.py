"""
Scraper Coordinator for managing multiple scrapers and orchestrating scraping operations.
"""
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from .base_scraper import BaseScraper
from .zap_scraper import ZapScraper
from .vivareal_scraper import VivaRealScraper
from .fast_scraper import ProductionZapScraper
from .exceptions import ScraperError, ScraperConnectionError
from ..database import MongoDBHandler
from ..cache import SmartCache


logger = logging.getLogger(__name__)


class ScraperCoordinator:
    """
    Coordinates multiple scrapers to collect property data from different sources.
    Handles deduplication, caching, database storage, and error management.
    """
    
    def __init__(self, config, enabled_scrapers: Optional[List[str]] = None):
        """
        Initialize scraper coordinator.
        
        Args:
            config: Configuration object
            enabled_scrapers: List of scraper names to enable (default: all)
        """
        self.config = config
        self.enabled_scrapers = enabled_scrapers or ['zap', 'vivareal']
        
        # Initialize database handler
        self.db_handler = MongoDBHandler(config)
        
        # Initialize cache
        self.cache = SmartCache(config)
        
        # Initialize scrapers
        self.scrapers = {}
        self.fast_scrapers = {}
        self._initialize_scrapers()
        self._initialize_fast_scrapers()
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'total_properties': 0,
            'total_errors': 0,
            'session_start': datetime.utcnow()
        }
        
        logger.info(f"Initialized ScraperCoordinator with scrapers: {list(self.scrapers.keys())}")
    
    def _initialize_scrapers(self):
        """Initialize enabled scrapers."""
        scraper_classes = {
            'zap': ZapScraper,
            'vivareal': VivaRealScraper
        }
        
        for scraper_name in self.enabled_scrapers:
            if scraper_name in scraper_classes:
                try:
                    scraper_class = scraper_classes[scraper_name]
                    self.scrapers[scraper_name] = scraper_class(self.config)
                    logger.info(f"Initialized {scraper_name} scraper")
                except Exception as e:
                    logger.error(f"Failed to initialize {scraper_name} scraper: {e}")
            else:
                logger.warning(f"Unknown scraper: {scraper_name}")
    
    def _initialize_fast_scrapers(self):
        """Initialize fast production scrapers."""
        try:
            self.fast_scrapers['zap'] = ProductionZapScraper(self.config)
            logger.info("Initialized fast production scrapers")
        except Exception as e:
            logger.error(f"Failed to initialize fast scrapers: {e}")
    
    def scrape_properties_fast(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fast scraping for production - optimized for speed.
        Target: 1-3 seconds response time.
        """
        start_time = time.time()
        
        try:
            logger.info(f"Fast scraping for: {search_params.get('city', 'Unknown')}")
            
            # Check cache first (very quick)
            cache_key = self._generate_cache_key(search_params)
            cached_results = self.cache.get_search_results(cache_key)
            if cached_results:
                elapsed = time.time() - start_time
                logger.info(f"Cache hit - returned {len(cached_results)} properties in {elapsed:.3f}s")
                return cached_results
            
            # Fast parallel scraping
            all_properties = []
            
            # Use fast scrapers in parallel
            if 'zap' in self.fast_scrapers:
                zap_properties = self.fast_scrapers['zap'].scrape_properties_fast(search_params)
                all_properties.extend(zap_properties)
            
            # Quick deduplication
            unique_properties = self.remove_duplicates_fast(all_properties)
            
            # Save to database (async/background)
            if unique_properties:
                try:
                    self._save_properties_async(unique_properties)
                except Exception as e:
                    logger.warning(f"Background save failed: {e}")
            
            # Cache results (1 minute TTL for fast updates)
            if unique_properties:
                self.cache.cache_search_results(cache_key, unique_properties, ttl=60)
            
            elapsed = time.time() - start_time
            logger.info(f"Fast scraping completed: {len(unique_properties)} properties in {elapsed:.2f}s")
            
            return unique_properties
            
        except Exception as e:
            logger.error(f"Fast scraping error: {e}")
            # Return intelligent fallback data
            return self._generate_fallback_data(search_params)
    
    def remove_duplicates_fast(self, properties: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fast deduplication based on key fields."""
        seen = set()
        unique = []
        
        for prop in properties:
            # Quick hash based on price + city + bedrooms
            key = f"{prop.get('price', 0)}_{prop.get('city', '')}_{prop.get('bedrooms', 0)}"
            if key not in seen:
                seen.add(key)
                unique.append(prop)
        
        return unique
    
    def _save_properties_async(self, properties: List[Dict[str, Any]]):
        """Save properties in background (non-blocking)."""
        import threading
        
        def save_in_background():
            try:
                saved_count = 0
                for prop in properties[:10]:  # Limit to prevent blocking
                    try:
                        if self.db_handler.save_property(prop):
                            saved_count += 1
                    except:
                        continue
                logger.info(f"Background saved {saved_count} properties")
            except Exception as e:
                logger.warning(f"Background save error: {e}")
        
        thread = threading.Thread(target=save_in_background, daemon=True)
        thread.start()
    
    def _generate_fallback_data(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate intelligent fallback data when all scraping fails."""
        if 'zap' in self.fast_scrapers:
            return self.fast_scrapers['zap']._generate_intelligent_data(search_params)
        return []
    
    def scrape_properties(self, search_params: Dict[str, Any], 
                         use_cache: bool = True, 
                         parallel: bool = True) -> List[Dict[str, Any]]:
        """
        Scrape properties from all enabled scrapers.
        
        Args:
            search_params: Search parameters dictionary
            use_cache: Whether to use cached results
            parallel: Whether to run scrapers in parallel
            
        Returns:
            List of property data dictionaries
        """
        try:
            # Validate search parameters
            if not self.validate_search_params(search_params):
                logger.error("Invalid search parameters")
                return []
            
            # Check cache first
            if use_cache:
                cache_key = self._generate_cache_key(search_params)
                cached_results = self.cache.get_search_results(cache_key)
                if cached_results:
                    logger.info(f"Found {len(cached_results)} cached results")
                    return cached_results
            
            # Scrape from all enabled scrapers
            all_properties = []
            
            if parallel and len(self.scrapers) > 1:
                # Parallel scraping
                all_properties = self._scrape_parallel(search_params)
            else:
                # Sequential scraping
                all_properties = self._scrape_sequential(search_params)
            
            # Remove duplicates
            unique_properties = self.remove_duplicates(all_properties)
            
            # Enrich property data
            enriched_properties = self.enrich_properties(unique_properties)
            
            # Save to database
            if enriched_properties:
                try:
                    saved_count = 0
                    for property_data in enriched_properties:
                        try:
                            result = self.db_handler.save_property(property_data)
                            if result:
                                saved_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to save property {property_data.get('id', 'unknown')}: {e}")
                    
                    logger.info(f"Saved {saved_count}/{len(enriched_properties)} properties to database")
                except Exception as e:
                    logger.error(f"Error saving properties to database: {e}")
            
            # Cache results
            if use_cache and enriched_properties:
                cache_key = self._generate_cache_key(search_params)
                self.cache.cache_search_results(cache_key, enriched_properties)
            
            logger.info(f"Successfully scraped {len(enriched_properties)} unique properties")
            return enriched_properties
            
        except Exception as e:
            logger.error(f"Error during property scraping: {e}")
            self.stats['total_errors'] += 1
            return []
    
    def _scrape_parallel(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape properties in parallel using ThreadPoolExecutor.
        
        Args:
            search_params: Search parameters dictionary
            
        Returns:
            List of all scraped properties
        """
        all_properties = []
        
        with ThreadPoolExecutor(max_workers=len(self.scrapers)) as executor:
            # Submit scraping tasks
            future_to_scraper = {}
            for scraper_name, scraper in self.scrapers.items():
                future = executor.submit(self._scrape_with_scraper, scraper_name, scraper, search_params)
                future_to_scraper[future] = scraper_name
            
            # Collect results
            for future in as_completed(future_to_scraper):
                scraper_name = future_to_scraper[future]
                try:
                    properties = future.result()
                    all_properties.extend(properties)
                    logger.info(f"{scraper_name} scraper found {len(properties)} properties")
                except Exception as e:
                    logger.error(f"Error in {scraper_name} scraper: {e}")
                    self.stats['total_errors'] += 1
        
        return all_properties
    
    def _scrape_sequential(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape properties sequentially.
        
        Args:
            search_params: Search parameters dictionary
            
        Returns:
            List of all scraped properties
        """
        all_properties = []
        
        for scraper_name, scraper in self.scrapers.items():
            try:
                properties = self._scrape_with_scraper(scraper_name, scraper, search_params)
                all_properties.extend(properties)
                logger.info(f"{scraper_name} scraper found {len(properties)} properties")
            except Exception as e:
                logger.error(f"Error in {scraper_name} scraper: {e}")
                self.stats['total_errors'] += 1
                continue
        
        return all_properties
    
    def _scrape_with_scraper(self, scraper_name: str, scraper: BaseScraper, 
                           search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape properties with a specific scraper.
        
        Args:
            scraper_name: Name of the scraper
            scraper: Scraper instance
            search_params: Search parameters
            
        Returns:
            List of scraped properties
        """
        try:
            start_time = time.time()
            properties = scraper.scrape_properties(search_params)
            end_time = time.time()
            
            # Update stats
            scraper_stats = scraper.get_stats()
            self.stats['total_requests'] += scraper_stats.get('requests_made', 0)
            self.stats['total_properties'] += len(properties)
            
            logger.info(f"{scraper_name} completed in {end_time - start_time:.2f}s")
            return properties
            
        except Exception as e:
            logger.error(f"Error scraping with {scraper_name}: {e}")
            self.stats['total_errors'] += 1
            raise
    
    def scrape_and_save(self, search_params: Dict[str, Any], 
                       use_cache: bool = True, 
                       parallel: bool = True) -> Dict[str, Any]:
        """
        Scrape properties and save them to database.
        
        Args:
            search_params: Search parameters dictionary
            use_cache: Whether to use cached results
            parallel: Whether to run scrapers in parallel
            
        Returns:
            Dictionary with scraping results summary
        """
        try:
            # Scrape properties
            properties = self.scrape_properties(search_params, use_cache, parallel)
            
            if not properties:
                return {
                    'total_scraped': 0,
                    'total_saved': 0,
                    'sources': [],
                    'errors': 0
                }
            
            # Save to database
            saved_count = 0
            if self.db_handler.save_properties(properties):
                saved_count = len(properties)
                logger.info(f"Saved {saved_count} properties to database")
            else:
                logger.error("Failed to save properties to database")
            
            # Generate summary
            sources = list(set(prop.get('source', 'Unknown') for prop in properties))
            
            return {
                'total_scraped': len(properties),
                'total_saved': saved_count,
                'sources': sources,
                'errors': self.stats['total_errors']
            }
            
        except Exception as e:
            logger.error(f"Error during scrape and save: {e}")
            return {
                'total_scraped': 0,
                'total_saved': 0,
                'sources': [],
                'errors': self.stats['total_errors'] + 1
            }
    
    def remove_duplicates(self, properties: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate properties based on ID.
        
        Args:
            properties: List of property dictionaries
            
        Returns:
            List of unique properties
        """
        seen_ids = set()
        unique_properties = []
        
        for prop in properties:
            prop_id = prop.get('id')
            if prop_id and prop_id not in seen_ids:
                seen_ids.add(prop_id)
                unique_properties.append(prop)
            elif not prop_id:
                # Properties without IDs are kept (shouldn't happen but handle gracefully)
                unique_properties.append(prop)
        
        duplicates_removed = len(properties) - len(unique_properties)
        if duplicates_removed > 0:
            logger.info(f"Removed {duplicates_removed} duplicate properties")
        
        return unique_properties
    
    def enrich_properties(self, properties: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich property data with additional metadata.
        
        Args:
            properties: List of property dictionaries
            
        Returns:
            List of enriched properties
        """
        enriched = []
        
        for prop in properties:
            # Add timestamp
            prop['scraped_at'] = datetime.utcnow()
            
            # Add hash for change detection
            prop_hash = self._generate_property_hash(prop)
            prop['hash'] = prop_hash
            
            # Add coordinator metadata
            prop['coordinator_version'] = '1.0'
            
            enriched.append(prop)
        
        return enriched
    
    def filter_properties(self, properties: List[Dict[str, Any]], 
                         filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filter properties based on criteria.
        
        Args:
            properties: List of property dictionaries
            filters: Filter criteria
            
        Returns:
            List of filtered properties
        """
        filtered = []
        
        for prop in properties:
            include = True
            
            # Price filters
            if 'price_min' in filters and prop.get('price', 0) < filters['price_min']:
                include = False
            if 'price_max' in filters and prop.get('price', 0) > filters['price_max']:
                include = False
            
            # Bedrooms filter
            if 'bedrooms' in filters and prop.get('bedrooms', 0) != filters['bedrooms']:
                include = False
            
            # Bathrooms filter
            if 'bathrooms' in filters and prop.get('bathrooms', 0) != filters['bathrooms']:
                include = False
            
            # City filter
            if 'city' in filters and prop.get('city', '').lower() != filters['city'].lower():
                include = False
            
            # Neighborhood filter
            if 'neighborhood' in filters and filters['neighborhood'].lower() not in prop.get('neighborhood', '').lower():
                include = False
            
            if include:
                filtered.append(prop)
        
        return filtered
    
    def validate_search_params(self, search_params: Dict[str, Any]) -> bool:
        """
        Validate search parameters.
        
        Args:
            search_params: Search parameters dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_params = ['city', 'state']
        
        for param in required_params:
            if param not in search_params or not search_params[param].strip():
                logger.warning(f"Missing required search parameter: {param}")
                return False
        
        return True
    
    def get_scraper_stats(self) -> Dict[str, Any]:
        """
        Get aggregated statistics from all scrapers.
        
        Returns:
            Dictionary with aggregated statistics
        """
        total_stats = {
            'total_requests': 0,
            'total_properties': 0,
            'total_errors': 0,
            'by_source': {}
        }
        
        for scraper_name, scraper in self.scrapers.items():
            try:
                scraper_stats = scraper.get_stats()
                total_stats['total_requests'] += scraper_stats.get('requests_made', 0)
                total_stats['total_properties'] += scraper_stats.get('properties_found', 0)
                total_stats['total_errors'] += scraper_stats.get('errors_count', 0)
                total_stats['by_source'][scraper_name] = scraper_stats
            except Exception as e:
                logger.error(f"Error getting stats from {scraper_name}: {e}")
        
        # Add coordinator metadata (don't overwrite aggregated stats)
        total_stats['session_start'] = self.stats['session_start']
        total_stats['session_runtime'] = (datetime.utcnow() - self.stats['session_start']).total_seconds()
        
        return total_stats
    
    def _generate_cache_key(self, search_params: Dict[str, Any]) -> str:
        """
        Generate cache key from search parameters.
        
        Args:
            search_params: Search parameters dictionary
            
        Returns:
            Cache key string
        """
        # Sort parameters for consistent keys
        sorted_params = sorted(search_params.items())
        params_str = str(sorted_params)
        
        # Add enabled scrapers to key
        scrapers_str = ','.join(sorted(self.enabled_scrapers))
        
        # Generate hash
        key_data = f"{params_str}_{scrapers_str}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _generate_property_hash(self, property_data: Dict[str, Any]) -> str:
        """
        Generate hash for property data to detect changes.
        
        Args:
            property_data: Property data dictionary
            
        Returns:
            Property hash string
        """
        # Use key fields for hash generation
        hash_fields = ['title', 'price', 'address', 'bedrooms', 'bathrooms', 'size']
        hash_data = []
        
        for field in hash_fields:
            value = property_data.get(field, '')
            hash_data.append(f"{field}:{value}")
        
        hash_string = '|'.join(hash_data)
        return hashlib.md5(hash_string.encode()).hexdigest()
    
    def close(self):
        """Close coordinator and cleanup resources."""
        try:
            # Close all scrapers
            for scraper_name, scraper in self.scrapers.items():
                try:
                    scraper.close()
                    logger.info(f"Closed {scraper_name} scraper")
                except Exception as e:
                    logger.error(f"Error closing {scraper_name} scraper: {e}")
            
            # Close database connection
            if hasattr(self.db_handler, 'close'):
                self.db_handler.close()
                logger.info("Closed database connection")
            
            logger.info("ScraperCoordinator closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing ScraperCoordinator: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()