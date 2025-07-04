import pytest
from unittest.mock import Mock, patch, MagicMock
import time
from datetime import datetime, timedelta

from src.analytics.analytics import Analytics
from src.analytics.metrics import MetricsCollector
from src.analytics.exceptions import AnalyticsError


class TestAnalytics:
    @pytest.fixture
    def analytics(self):
        config = {
            'ANALYTICS_ENABLED': True,
            'ANALYTICS_STORAGE': 'memory',
            'ANALYTICS_BATCH_SIZE': 100,
            'ANALYTICS_FLUSH_INTERVAL': 60,
            'TESTING': True
        }
        return Analytics(config)
    
    def test_request_tracking(self, analytics):
        """Test request tracking functionality."""
        # Track a request
        analytics.track_request(
            endpoint='/api/v1/search',
            method='GET',
            status_code=200,
            response_time=0.145,
            user_ip='192.168.1.1',
            user_agent='TestClient/1.0'
        )
        
        # Verify request was tracked
        stats = analytics.get_request_stats('/api/v1/search')
        assert stats['total_requests'] == 1
        assert stats['avg_response_time'] == 0.145
        assert stats['status_codes']['200'] == 1
    
    def test_performance_metrics(self, analytics):
        """Test performance metrics collection."""
        # Track multiple requests with different response times
        response_times = [0.1, 0.2, 0.15, 0.3, 0.25]
        
        for i, rt in enumerate(response_times):
            analytics.track_request(
                endpoint='/api/v1/search',
                method='GET',
                status_code=200,
                response_time=rt
            )
        
        # Get performance metrics
        metrics = analytics.get_performance_metrics('/api/v1/search')
        
        assert metrics['total_requests'] == 5
        assert metrics['avg_response_time'] == 0.2  # (0.1+0.2+0.15+0.3+0.25)/5
        assert metrics['min_response_time'] == 0.1
        assert metrics['max_response_time'] == 0.3
        assert 'p95_response_time' in metrics
        assert 'p99_response_time' in metrics
    
    def test_error_tracking(self, analytics):
        """Test error tracking functionality."""
        # Track errors
        analytics.track_error(
            endpoint='/api/v1/search',
            error_type='ValidationError',
            error_message='Invalid city parameter',
            stack_trace='File "/app/api.py", line 42...'
        )
        
        analytics.track_error(
            endpoint='/api/v1/search',
            error_type='DatabaseError',
            error_message='Connection timeout'
        )
        
        # Verify error tracking
        error_stats = analytics.get_error_stats('/api/v1/search')
        assert error_stats['total_errors'] == 2
        assert error_stats['error_types']['ValidationError'] == 1
        assert error_stats['error_types']['DatabaseError'] == 1
        
        # Test error rate calculation
        analytics.track_request('/api/v1/search', 'GET', 200, 0.1)  # Success
        error_rate = analytics.get_error_rate('/api/v1/search')
        assert error_rate == 2/3  # 2 errors out of 3 total (2 errors + 1 success)
    
    def test_user_behavior_analytics(self, analytics):
        """Test user behavior analytics."""
        # Track user behavior events
        analytics.track_user_event(
            user_id='user123',
            event_type='property_search',
            event_data={
                'city': 'São Paulo',
                'filters': {'min_price': 100000, 'bedrooms': 2},
                'results_count': 150
            }
        )
        
        analytics.track_user_event(
            user_id='user123',
            event_type='property_view',
            event_data={'property_id': 'prop456', 'price': 250000}
        )
        
        # Get user behavior stats
        user_stats = analytics.get_user_behavior_stats()
        assert user_stats['total_users'] == 1
        assert user_stats['total_events'] == 2
        assert user_stats['events_by_type']['property_search'] == 1
        assert user_stats['events_by_type']['property_view'] == 1
        
        # Get user-specific stats
        user_events = analytics.get_user_events('user123')
        assert len(user_events) == 2
        assert user_events[0]['event_type'] == 'property_search'
    
    def test_business_metrics(self, analytics):
        """Test business metrics tracking."""
        # Track business events
        analytics.track_business_metric('property_searches', 1, {'city': 'São Paulo'})
        analytics.track_business_metric('property_searches', 1, {'city': 'Rio de Janeiro'})
        analytics.track_business_metric('api_calls', 10)
        analytics.track_business_metric('cache_hits', 8)
        
        # Get business metrics
        metrics = analytics.get_business_metrics()
        assert metrics['property_searches'] == 2
        assert metrics['api_calls'] == 10
        assert metrics['cache_hits'] == 8
        
        # Test metric aggregation by dimensions
        search_by_city = analytics.get_business_metric_by_dimension('property_searches', 'city')
        assert search_by_city['São Paulo'] == 1
        assert search_by_city['Rio de Janeiro'] == 1
    
    def test_custom_events(self, analytics):
        """Test custom event tracking."""
        # Track custom events
        analytics.track_custom_event(
            event_name='scraper_run',
            event_data={
                'scraper_type': 'zap',
                'properties_found': 1250,
                'execution_time': 45.2,
                'success': True
            }
        )
        
        analytics.track_custom_event(
            event_name='cache_cleanup',
            event_data={
                'keys_removed': 150,
                'memory_freed_mb': 25.6
            }
        )
        
        # Get custom event stats
        custom_stats = analytics.get_custom_event_stats()
        assert custom_stats['total_events'] == 2
        assert 'scraper_run' in custom_stats['event_types']
        assert 'cache_cleanup' in custom_stats['event_types']
        
        # Get specific event data
        scraper_events = analytics.get_custom_events_by_type('scraper_run')
        assert len(scraper_events) == 1
        assert scraper_events[0]['event_data']['properties_found'] == 1250
    
    def test_analytics_batching(self, analytics):
        """Test analytics batching and flushing."""
        # Configure small batch size for testing
        old_batch_size = analytics.batch_size
        analytics.batch_size = 3
        
        # Track multiple requests
        for i in range(5):
            analytics.track_request(f'/api/v1/endpoint{i}', 'GET', 200, 0.1)
        
        # Check that batching occurred
        assert analytics.get_batch_count() >= 1
        
        # Force flush
        analytics.flush()
        
        # Verify all data was flushed
        assert analytics.get_pending_events_count() == 0
        
        # Restore original batch size
        analytics.batch_size = old_batch_size
    
    def test_analytics_filtering(self, analytics):
        """Test analytics data filtering and querying."""
        # Track requests over time
        base_time = datetime.utcnow()
        
        for i in range(10):
            timestamp = base_time + timedelta(minutes=i)
            analytics.track_request(
                endpoint='/api/v1/search',
                method='GET',
                status_code=200,
                response_time=0.1 + (i * 0.01),
                timestamp=timestamp
            )
        
        # Filter by time range
        recent_stats = analytics.get_request_stats(
            endpoint='/api/v1/search',
            start_time=base_time + timedelta(minutes=5),
            end_time=base_time + timedelta(minutes=9)
        )
        
        assert recent_stats['total_requests'] == 5  # Minutes 5-9
        
        # Filter by status code
        success_stats = analytics.get_request_stats(
            endpoint='/api/v1/search',
            status_codes=[200]
        )
        
        assert success_stats['total_requests'] == 10


