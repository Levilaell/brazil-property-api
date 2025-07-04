"""
Tests for Cache Manager - Phase 2 of TDD Development.
Following TDD approach - write tests first, then implement.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from src.cache import CacheManager, CacheConnectionError, CacheOperationError
from src.config import DevelopmentConfig


@pytest.mark.unit
class TestCacheManager:
    """Test core cache manager functionality."""
    
    def test_cache_initialization(self):
        """Test cache manager initializes with default settings."""
        config = DevelopmentConfig()
        cache_manager = CacheManager(config)
        
        assert cache_manager.config == config
        assert cache_manager.redis_client is not None
        assert cache_manager.memory_cache is not None
        assert cache_manager.stats['hits'] == 0
        assert cache_manager.stats['misses'] == 0
        assert cache_manager.stats['errors'] == 0
    
    def test_redis_connection_success(self):
        """Test successful Redis connection."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            
            cache_manager = CacheManager(config)
            assert cache_manager.redis_connected is True
            assert cache_manager.redis_client == mock_redis
    
    def test_redis_connection_failure_fallback(self):
        """Test Redis connection failure falls back to memory cache."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis_class.side_effect = Exception("Redis connection failed")
            
            cache_manager = CacheManager(config)
            assert cache_manager.redis_connected is False
            assert cache_manager.memory_cache is not None
    
    def test_set_and_get_value(self):
        """Test setting and getting cache values."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            mock_redis.get.return_value = b'"test_value"'
            
            cache_manager = CacheManager(config)
            
            # Test successful set and get
            cache_manager.set('test_key', 'test_value', ttl=300)
            result = cache_manager.get('test_key')
            
            assert result == 'test_value'
            assert cache_manager.stats['hits'] == 1
    
    def test_cache_expiration(self):
        """Test that cache entries expire after TTL."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.get.return_value = None
            
            cache_manager = CacheManager(config)
            
            result = cache_manager.get('expired_key')
            assert result is None
            assert cache_manager.stats['misses'] == 1
    
    def test_cache_miss_returns_none(self):
        """Test cache miss returns None."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.get.return_value = None
            
            cache_manager = CacheManager(config)
            
            result = cache_manager.get('nonexistent_key')
            assert result is None
            assert cache_manager.stats['misses'] == 1
    
    def test_memory_cache_fallback(self):
        """Test memory cache is used when Redis fails."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis_class.side_effect = Exception("Redis down")
            
            cache_manager = CacheManager(config)
            
            # Should use memory cache
            cache_manager.set('memory_key', 'memory_value')
            result = cache_manager.get('memory_key')
            
            assert result == 'memory_value'
            assert cache_manager.redis_connected is False
    
    def test_cache_key_generation(self):
        """Test cache key generation for different data types."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            
            cache_manager = CacheManager(config)
            
            # Test different key types
            string_key = cache_manager._generate_key("simple_string")
            dict_key = cache_manager._generate_key({"city": "Rio", "price": 500000})
            list_key = cache_manager._generate_key(["item1", "item2"])
            
            assert isinstance(string_key, str)
            assert isinstance(dict_key, str)
            assert isinstance(list_key, str)
            assert string_key != dict_key != list_key
    
    def test_cache_stats_tracking(self):
        """Test cache statistics are properly tracked."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            
            cache_manager = CacheManager(config)
            
            # Test hits
            mock_redis.get.return_value = b'"cached_value"'
            cache_manager.get('hit_key')
            assert cache_manager.stats['hits'] == 1
            
            # Test misses
            mock_redis.get.return_value = None
            cache_manager.get('miss_key')
            assert cache_manager.stats['misses'] == 1
            
            # Test operations
            cache_manager.set('new_key', 'new_value')
            assert cache_manager.stats['operations'] >= 1
    
    def test_cache_cleanup(self):
        """Test cache cleanup functionality."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            
            cache_manager = CacheManager(config)
            
            # Test cleanup
            result = cache_manager.cleanup()
            assert result is True
            
            # Should clear memory cache
            assert len(cache_manager.memory_cache) == 0
    
    def test_cache_delete(self):
        """Test cache deletion functionality."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.delete.return_value = 1
            
            cache_manager = CacheManager(config)
            
            # Test delete
            result = cache_manager.delete('test_key')
            assert result is True
    
    def test_cache_exists(self):
        """Test cache key existence check."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            
            cache_manager = CacheManager(config)
            
            # Test exists
            mock_redis.exists.return_value = 1
            result = cache_manager.exists('test_key')
            assert result is True
            
            mock_redis.exists.return_value = 0
            result = cache_manager.exists('nonexistent_key')
            assert result is False
    
    def test_cache_health_check(self):
        """Test cache health check functionality."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            
            cache_manager = CacheManager(config)
            
            # Test healthy cache
            health = cache_manager.health_check()
            
            assert health['redis_connected'] is True
            assert health['memory_cache_size'] >= 0
            assert 'stats' in health
    
    def test_cache_error_handling(self):
        """Test cache error handling."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            
            cache_manager = CacheManager(config)
            
            # Test Redis operation error
            mock_redis.get.side_effect = Exception("Redis error")
            
            result = cache_manager.get('error_key')
            assert result is None  # Should fallback gracefully
            assert cache_manager.stats['errors'] >= 1


