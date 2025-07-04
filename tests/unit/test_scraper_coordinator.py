"""
Tests for Scraper Coordinator - Phase 4 of TDD Development.
Following TDD approach - write tests first, then implement.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.scrapers import ScraperCoordinator
from src.scrapers.exceptions import ScraperError, ScraperConnectionError
from src.config import DevelopmentConfig
from src.database import MongoDBHandler
from src.cache import SmartCache


@pytest.mark.unit
class TestScraperCoordinator:
    """Test scraper coordinator functionality."""
    
    def test_coordinator_initialization(self):
        """Test scraper coordinator initialization."""
        config = DevelopmentConfig()
        
        with patch('src.scrapers.coordinator.MongoDBHandler'):
            with patch('src.scrapers.coordinator.SmartCache'):
                coordinator = ScraperCoordinator(config)
                
                assert coordinator.config == config
                assert coordinator.enabled_scrapers == ['zap', 'vivareal']
                assert len(coordinator.scrapers) == 2
                assert 'zap' in coordinator.scrapers
                assert 'vivareal' in coordinator.scrapers
    
    def test_coordinator_with_specific_scrapers(self):
        """Test coordinator initialization with specific scrapers."""
        config = DevelopmentConfig()
        enabled_scrapers = ['zap']
        
        with patch('src.scrapers.coordinator.MongoDBHandler'):
            with patch('src.scrapers.coordinator.SmartCache'):
                coordinator = ScraperCoordinator(config, enabled_scrapers=enabled_scrapers)
                
                assert coordinator.enabled_scrapers == ['zap']
                assert len(coordinator.scrapers) == 1
                assert 'zap' in coordinator.scrapers
                assert 'vivareal' not in coordinator.scrapers
    
    @patch('src.scrapers.coordinator.MongoDBHandler')
    @patch('src.scrapers.coordinator.SmartCache')
    def test_scrape_properties_single_scraper(self, mock_cache, mock_db):
        """Test scraping properties with single scraper."""
        config = DevelopmentConfig()
        coordinator = ScraperCoordinator(config, enabled_scrapers=['zap'])
        
        # Mock cache to return None (no cached results)
        mock_cache_instance = mock_cache.return_value
        mock_cache_instance.get_search_results.return_value = None
        
        # Mock scraper response
        mock_properties = [
            {'id': 'zap_1', 'title': 'Apartamento 1', 'price': 500000, 'source': 'ZAP'},
            {'id': 'zap_2', 'title': 'Apartamento 2', 'price': 750000, 'source': 'ZAP'}
        ]
        
        with patch.object(coordinator.scrapers['zap'], 'scrape_properties', return_value=mock_properties):
            search_params = {'city': 'Rio de Janeiro', 'state': 'RJ'}
            results = coordinator.scrape_properties(search_params)
            
            assert len(results) == 2
            assert results[0]['source'] == 'ZAP'
            assert results[1]['source'] == 'ZAP'
    
    @patch('src.scrapers.coordinator.MongoDBHandler')
    @patch('src.scrapers.coordinator.SmartCache')
    def test_scrape_properties_multiple_scrapers(self, mock_cache, mock_db):
        """Test scraping properties with multiple scrapers."""
        config = DevelopmentConfig()
        coordinator = ScraperCoordinator(config)
        
        # Mock cache to return None (no cached results)
        mock_cache_instance = mock_cache.return_value
        mock_cache_instance.get_search_results.return_value = None
        
        # Mock scraper responses
        zap_properties = [
            {'id': 'zap_1', 'title': 'ZAP Apartamento 1', 'price': 500000, 'source': 'ZAP'}
        ]
        vivareal_properties = [
            {'id': 'vivareal_1', 'title': 'VivaReal Apartamento 1', 'price': 600000, 'source': 'VivaReal'}
        ]
        
        with patch.object(coordinator.scrapers['zap'], 'scrape_properties', return_value=zap_properties):
            with patch.object(coordinator.scrapers['vivareal'], 'scrape_properties', return_value=vivareal_properties):
                search_params = {'city': 'Rio de Janeiro', 'state': 'RJ'}
                results = coordinator.scrape_properties(search_params)
                
                assert len(results) == 2
                sources = [prop['source'] for prop in results]
                assert 'ZAP' in sources
                assert 'VivaReal' in sources
    
    @patch('src.scrapers.coordinator.MongoDBHandler')
    @patch('src.scrapers.coordinator.SmartCache')
    def test_scrape_properties_with_error_handling(self, mock_cache, mock_db):
        """Test scraping with error handling."""
        config = DevelopmentConfig()
        coordinator = ScraperCoordinator(config)
        
        # Mock cache to return None (no cached results)
        mock_cache_instance = mock_cache.return_value
        mock_cache_instance.get_search_results.return_value = None
        
        # Mock one scraper failing and one succeeding
        vivareal_properties = [
            {'id': 'vivareal_1', 'title': 'VivaReal Apartamento 1', 'price': 600000, 'source': 'VivaReal'}
        ]
        
        with patch.object(coordinator.scrapers['zap'], 'scrape_properties', side_effect=ScraperConnectionError("ZAP failed")):
            with patch.object(coordinator.scrapers['vivareal'], 'scrape_properties', return_value=vivareal_properties):
                search_params = {'city': 'Rio de Janeiro', 'state': 'RJ'}
                results = coordinator.scrape_properties(search_params)
                
                # Should still return results from successful scraper
                assert len(results) == 1
                assert results[0]['source'] == 'VivaReal'
    
    @patch('src.scrapers.coordinator.MongoDBHandler')
    @patch('src.scrapers.coordinator.SmartCache')
    def test_scrape_and_save_properties(self, mock_cache, mock_db):
        """Test scraping and saving properties to database."""
        config = DevelopmentConfig()
        coordinator = ScraperCoordinator(config, enabled_scrapers=['zap'])
        
        # Mock cache to return None (no cached results)
        mock_cache_instance = mock_cache.return_value
        mock_cache_instance.get_search_results.return_value = None
        
        # Mock scraper response
        mock_properties = [
            {'id': 'zap_1', 'title': 'Apartamento 1', 'price': 500000, 'source': 'ZAP', 'city': 'Rio de Janeiro'}
        ]
        
        # Mock database save
        mock_db_instance = mock_db.return_value
        mock_db_instance.save_properties.return_value = True
        
        with patch.object(coordinator.scrapers['zap'], 'scrape_properties', return_value=mock_properties):
            search_params = {'city': 'Rio de Janeiro', 'state': 'RJ'}
            results = coordinator.scrape_and_save(search_params)
            
            assert results['total_scraped'] == 1
            assert results['total_saved'] == 1
            assert results['sources'] == ['ZAP']
            
            # Verify database save was called
            mock_db_instance.save_properties.assert_called_once()
    
    @patch('src.scrapers.coordinator.MongoDBHandler')
    @patch('src.scrapers.coordinator.SmartCache')
    def test_remove_duplicates(self, mock_cache, mock_db):
        """Test removing duplicate properties from results."""
        config = DevelopmentConfig()
        coordinator = ScraperCoordinator(config)
        
        # Mock properties with duplicates (same ID)
        properties = [
            {'id': 'prop_1', 'title': 'Apartamento 1', 'price': 500000, 'source': 'ZAP'},
            {'id': 'prop_2', 'title': 'Apartamento 2', 'price': 600000, 'source': 'ZAP'},
            {'id': 'prop_1', 'title': 'Apartamento 1', 'price': 500000, 'source': 'VivaReal'},  # Duplicate
            {'id': 'prop_3', 'title': 'Apartamento 3', 'price': 700000, 'source': 'VivaReal'}
        ]
        
        unique_properties = coordinator.remove_duplicates(properties)
        
        assert len(unique_properties) == 3
        property_ids = [prop['id'] for prop in unique_properties]
        assert property_ids.count('prop_1') == 1  # Only one instance of prop_1
        assert 'prop_2' in property_ids
        assert 'prop_3' in property_ids
    
    @patch('src.scrapers.coordinator.MongoDBHandler')
    @patch('src.scrapers.coordinator.SmartCache')
    def test_validate_search_params(self, mock_cache, mock_db):
        """Test search parameters validation."""
        config = DevelopmentConfig()
        coordinator = ScraperCoordinator(config)
        
        # Valid parameters
        valid_params = {
            'city': 'Rio de Janeiro',
            'state': 'RJ',
            'transaction_type': 'venda'
        }
        assert coordinator.validate_search_params(valid_params) is True
        
        # Missing required parameters
        invalid_params = {
            'city': 'Rio de Janeiro'
            # Missing state
        }
        assert coordinator.validate_search_params(invalid_params) is False
        
        # Empty city
        invalid_params2 = {
            'city': '',
            'state': 'RJ'
        }
        assert coordinator.validate_search_params(invalid_params2) is False
    
    @patch('src.scrapers.coordinator.MongoDBHandler')
    @patch('src.scrapers.coordinator.SmartCache')
    def test_get_scraper_stats(self, mock_cache, mock_db):
        """Test getting aggregated scraper statistics."""
        config = DevelopmentConfig()
        coordinator = ScraperCoordinator(config)
        
        # Mock scraper stats
        with patch.object(coordinator.scrapers['zap'], 'get_stats', return_value={
            'requests_made': 5, 'properties_found': 25, 'errors_count': 1
        }):
            with patch.object(coordinator.scrapers['vivareal'], 'get_stats', return_value={
                'requests_made': 3, 'properties_found': 18, 'errors_count': 0
            }):
                stats = coordinator.get_scraper_stats()
                
                assert stats['total_requests'] == 8
                assert stats['total_properties'] == 43
                assert stats['total_errors'] == 1
                assert 'zap' in stats['by_source']
                assert 'vivareal' in stats['by_source']
    
    @patch('src.scrapers.coordinator.MongoDBHandler')
    @patch('src.scrapers.coordinator.SmartCache')
    def test_cache_integration(self, mock_cache, mock_db):
        """Test cache integration."""
        config = DevelopmentConfig()
        coordinator = ScraperCoordinator(config)
        
        # Mock cache operations
        mock_cache_instance = mock_cache.return_value
        mock_cache_instance.get_search_results.return_value = None  # No cached results
        
        # Mock scraper response
        mock_properties = [
            {'id': 'zap_1', 'title': 'Apartamento 1', 'price': 500000, 'source': 'ZAP'}
        ]
        
        with patch.object(coordinator.scrapers['zap'], 'scrape_properties', return_value=mock_properties):
            with patch.object(coordinator.scrapers['vivareal'], 'scrape_properties', return_value=[]):
                search_params = {'city': 'Rio de Janeiro', 'state': 'RJ'}
                results = coordinator.scrape_properties(search_params, use_cache=True)
                
                assert len(results) == 1
                # Verify cache was checked and results were cached
                mock_cache_instance.get_search_results.assert_called()
                mock_cache_instance.cache_search_results.assert_called()
    
    @patch('src.scrapers.coordinator.MongoDBHandler')
    @patch('src.scrapers.coordinator.SmartCache')
    def test_cache_hit(self, mock_cache, mock_db):
        """Test cache hit scenario."""
        config = DevelopmentConfig()
        coordinator = ScraperCoordinator(config)
        
        # Mock cached results
        cached_properties = [
            {'id': 'cached_1', 'title': 'Cached Apartamento', 'price': 400000, 'source': 'Cache'}
        ]
        
        mock_cache_instance = mock_cache.return_value
        mock_cache_instance.get_search_results.return_value = cached_properties
        
        search_params = {'city': 'Rio de Janeiro', 'state': 'RJ'}
        results = coordinator.scrape_properties(search_params, use_cache=True)
        
        assert len(results) == 1
        assert results[0]['source'] == 'Cache'
        
        # Verify cache was called for retrieval
        mock_cache_instance.get_search_results.assert_called()
    
    @patch('src.scrapers.coordinator.MongoDBHandler')
    @patch('src.scrapers.coordinator.SmartCache')
    def test_property_enrichment(self, mock_cache, mock_db):
        """Test property data enrichment."""
        config = DevelopmentConfig()
        coordinator = ScraperCoordinator(config)
        
        # Mock properties with minimal data
        properties = [
            {'id': 'zap_1', 'title': 'Apartamento', 'price': 500000, 'source': 'ZAP', 'city': 'Rio de Janeiro'}
        ]
        
        enriched = coordinator.enrich_properties(properties)
        
        assert len(enriched) == 1
        assert 'scraped_at' in enriched[0]
        assert 'hash' in enriched[0]
        assert enriched[0]['hash'] is not None
    
    @patch('src.scrapers.coordinator.MongoDBHandler')
    @patch('src.scrapers.coordinator.SmartCache')
    def test_parallel_scraping(self, mock_cache, mock_db):
        """Test parallel scraping capability."""
        config = DevelopmentConfig()
        coordinator = ScraperCoordinator(config)
        
        # Mock cache to return None (no cached results)
        mock_cache_instance = mock_cache.return_value
        mock_cache_instance.get_search_results.return_value = None
        
        # Mock scraper responses with delays to simulate real scraping
        zap_properties = [{'id': 'zap_1', 'source': 'ZAP'}]
        vivareal_properties = [{'id': 'vivareal_1', 'source': 'VivaReal'}]
        
        with patch.object(coordinator.scrapers['zap'], 'scrape_properties', return_value=zap_properties):
            with patch.object(coordinator.scrapers['vivareal'], 'scrape_properties', return_value=vivareal_properties):
                search_params = {'city': 'Rio de Janeiro', 'state': 'RJ'}
                results = coordinator.scrape_properties(search_params, parallel=True)
                
                assert len(results) == 2
                sources = [prop['source'] for prop in results]
                assert 'ZAP' in sources
                assert 'VivaReal' in sources
    
    @patch('src.scrapers.coordinator.MongoDBHandler')
    @patch('src.scrapers.coordinator.SmartCache')
    def test_coordinator_close(self, mock_cache, mock_db):
        """Test coordinator cleanup."""
        config = DevelopmentConfig()
        coordinator = ScraperCoordinator(config)
        
        # Mock scraper close methods
        with patch.object(coordinator.scrapers['zap'], 'close') as mock_zap_close:
            with patch.object(coordinator.scrapers['vivareal'], 'close') as mock_vivareal_close:
                coordinator.close()
                
                # Verify all scrapers were closed
                mock_zap_close.assert_called_once()
                mock_vivareal_close.assert_called_once()
    
    @patch('src.scrapers.coordinator.MongoDBHandler')
    @patch('src.scrapers.coordinator.SmartCache')
    def test_filter_properties_by_criteria(self, mock_cache, mock_db):
        """Test filtering properties by criteria."""
        config = DevelopmentConfig()
        coordinator = ScraperCoordinator(config)
        
        properties = [
            {'id': 'prop_1', 'price': 300000, 'bedrooms': 2, 'city': 'Rio de Janeiro'},
            {'id': 'prop_2', 'price': 800000, 'bedrooms': 3, 'city': 'Rio de Janeiro'},
            {'id': 'prop_3', 'price': 600000, 'bedrooms': 2, 'city': 'São Paulo'},
        ]
        
        # Test price filter
        filters = {'price_min': 500000}
        filtered = coordinator.filter_properties(properties, filters)
        assert len(filtered) == 2
        assert all(prop['price'] >= 500000 for prop in filtered)
        
        # Test bedrooms filter
        filters = {'bedrooms': 2}
        filtered = coordinator.filter_properties(properties, filters)
        assert len(filtered) == 2
        assert all(prop['bedrooms'] == 2 for prop in filtered)
        
        # Test city filter
        filters = {'city': 'Rio de Janeiro'}
        filtered = coordinator.filter_properties(properties, filters)
        assert len(filtered) == 2
        assert all(prop['city'] == 'Rio de Janeiro' for prop in filtered)