"""
Tests for SmartCache - Specialized cache wrapper for property data.
Following TDD approach - write tests first, then implement.
"""
import pytest
from unittest.mock import Mock, patch
from src.cache import SmartCache
from src.config import DevelopmentConfig


@pytest.mark.unit
class TestSmartCache:
    """Test SmartCache wrapper functionality."""
    
    def test_smart_cache_initialization(self):
        """Test SmartCache initializes properly."""
        config = DevelopmentConfig()
        smart_cache = SmartCache(config)
        
        assert smart_cache.config == config
        assert smart_cache.cache_manager is not None
        assert smart_cache.cache_warmed is False
        assert smart_cache.cache_prefixes is not None
    
    def test_search_results_caching(self):
        """Test caching of search results."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            mock_redis.get.return_value = None
            
            smart_cache = SmartCache(config)
            
            search_filters = {
                "city": "Rio de Janeiro",
                "min_price": 500000,
                "max_price": 1000000,
                "bedrooms": 2
            }
            
            search_results = {
                "properties": [{"id": "prop_1", "title": "Test Property"}],
                "total": 1,
                "page": 1
            }
            
            # Cache search results
            result = smart_cache.cache_search_results(search_filters, search_results, ttl=600)
            assert result is True
            
            # Retrieve search results
            cached_results = smart_cache.get_search_results(search_filters)
            assert cached_results is None  # Since mock returns None
    
    def test_property_details_caching(self):
        """Test caching of individual property details."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            mock_redis.get.return_value = b'{"id": "prop_123", "title": "Cached Property"}'
            
            smart_cache = SmartCache(config)
            
            property_data = {
                "id": "prop_123",
                "title": "Test Property",
                "price": 800000,
                "city": "Rio de Janeiro"
            }
            
            # Cache property details
            result = smart_cache.cache_property_details("prop_123", property_data)
            assert result is True
            
            # Retrieve property details
            cached_property = smart_cache.get_property_details("prop_123")
            assert cached_property is not None
    
    def test_price_history_caching(self):
        """Test caching of price history data."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            
            smart_cache = SmartCache(config)
            
            price_history = [
                {"date": "2024-01-01", "avg_price": 750000},
                {"date": "2024-02-01", "avg_price": 780000}
            ]
            
            # Cache price history
            result = smart_cache.cache_price_history("Rio de Janeiro", "Copacabana", price_history)
            assert result is True
    
    def test_market_analysis_caching(self):
        """Test caching of market analysis data."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            
            smart_cache = SmartCache(config)
            
            market_analysis = {
                "city": "Rio de Janeiro",
                "avg_price": 825000,
                "price_growth": 4.2,
                "hottest_neighborhoods": ["Leblon", "Ipanema"]
            }
            
            # Cache market analysis
            result = smart_cache.cache_market_analysis("Rio de Janeiro", market_analysis)
            assert result is True
    
    def test_cache_invalidation(self):
        """Test cache invalidation functionality."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.delete.return_value = 1
            
            smart_cache = SmartCache(config)
            
            # Test invalidating search results
            result = smart_cache.invalidate_search_cache("Rio de Janeiro")
            assert result is True
            
            # Test invalidating property cache
            result = smart_cache.invalidate_property_cache("prop_123")
            assert result is True
            
            # Test invalidating all cache
            result = smart_cache.invalidate_all_cache()
            assert result is True
    
    def test_cache_warmup(self):
        """Test cache warmup functionality."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            
            smart_cache = SmartCache(config)
            
            # Mock popular searches data
            popular_searches = [
                {"city": "Rio de Janeiro", "neighborhood": "Copacabana"},
                {"city": "São Paulo", "neighborhood": "Vila Madalena"}
            ]
            
            # Test cache warmup
            result = smart_cache.warmup_cache(popular_searches)
            assert result is True
            assert smart_cache.cache_warmed is True
    
    def test_cache_health_check(self):
        """Test cache health check functionality."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            
            smart_cache = SmartCache(config)
            
            health = smart_cache.health_check()
            
            assert 'cache_manager' in health
            assert 'specialized_stats' in health
            assert 'cache_warmed' in health
            assert health['cache_warmed'] is False
    
    def test_cache_key_patterns(self):
        """Test different cache key patterns are generated correctly."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            
            smart_cache = SmartCache(config)
            
            # Test search key generation
            search_key = smart_cache._generate_search_key({"city": "Rio", "price": 500000})
            assert "search:" in search_key
            
            # Test property key generation
            property_key = smart_cache._generate_property_key("prop_123")
            assert "property:" in property_key
            
            # Test price history key generation
            price_key = smart_cache._generate_price_history_key("Rio", "Copacabana")
            assert "price_history:" in price_key
            
            # Test market analysis key generation
            market_key = smart_cache._generate_market_analysis_key("Rio")
            assert "market_analysis:" in market_key
    
    def test_ttl_configuration(self):
        """Test different TTL configurations for different data types."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            
            smart_cache = SmartCache(config)
            
            # Test different TTL values
            assert smart_cache.search_ttl > 0
            assert smart_cache.property_ttl > 0
            assert smart_cache.price_history_ttl > 0
            assert smart_cache.market_analysis_ttl > 0
            
            # Verify TTLs are appropriate for data types
            assert smart_cache.search_ttl <= smart_cache.property_ttl
            assert smart_cache.price_history_ttl >= smart_cache.search_ttl


@pytest.mark.unit
class TestSmartCacheAdvanced:
    """Test advanced SmartCache functionality."""
    
    def test_batch_cache_operations(self):
        """Test batch caching of multiple items."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            
            smart_cache = SmartCache(config)
            
            properties = [
                {"id": "prop_1", "title": "Property 1"},
                {"id": "prop_2", "title": "Property 2"},
                {"id": "prop_3", "title": "Property 3"}
            ]
            
            # Batch cache properties
            result = smart_cache.batch_cache_properties(properties)
            assert result is True
            
            # Verify all properties were cached
            assert mock_redis.setex.call_count == 3
    
    def test_cache_statistics(self):
        """Test cache statistics tracking."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            
            smart_cache = SmartCache(config)
            
            # Get cache statistics
            stats = smart_cache.get_cache_statistics()
            
            assert 'specialized_stats' in stats
            assert 'total_keys' in stats['specialized_stats']
            assert 'search_cache_keys' in stats['specialized_stats']
            assert 'property_cache_keys' in stats['specialized_stats']
            assert 'price_history_keys' in stats['specialized_stats']
            assert 'market_analysis_keys' in stats['specialized_stats']
    
    def test_cache_namespace_management(self):
        """Test cache namespace management."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            
            smart_cache1 = SmartCache(config, namespace="production")
            smart_cache2 = SmartCache(config, namespace="staging")
            
            # Keys should be different between namespaces
            key1 = smart_cache1._generate_property_key("prop_123")
            key2 = smart_cache2._generate_property_key("prop_123")
            
            assert key1 != key2
            assert "production" in key1
            assert "staging" in key2
    
    def test_cache_expiry_policies(self):
        """Test different cache expiry policies."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            
            smart_cache = SmartCache(config)
            
            # Test custom TTL override
            search_filters = {"city": "Rio"}
            search_results = {"properties": []}
            
            result = smart_cache.cache_search_results(
                search_filters, 
                search_results, 
                ttl=1800  # Custom 30-minute TTL
            )
            assert result is True
    
    def test_cache_compression(self):
        """Test cache data compression for large datasets."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            
            smart_cache = SmartCache(config, enable_compression=True)
            
            # Large dataset that should be compressed
            large_property_list = [
                {"id": f"prop_{i}", "title": f"Property {i}", "description": "A" * 1000}
                for i in range(100)
            ]
            
            search_filters = {"city": "Rio"}
            search_results = {"properties": large_property_list}
            
            result = smart_cache.cache_search_results(search_filters, search_results)
            assert result is True