class TestMetricsCollection:
    @pytest.fixture
    def metrics_collector(self):
        config = {
            'METRICS_ENABLED': True,
            'METRICS_STORAGE': 'memory',
            'METRICS_RETENTION_DAYS': 30,
            'TESTING': True
        }
        return MetricsCollector(config)
    
    def test_response_time_tracking(self, metrics_collector):
        """Test response time tracking and statistics."""
        endpoint = '/api/v1/search'
        
        # Record response times
        response_times = [0.1, 0.2, 0.15, 0.3, 0.25, 0.12, 0.18, 0.22, 0.28, 0.16]
        
        for rt in response_times:
            metrics_collector.record_response_time(endpoint, rt)
        
        # Get response time metrics
        metrics = metrics_collector.get_response_time_metrics(endpoint)
        
        assert metrics['count'] == 10
        assert metrics['avg'] == 0.196  # Average of response times
        assert metrics['min'] == 0.1
        assert metrics['max'] == 0.3
        assert 0.1 <= metrics['median'] <= 0.3
        assert 0.2 <= metrics['p95'] <= 0.3
        assert 0.25 <= metrics['p99'] <= 0.3
    
    def test_endpoint_usage_stats(self, metrics_collector):
        """Test endpoint usage statistics."""
        # Record endpoint usage
        endpoints = [
            '/api/v1/search',
            '/api/v1/search',
            '/api/v1/price-history',
            '/api/v1/search',
            '/api/v1/market-analysis',
            '/api/v1/search'
        ]
        
        for endpoint in endpoints:
            metrics_collector.record_endpoint_usage(endpoint, 'GET')
        
        # Get usage stats
        usage_stats = metrics_collector.get_endpoint_usage_stats()
        
        assert usage_stats['/api/v1/search'] == 4
        assert usage_stats['/api/v1/price-history'] == 1
        assert usage_stats['/api/v1/market-analysis'] == 1
        
        # Get top endpoints
        top_endpoints = metrics_collector.get_top_endpoints(limit=2)
        assert top_endpoints[0][0] == '/api/v1/search'
        assert top_endpoints[0][1] == 4
    
    def test_cache_performance_metrics(self, metrics_collector):
        """Test cache performance metrics."""
        # Record cache events
        metrics_collector.record_cache_hit('search_results')
        metrics_collector.record_cache_hit('property_details')
        metrics_collector.record_cache_miss('market_analysis')
        metrics_collector.record_cache_hit('search_results')
        metrics_collector.record_cache_miss('price_history')
        
        # Get cache metrics
        cache_metrics = metrics_collector.get_cache_metrics()
        
        assert cache_metrics['total_requests'] == 5
        assert cache_metrics['hits'] == 3
        assert cache_metrics['misses'] == 2
        assert cache_metrics['hit_ratio'] == 0.6
        
        # Get cache metrics by key pattern
        search_metrics = metrics_collector.get_cache_metrics_by_pattern('search_*')
        assert search_metrics['hits'] == 2
        assert search_metrics['misses'] == 0
    
    def test_database_performance_metrics(self, metrics_collector):
        """Test database performance metrics."""
        # Record database operations
        metrics_collector.record_db_operation('find', 'properties', 0.05, success=True)
        metrics_collector.record_db_operation('find', 'properties', 0.12, success=True)
        metrics_collector.record_db_operation('insert', 'properties', 0.08, success=True)
        metrics_collector.record_db_operation('find', 'properties', 0.25, success=False)
        
        # Get database metrics
        db_metrics = metrics_collector.get_database_metrics()
        
        assert db_metrics['total_operations'] == 4
        assert db_metrics['successful_operations'] == 3
        assert db_metrics['failed_operations'] == 1
        assert db_metrics['success_rate'] == 0.75
        assert db_metrics['avg_response_time'] == 0.125  # (0.05+0.12+0.08+0.25)/4
        
        # Get metrics by operation type
        find_metrics = metrics_collector.get_database_metrics_by_operation('find')
        assert find_metrics['total_operations'] == 3
        assert find_metrics['success_rate'] == 2/3  # 2 successful out of 3
    
    def test_scraper_success_rates(self, metrics_collector):
        """Test scraper success rate tracking."""
        # Record scraper runs
        metrics_collector.record_scraper_run('zap', success=True, properties_found=1250, duration=45.2)
        metrics_collector.record_scraper_run('zap', success=True, properties_found=1180, duration=42.8)
        metrics_collector.record_scraper_run('vivareal', success=True, properties_found=980, duration=38.5)
        metrics_collector.record_scraper_run('zap', success=False, error='Connection timeout', duration=60.0)
        metrics_collector.record_scraper_run('vivareal', success=True, properties_found=1050, duration=41.2)
        
        # Get overall scraper metrics
        scraper_metrics = metrics_collector.get_scraper_metrics()
        
        assert scraper_metrics['total_runs'] == 5
        assert scraper_metrics['successful_runs'] == 4
        assert scraper_metrics['success_rate'] == 0.8
        assert scraper_metrics['avg_duration'] == 45.54  # Average of all durations
        assert scraper_metrics['total_properties_found'] == 4460  # Sum of successful runs
        
        # Get metrics by scraper type
        zap_metrics = metrics_collector.get_scraper_metrics_by_type('zap')
        assert zap_metrics['total_runs'] == 3
        assert zap_metrics['success_rate'] == 2/3
        assert zap_metrics['avg_properties_per_run'] == (1250 + 1180) / 2  # Only successful runs
        
        vivareal_metrics = metrics_collector.get_scraper_metrics_by_type('vivareal')
        assert vivareal_metrics['total_runs'] == 2
        assert vivareal_metrics['success_rate'] == 1.0
    
    def test_metrics_aggregation_by_time(self, metrics_collector):
        """Test metrics aggregation by time periods."""
        base_time = datetime.utcnow()
        
        # Record metrics over different time periods
        for i in range(24):  # 24 hours
            timestamp = base_time + timedelta(hours=i)
            metrics_collector.record_endpoint_usage('/api/v1/search', 'GET', timestamp=timestamp)
            metrics_collector.record_response_time('/api/v1/search', 0.1 + (i * 0.01), timestamp=timestamp)
        
        # Get hourly aggregation
        hourly_metrics = metrics_collector.get_metrics_by_hour('/api/v1/search', base_time, base_time + timedelta(hours=23))
        assert len(hourly_metrics) == 24
        
        # Get daily aggregation
        daily_metrics = metrics_collector.get_metrics_by_day('/api/v1/search', base_time, base_time + timedelta(days=1))
        assert len(daily_metrics) == 1
        assert daily_metrics[0]['requests'] == 24
    
    def test_metrics_alerts(self, metrics_collector):
        """Test metrics-based alerting."""
        # Configure alert thresholds
        metrics_collector.set_alert_threshold('response_time', 0.5)  # 500ms
        metrics_collector.set_alert_threshold('error_rate', 0.1)     # 10%
        
        # Record metrics that should trigger alerts
        metrics_collector.record_response_time('/api/v1/search', 0.8)  # Above threshold
        metrics_collector.record_endpoint_usage('/api/v1/search', 'GET', status_code=500)  # Error
        
        # Check for alerts
        alerts = metrics_collector.get_active_alerts()
        
        assert len(alerts) >= 1
        response_time_alert = next((a for a in alerts if a['metric'] == 'response_time'), None)
        assert response_time_alert is not None
        assert response_time_alert['value'] == 0.8
        assert response_time_alert['threshold'] == 0.5