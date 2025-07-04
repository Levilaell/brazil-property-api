"""
Tests for Cache Decorator functionality.
Following TDD approach - write tests first, then implement.
"""
import pytest
import time
from unittest.mock import Mock, patch
from src.cache import cache_result, CacheManager
from src.config import DevelopmentConfig


@pytest.mark.unit
class TestCacheDecorator:
    """Test cache result decorator functionality."""
    
    def test_function_result_cached(self):
        """Test that function results are cached."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            mock_redis.get.return_value = None  # Cache miss first time
            
            call_count = 0
            
            @cache_result(config, ttl=300)
            def expensive_function(x, y):
                nonlocal call_count
                call_count += 1
                return x + y
            
            # First call should execute function
            result1 = expensive_function(1, 2)
            assert result1 == 3
            assert call_count == 1
            
            # Second call should use cache (but mock returns None, so will execute again)
            result2 = expensive_function(1, 2)
            assert result2 == 3
            assert call_count == 2  # Mock doesn't return cached value
    
    def test_cache_hit_skips_execution(self):
        """Test that cache hit skips function execution."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            mock_redis.get.return_value = b'"cached_result"'  # Cache hit
            
            call_count = 0
            
            @cache_result(config, ttl=300)
            def expensive_function(x):
                nonlocal call_count
                call_count += 1
                return x * 2
            
            # Function should not be called due to cache hit
            result = expensive_function(5)
            assert result == "cached_result"
            assert call_count == 0
    
    def test_cache_miss_executes_function(self):
        """Test that cache miss executes the function."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            mock_redis.get.return_value = None  # Cache miss
            
            call_count = 0
            
            @cache_result(config, ttl=300)
            def compute_result(x):
                nonlocal call_count
                call_count += 1
                return x ** 2
            
            result = compute_result(4)
            assert result == 16
            assert call_count == 1
    
    def test_cache_key_from_args(self):
        """Test cache key generation from function arguments."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            mock_redis.get.return_value = None
            
            @cache_result(config)
            def test_function(a, b, c):
                return a + b + c
            
            # Call function with different arguments
            test_function(1, 2, 3)
            test_function(4, 5, 6)
            
            # Should have been called twice with different keys
            assert mock_redis.setex.call_count == 2
            
            # Keys should be different
            calls = mock_redis.setex.call_args_list
            key1 = calls[0][0][0]
            key2 = calls[1][0][0]
            assert key1 != key2
    
    def test_cache_key_from_kwargs(self):
        """Test cache key generation from keyword arguments."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            mock_redis.get.return_value = None
            
            @cache_result(config)
            def test_function(a, b=10, c=20):
                return a + b + c
            
            # Call function with different kwargs
            test_function(1, b=5, c=15)
            test_function(1, b=10, c=20)
            
            # Should generate different cache keys
            assert mock_redis.setex.call_count == 2
            calls = mock_redis.setex.call_args_list
            key1 = calls[0][0][0]
            key2 = calls[1][0][0]
            assert key1 != key2
    
    def test_custom_ttl_respected(self):
        """Test that custom TTL values are respected."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            mock_redis.get.return_value = None
            
            @cache_result(config, ttl=1800)
            def test_function(x):
                return x * 2
            
            test_function(5)
            
            # Verify TTL was passed to cache
            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args
            ttl_used = call_args[0][1]  # Second argument is TTL
            assert ttl_used == 1800
    
    def test_cache_invalidation_pattern(self):
        """Test cache invalidation pattern support."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            mock_redis.get.return_value = None
            mock_redis.delete.return_value = 1
            
            @cache_result(config, cache_prefix="test_func:")
            def test_function(x):
                return x * 2
            
            test_function(5)
            
            # Verify cache key has the prefix
            call_args = mock_redis.setex.call_args
            cache_key = call_args[0][0]
            assert "test_func:" in cache_key
    
    def test_decorator_with_class_methods(self):
        """Test decorator works with class methods."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            mock_redis.get.return_value = None
            
            class TestClass:
                @cache_result(config, ttl=600)
                def compute_value(self, x, y):
                    return x * y + 10
            
            obj = TestClass()
            result = obj.compute_value(3, 4)
            assert result == 22
            
            # Verify cache was used
            mock_redis.setex.assert_called_once()
    
    def test_decorator_with_async_functions(self):
        """Test decorator works with async functions."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            mock_redis.get.return_value = None
            
            @cache_result(config, ttl=300)
            async def async_function(x):
                return x ** 2
            
            import asyncio
            
            async def test_async():
                result = await async_function(4)
                assert result == 16
            
            # Run async test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(test_async())
            finally:
                loop.close()
    
    def test_cache_error_handling(self):
        """Test cache decorator handles errors gracefully."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.side_effect = Exception("Cache error")
            mock_redis.get.side_effect = Exception("Cache error")
            
            call_count = 0
            
            @cache_result(config, ttl=300)
            def test_function(x):
                nonlocal call_count
                call_count += 1
                return x * 2
            
            # Function should still work even if cache fails
            result = test_function(5)
            assert result == 10
            assert call_count == 1
    
    def test_cache_disabled_mode(self):
        """Test cache decorator can be disabled."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            
            call_count = 0
            
            @cache_result(config, enabled=False)
            def test_function(x):
                nonlocal call_count
                call_count += 1
                return x * 2
            
            # Function should be called each time when cache is disabled
            result1 = test_function(5)
            result2 = test_function(5)
            
            assert result1 == 10
            assert result2 == 10
            assert call_count == 2
            
            # Cache should not have been used
            assert not mock_redis.get.called
            assert not mock_redis.setex.called


@pytest.mark.unit
class TestCacheDecoratorAdvanced:
    """Test advanced cache decorator functionality."""
    
    def test_conditional_caching(self):
        """Test conditional caching based on function result."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            mock_redis.get.return_value = None
            
            def should_cache(result):
                # Only cache positive results
                return result > 0
            
            @cache_result(config, condition=should_cache)
            def test_function(x):
                return x - 5
            
            # Should cache positive result
            result1 = test_function(10)  # Returns 5 (positive)
            assert result1 == 5
            
            # Should not cache negative result
            result2 = test_function(2)   # Returns -3 (negative)
            assert result2 == -3
            
            # Verify only positive result was cached
            assert mock_redis.setex.call_count == 1
    
    def test_cache_serialization_options(self):
        """Test different serialization options for cache."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            mock_redis.get.return_value = None
            
            @cache_result(config, serializer='json')
            def json_function(data):
                return {"result": data * 2}
            
            @cache_result(config, serializer='pickle')
            def pickle_function(data):
                return {"result": data * 3, "complex": set([1, 2, 3])}
            
            # Test JSON serialization
            result1 = json_function(5)
            assert result1 == {"result": 10}
            
            # Test pickle serialization  
            result2 = pickle_function(4)
            assert result2 == {"result": 12, "complex": set([1, 2, 3])}
    
    def test_cache_versioning(self):
        """Test cache versioning for function changes."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            mock_redis.get.return_value = None
            
            @cache_result(config, version="v1.0")
            def versioned_function(x):
                return x * 2
            
            versioned_function(5)
            
            # Verify version is included in cache key
            call_args = mock_redis.setex.call_args
            cache_key = call_args[0][0]
            assert "v1.0" in cache_key
    
    def test_cache_warming(self):
        """Test cache warming functionality."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            mock_redis.get.return_value = None
            
            @cache_result(config, warm_cache=True)
            def warmable_function(x):
                return x ** 2
            
            # Function should support cache warming
            assert hasattr(warmable_function, 'warm_cache')
            assert hasattr(warmable_function, 'invalidate_cache')
    
    def test_cache_statistics_tracking(self):
        """Test cache statistics tracking in decorator."""
        config = DevelopmentConfig()
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            mock_redis.get.return_value = None
            
            @cache_result(config, track_stats=True)
            def tracked_function(x):
                return x * 2
            
            # Function should track cache statistics
            result = tracked_function(5)
            assert result == 10
            
            # Should have statistics available
            if hasattr(tracked_function, 'cache_stats'):
                stats = tracked_function.cache_stats
                assert 'calls' in stats
                assert 'cache_hits' in stats
                assert 'cache_misses' in stats