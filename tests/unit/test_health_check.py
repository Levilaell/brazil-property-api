import pytest
from unittest.mock import Mock, patch, MagicMock
import time
from datetime import datetime, timedelta

from src.analytics.health_check import HealthChecker, ComponentHealth
from src.analytics.exceptions import HealthCheckError


class TestHealthCheck:
    @pytest.fixture
    def health_checker(self):
        config = {
            'HEALTH_CHECK_ENABLED': True,
            'HEALTH_CHECK_TIMEOUT': 5,
            'HEALTH_CHECK_CACHE_TTL': 60,
            'HEALTH_CHECK_COMPONENTS': ['database', 'cache', 'scrapers'],
            'TESTING': True
        }
        return HealthChecker(config)
    
    def test_database_health(self, health_checker):
        """Test database health check."""
        # Mock successful database connection
        with patch('src.database.MongoDBHandler') as mock_db_class:
            mock_db = mock_db_class.return_value
            mock_db.ping.return_value = True
            mock_db.get_connection_stats.return_value = {
                'active_connections': 5,
                'max_connections': 100,
                'response_time_ms': 12
            }
            
            # Check database health
            db_health = health_checker.check_database_health()
            
            assert db_health.status == 'healthy'
            assert db_health.component == 'database'
            assert 'response_time_ms' in db_health.details
            assert db_health.details['active_connections'] == 5
            
        # Mock database connection failure
        with patch('src.database.MongoDBHandler') as mock_db_class:
            mock_db = mock_db_class.return_value
            mock_db.ping.side_effect = Exception('Connection failed')
            
            db_health = health_checker.check_database_health()
            
            assert db_health.status == 'unhealthy'
            assert 'Connection failed' in db_health.error_message
    
    def test_cache_health(self, health_checker):
        """Test cache health check."""
        # Mock successful cache connection
        with patch('src.cache.CacheManager') as mock_cache_class:
            mock_cache = mock_cache_class.return_value
            mock_cache.health_check.return_value = {
                'status': 'healthy',
                'redis_connected': True,
                'memory_usage_mb': 45.2,
                'keys_count': 1250,
                'hit_ratio': 0.85
            }
            
            # Check cache health
            cache_health = health_checker.check_cache_health()
            
            assert cache_health.status == 'healthy'
            assert cache_health.component == 'cache'
            assert cache_health.details['redis_connected'] is True
            assert cache_health.details['hit_ratio'] == 0.85
            
        # Mock cache connection failure
        with patch('src.cache.CacheManager') as mock_cache_class:
            mock_cache = mock_cache_class.return_value
            mock_cache.health_check.side_effect = Exception('Redis unavailable')
            
            cache_health = health_checker.check_cache_health()
            
            assert cache_health.status == 'unhealthy'
            assert 'Redis unavailable' in cache_health.error_message
    
    def test_external_services_health(self, health_checker):
        """Test external services health check."""
        # Mock successful external service checks
        with patch('requests.get') as mock_get:
            # Mock ZAP website response
            zap_response = Mock()
            zap_response.status_code = 200
            zap_response.elapsed.total_seconds.return_value = 0.5
            
            # Mock VivaReal website response  
            vivareal_response = Mock()
            vivareal_response.status_code = 200
            vivareal_response.elapsed.total_seconds.return_value = 0.7
            
            mock_get.side_effect = [zap_response, vivareal_response]
            
            # Check external services health
            services_health = health_checker.check_external_services_health()
            
            assert services_health.status == 'healthy'
            assert services_health.component == 'external_services'
            assert 'zap' in services_health.details
            assert 'vivareal' in services_health.details
            assert services_health.details['zap']['status_code'] == 200
            assert services_health.details['vivareal']['response_time'] == 0.7
            
        # Mock external service failure
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception('Connection timeout')
            
            services_health = health_checker.check_external_services_health()
            
            assert services_health.status == 'degraded'  # Some services might still work
    
    def test_overall_health_status(self, health_checker):
        """Test overall health status aggregation."""
        # Mock all components healthy
        with patch.object(health_checker, 'check_database_health') as mock_db:
            with patch.object(health_checker, 'check_cache_health') as mock_cache:
                with patch.object(health_checker, 'check_external_services_health') as mock_services:
                    
                    mock_db.return_value = ComponentHealth('database', 'healthy', {})
                    mock_cache.return_value = ComponentHealth('cache', 'healthy', {})
                    mock_services.return_value = ComponentHealth('external_services', 'healthy', {})
                    
                    overall_health = health_checker.get_overall_health()
                    
                    assert overall_health['status'] == 'healthy'
                    assert len(overall_health['components']) == 3
                    assert all(comp['status'] == 'healthy' for comp in overall_health['components'])
                    
        # Mock one component unhealthy
        with patch.object(health_checker, 'check_database_health') as mock_db:
            with patch.object(health_checker, 'check_cache_health') as mock_cache:
                with patch.object(health_checker, 'check_external_services_health') as mock_services:
                    
                    mock_db.return_value = ComponentHealth('database', 'unhealthy', {}, 'Connection failed')
                    mock_cache.return_value = ComponentHealth('cache', 'healthy', {})
                    mock_services.return_value = ComponentHealth('external_services', 'healthy', {})
                    
                    overall_health = health_checker.get_overall_health()
                    
                    assert overall_health['status'] == 'degraded'
                    unhealthy_components = [c for c in overall_health['components'] if c['status'] == 'unhealthy']
                    assert len(unhealthy_components) == 1
                    assert unhealthy_components[0]['component'] == 'database'
    
    def test_health_check_caching(self, health_checker):
        """Test health check caching functionality."""
        with patch.object(health_checker, 'check_database_health') as mock_db:
            # First call should execute the check
            mock_db.return_value = ComponentHealth('database', 'healthy', {'response_time': 10})
            
            result1 = health_checker.get_cached_health_check('database')
            assert result1.status == 'healthy'
            assert mock_db.call_count == 1
            
            # Second call should use cache
            result2 = health_checker.get_cached_health_check('database')
            assert result2.status == 'healthy'
            assert mock_db.call_count == 1  # Still 1, used cache
            
            # Force refresh should bypass cache
            result3 = health_checker.get_cached_health_check('database', force_refresh=True)
            assert result3.status == 'healthy'
            assert mock_db.call_count == 2  # Incremented, bypassed cache
    
    def test_detailed_health_info(self, health_checker):
        """Test detailed health information collection."""
        with patch('src.database.MongoDBHandler') as mock_db_class:
            with patch('src.cache.CacheManager') as mock_cache_class:
                # Setup detailed mock responses
                mock_db = mock_db_class.return_value
                mock_db.ping.return_value = True
                mock_db.get_connection_stats.return_value = {
                    'active_connections': 5,
                    'max_connections': 100,
                    'response_time_ms': 12,
                    'database_size_mb': 1250.5,
                    'collections_count': 3,
                    'indexes_count': 15
                }
                
                mock_cache = mock_cache_class.return_value
                mock_cache.health_check.return_value = {
                    'status': 'healthy',
                    'redis_connected': True,
                    'memory_usage_mb': 45.2,
                    'keys_count': 1250,
                    'hit_ratio': 0.85,
                    'total_commands_processed': 150000,
                    'connected_clients': 3
                }
                
                # Get detailed health info
                detailed_health = health_checker.get_detailed_health_info()
                
                assert 'database' in detailed_health
                assert 'cache' in detailed_health
                assert 'external_services' in detailed_health
                assert 'system' in detailed_health
                
                # Check database details
                db_info = detailed_health['database']
                assert db_info['database_size_mb'] == 1250.5
                assert db_info['collections_count'] == 3
                
                # Check cache details
                cache_info = detailed_health['cache']
                assert cache_info['keys_count'] == 1250
                assert cache_info['total_commands_processed'] == 150000
    
    def test_health_check_timeouts(self, health_checker):
        """Test health check timeout handling."""
        # Configure short timeout for testing
        health_checker.timeout = 0.1
        
        # Mock slow database response
        with patch('src.database.MongoDBHandler') as mock_db_class:
            mock_db = mock_db_class.return_value
            
            def slow_ping():
                time.sleep(0.2)  # Longer than timeout
                return True
            
            mock_db.ping = slow_ping
            
            # Health check should timeout
            db_health = health_checker.check_database_health()
            
            assert db_health.status == 'unhealthy'
            assert 'timeout' in db_health.error_message.lower()
    
    def test_health_check_alerts(self, health_checker):
        """Test health check alerting system."""
        # Configure alert thresholds
        health_checker.set_alert_thresholds({
            'database_response_time_ms': 100,
            'cache_memory_usage_mb': 100,
            'cache_hit_ratio': 0.7
        })
        
        # Mock health check responses that exceed thresholds
        with patch('src.database.MongoDBHandler') as mock_db_class:
            with patch('src.cache.CacheManager') as mock_cache_class:
                mock_db = mock_db_class.return_value
                mock_db.ping.return_value = True
                mock_db.get_connection_stats.return_value = {
                    'response_time_ms': 150  # Above threshold
                }
                
                mock_cache = mock_cache_class.return_value
                mock_cache.health_check.return_value = {
                    'status': 'healthy',
                    'memory_usage_mb': 120,  # Above threshold
                    'hit_ratio': 0.6  # Below threshold
                }
                
                # Run health checks
                health_checker.check_database_health()
                health_checker.check_cache_health()
                
                # Get alerts
                alerts = health_checker.get_health_alerts()
                
                assert len(alerts) == 3  # Three metrics exceeded thresholds
                alert_metrics = [alert['metric'] for alert in alerts]
                assert 'database_response_time_ms' in alert_metrics
                assert 'cache_memory_usage_mb' in alert_metrics
                assert 'cache_hit_ratio' in alert_metrics
    
    def test_health_history_tracking(self, health_checker):
        """Test health check history tracking."""
        # Enable history tracking
        health_checker.enable_history_tracking()
        
        with patch.object(health_checker, 'check_database_health') as mock_db:
            # Simulate health checks over time
            health_statuses = ['healthy', 'healthy', 'degraded', 'unhealthy', 'healthy']
            
            for i, status in enumerate(health_statuses):
                timestamp = datetime.utcnow() + timedelta(minutes=i)
                mock_db.return_value = ComponentHealth('database', status, {}, timestamp=timestamp)
                
                health_checker.check_database_health()
            
            # Get health history
            history = health_checker.get_health_history('database', hours=1)
            
            assert len(history) == 5
            assert [h['status'] for h in history] == health_statuses
            
            # Get health trends
            trends = health_checker.get_health_trends('database')
            
            assert 'avg_uptime_percentage' in trends
            assert 'status_changes' in trends
            assert trends['status_changes'] == 4  # Number of status changes
    
    def test_component_health_scoring(self, health_checker):
        """Test health scoring system."""
        # Test different health scenarios
        scenarios = [
            {'status': 'healthy', 'response_time': 10, 'expected_score': 100},
            {'status': 'healthy', 'response_time': 50, 'expected_score': 90},
            {'status': 'degraded', 'response_time': 100, 'expected_score': 60},
            {'status': 'unhealthy', 'response_time': 1000, 'expected_score': 0}
        ]
        
        for scenario in scenarios:
            component_health = ComponentHealth(
                component='test',
                status=scenario['status'],
                details={'response_time_ms': scenario['response_time']}
            )
            
            score = health_checker.calculate_health_score(component_health)
            assert abs(score - scenario['expected_score']) <= 10  # Allow some tolerance
    
    def test_health_check_dependencies(self, health_checker):
        """Test health check component dependencies."""
        # Define component dependencies
        health_checker.set_component_dependencies({
            'api': ['database', 'cache'],
            'scrapers': ['database', 'external_services'],
            'analytics': ['database']
        })
        
        with patch.object(health_checker, 'check_database_health') as mock_db:
            with patch.object(health_checker, 'check_cache_health') as mock_cache:
                with patch.object(health_checker, 'check_external_services_health') as mock_services:
                    
                    # Mock database unhealthy, others healthy
                    mock_db.return_value = ComponentHealth('database', 'unhealthy', {})
                    mock_cache.return_value = ComponentHealth('cache', 'healthy', {})
                    mock_services.return_value = ComponentHealth('external_services', 'healthy', {})
                    
                    # Check dependent component status
                    api_health = health_checker.check_dependent_component_health('api')
                    scrapers_health = health_checker.check_dependent_component_health('scrapers')
                    analytics_health = health_checker.check_dependent_component_health('analytics')
                    
                    # API depends on database (unhealthy) and cache (healthy) -> degraded
                    assert api_health.status == 'degraded'
                    
                    # Scrapers depend on database (unhealthy) and external_services (healthy) -> degraded
                    assert scrapers_health.status == 'degraded'
                    
                    # Analytics depends only on database (unhealthy) -> unhealthy
                    assert analytics_health.status == 'unhealthy'