@pytest.mark.unit
class TestCacheManagerSerialization:
    """Test cache serialization and deserialization."""
    
    def test_serialize_string(self):
        """Test string serialization."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            
            cache_manager = CacheManager(config)
            
            result = cache_manager._serialize("test_string")
            assert isinstance(result, str)
            assert json.loads(result) == "test_string"
    
    def test_serialize_dict(self):
        """Test dictionary serialization."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            
            cache_manager = CacheManager(config)
            
            test_dict = {"key": "value", "number": 123}
            result = cache_manager._serialize(test_dict)
            assert isinstance(result, str)
            assert json.loads(result) == test_dict
    
    def test_serialize_list(self):
        """Test list serialization."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            
            cache_manager = CacheManager(config)
            
            test_list = ["item1", "item2", 123]
            result = cache_manager._serialize(test_list)
            assert isinstance(result, str)
            assert json.loads(result) == test_list
    
    def test_deserialize_valid_json(self):
        """Test deserialization of valid JSON."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            
            cache_manager = CacheManager(config)
            
            test_data = {"key": "value"}
            serialized = json.dumps(test_data)
            result = cache_manager._deserialize(serialized.encode())
            assert result == test_data
    
    def test_deserialize_invalid_json(self):
        """Test deserialization of invalid JSON."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            
            cache_manager = CacheManager(config)
            
            # Invalid JSON should return None
            result = cache_manager._deserialize(b"invalid json")
            assert result is None


@pytest.mark.unit
class TestCacheManagerConfiguration:
    """Test cache manager configuration options."""
    
    def test_different_ttl_values(self):
        """Test cache manager respects different TTL values."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            
            cache_manager = CacheManager(config)
            
            # Test different TTL values
            cache_manager.set('short_ttl', 'value', ttl=10)
            cache_manager.set('long_ttl', 'value', ttl=3600)
            cache_manager.set('default_ttl', 'value')  # Should use config default
            
            # Verify Redis was called with setex
            assert mock_redis.setex.call_count >= 2
    
    def test_cache_prefix_configuration(self):
        """Test cache key prefix configuration."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            
            cache_manager = CacheManager(config, key_prefix="brazil_property:")
            
            cache_manager.set('test_key', 'value')
            
            # Should have called Redis with prefixed key
            called_key = mock_redis.setex.call_args[0][0]
            assert called_key.startswith("brazil_property:")
    
    def test_cache_namespace_isolation(self):
        """Test cache namespace isolation."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            
            cache_manager1 = CacheManager(config, namespace="properties")
            cache_manager2 = CacheManager(config, namespace="analytics")
            
            cache_manager1.set('same_key', 'value1')
            cache_manager2.set('same_key', 'value2')
            
            # Keys should be different due to namespace
            calls = mock_redis.setex.call_args_list
            assert len(calls) == 2
            assert calls[0][0][0] != calls[1][0][0]  # Different keys


@pytest.mark.unit 
class TestCacheManagerMemoryFallback:
    """Test memory cache fallback functionality."""
    
    def test_memory_cache_operations(self):
        """Test memory cache basic operations."""
        config = DevelopmentConfig()
        
        # Force Redis failure
        with patch('redis.Redis') as mock_redis_class:
            mock_redis_class.side_effect = Exception("Redis unavailable")
            
            cache_manager = CacheManager(config)
            
            # Should work with memory cache
            cache_manager.set('memory_key', {'data': 'value'})
            result = cache_manager.get('memory_key')
            
            assert result == {'data': 'value'}
            assert cache_manager.redis_connected is False
    
    def test_memory_cache_ttl_simulation(self):
        """Test memory cache TTL simulation."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis_class.side_effect = Exception("Redis unavailable")
            
            cache_manager = CacheManager(config)
            
            # Set with very short TTL
            import time
            cache_manager.set('expire_key', 'value', ttl=0.1)
            
            # Should be available immediately
            result = cache_manager.get('expire_key')
            assert result == 'value'
            
            # Wait for expiration
            time.sleep(0.2)
            result = cache_manager.get('expire_key')
            assert result is None
    
    def test_memory_cache_size_limit(self):
        """Test memory cache size limitations."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis_class.side_effect = Exception("Redis unavailable")
            
            cache_manager = CacheManager(config, max_memory_items=3)
            
            # Add items beyond limit
            for i in range(5):
                cache_manager.set(f'key_{i}', f'value_{i}')
            
            # Should have at most max_memory_items
            assert len(cache_manager.memory_cache) <= 3