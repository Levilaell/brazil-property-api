"""
Metrics collection system for the Brazil Property API.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import statistics
import threading

from src.analytics.exceptions import MetricsError


logger = logging.getLogger(__name__)


class MetricsCollector:
    """Metrics collection and aggregation system."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('METRICS_ENABLED', True)
        self.storage_type = config.get('METRICS_STORAGE', 'memory')
        self.retention_days = config.get('METRICS_RETENTION_DAYS', 30)
        
        # In-memory storage for metrics
        self._response_times = defaultdict(list)
        self._endpoint_usage = defaultdict(int)
        self._cache_metrics = {
            'hits': 0,
            'misses': 0,
            'total_requests': 0,
            'hit_details': defaultdict(int),
            'miss_details': defaultdict(int)
        }
        self._database_metrics = []
        self._scraper_metrics = []
        self._alerts = []
        self._alert_thresholds = {}
        
        # Time-based aggregations
        self._hourly_metrics = defaultdict(lambda: defaultdict(list))
        self._daily_metrics = defaultdict(lambda: defaultdict(list))
        
        self._lock = threading.Lock()
        
        logger.info("MetricsCollector initialized")
    
    def record_response_time(self, endpoint: str, response_time: float, timestamp: Optional[datetime] = None):
        """Record response time for an endpoint."""
        if not self.enabled:
            return
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        with self._lock:
            self._response_times[endpoint].append({
                'time': response_time,
                'timestamp': timestamp
            })
            
            # Add to time-based aggregations
            hour_key = timestamp.replace(minute=0, second=0, microsecond=0)
            day_key = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            
            self._hourly_metrics[endpoint][hour_key].append(response_time)
            self._daily_metrics[endpoint][day_key].append(response_time)
            
            # Check alert thresholds
            self._check_response_time_alert(endpoint, response_time)
    
    def record_endpoint_usage(self, endpoint: str, method: str, timestamp: Optional[datetime] = None,
                            status_code: Optional[int] = None):
        """Record endpoint usage."""
        if not self.enabled:
            return
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        endpoint_key = f"{method} {endpoint}"
        
        with self._lock:
            self._endpoint_usage[endpoint_key] += 1
            
            # Record error if status code indicates failure
            if status_code and status_code >= 500:
                self._check_error_rate_alert(endpoint_key)
    
    def record_cache_hit(self, cache_key: str):
        """Record a cache hit."""
        if not self.enabled:
            return
        
        with self._lock:
            self._cache_metrics['hits'] += 1
            self._cache_metrics['total_requests'] += 1
            self._cache_metrics['hit_details'][cache_key] += 1
    
    def record_cache_miss(self, cache_key: str):
        """Record a cache miss."""
        if not self.enabled:
            return
        
        with self._lock:
            self._cache_metrics['misses'] += 1
            self._cache_metrics['total_requests'] += 1
            self._cache_metrics['miss_details'][cache_key] += 1
    
    def record_db_operation(self, operation: str, collection: str, duration: float, success: bool):
        """Record a database operation."""
        if not self.enabled:
            return
        
        with self._lock:
            self._database_metrics.append({
                'operation': operation,
                'collection': collection,
                'duration': duration,
                'success': success,
                'timestamp': datetime.utcnow()
            })
    
    def record_scraper_run(self, scraper_type: str, success: bool, properties_found: Optional[int] = None,
                          duration: Optional[float] = None, error: Optional[str] = None):
        """Record a scraper run."""
        if not self.enabled:
            return
        
        with self._lock:
            self._scraper_metrics.append({
                'scraper_type': scraper_type,
                'success': success,
                'properties_found': properties_found or 0,
                'duration': duration or 0,
                'error': error,
                'timestamp': datetime.utcnow()
            })
    
    def get_response_time_metrics(self, endpoint: str) -> Dict[str, float]:
        """Get response time metrics for an endpoint."""
        with self._lock:
            response_times = [rt['time'] for rt in self._response_times.get(endpoint, [])]
        
        if not response_times:
            return {
                'count': 0,
                'avg': 0,
                'min': 0,
                'max': 0,
                'median': 0,
                'p95': 0,
                'p99': 0
            }
        
        response_times.sort()
        
        return {
            'count': len(response_times),
            'avg': statistics.mean(response_times),
            'min': min(response_times),
            'max': max(response_times),
            'median': statistics.median(response_times),
            'p95': self._percentile(response_times, 95),
            'p99': self._percentile(response_times, 99)
        }
    
    def get_endpoint_usage_stats(self) -> Dict[str, int]:
        """Get endpoint usage statistics."""
        with self._lock:
            return dict(self._endpoint_usage)
    
    def get_top_endpoints(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get top endpoints by usage."""
        with self._lock:
            usage_items = list(self._endpoint_usage.items())
        
        usage_items.sort(key=lambda x: x[1], reverse=True)
        return usage_items[:limit]
    
    def get_cache_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics."""
        with self._lock:
            metrics = self._cache_metrics.copy()
        
        if metrics['total_requests'] > 0:
            metrics['hit_ratio'] = metrics['hits'] / metrics['total_requests']
        else:
            metrics['hit_ratio'] = 0
        
        return metrics
    
    def get_cache_metrics_by_pattern(self, pattern: str) -> Dict[str, Any]:
        """Get cache metrics filtered by key pattern."""
        with self._lock:
            hit_details = dict(self._cache_metrics['hit_details'])
            miss_details = dict(self._cache_metrics['miss_details'])
        
        # Simple pattern matching (starts with)
        pattern_prefix = pattern.replace('*', '')
        
        filtered_hits = sum(count for key, count in hit_details.items() if key.startswith(pattern_prefix))
        filtered_misses = sum(count for key, count in miss_details.items() if key.startswith(pattern_prefix))
        total = filtered_hits + filtered_misses
        
        return {
            'hits': filtered_hits,
            'misses': filtered_misses,
            'total_requests': total,
            'hit_ratio': filtered_hits / total if total > 0 else 0
        }
    
    def get_database_metrics(self) -> Dict[str, Any]:
        """Get database performance metrics."""
        with self._lock:
            operations = self._database_metrics.copy()
        
        if not operations:
            return {
                'total_operations': 0,
                'successful_operations': 0,
                'failed_operations': 0,
                'success_rate': 0,
                'avg_response_time': 0
            }
        
        successful = sum(1 for op in operations if op['success'])
        failed = len(operations) - successful
        avg_time = statistics.mean(op['duration'] for op in operations)
        
        return {
            'total_operations': len(operations),
            'successful_operations': successful,
            'failed_operations': failed,
            'success_rate': successful / len(operations),
            'avg_response_time': avg_time
        }
    
    def get_database_metrics_by_operation(self, operation_type: str) -> Dict[str, Any]:
        """Get database metrics filtered by operation type."""
        with self._lock:
            operations = [op for op in self._database_metrics if op['operation'] == operation_type]
        
        if not operations:
            return {
                'total_operations': 0,
                'successful_operations': 0,
                'failed_operations': 0,
                'success_rate': 0,
                'avg_response_time': 0
            }
        
        successful = sum(1 for op in operations if op['success'])
        failed = len(operations) - successful
        avg_time = statistics.mean(op['duration'] for op in operations)
        
        return {
            'total_operations': len(operations),
            'successful_operations': successful,
            'failed_operations': failed,
            'success_rate': successful / len(operations),
            'avg_response_time': avg_time
        }
    
    def get_scraper_metrics(self) -> Dict[str, Any]:
        """Get scraper performance metrics."""
        with self._lock:
            runs = self._scraper_metrics.copy()
        
        if not runs:
            return {
                'total_runs': 0,
                'successful_runs': 0,
                'success_rate': 0,
                'avg_duration': 0,
                'total_properties_found': 0
            }
        
        successful_runs = [run for run in runs if run['success']]
        total_properties = sum(run['properties_found'] for run in successful_runs)
        
        return {
            'total_runs': len(runs),
            'successful_runs': len(successful_runs),
            'success_rate': len(successful_runs) / len(runs),
            'avg_duration': statistics.mean(run['duration'] for run in runs),
            'total_properties_found': total_properties
        }
    
    def get_scraper_metrics_by_type(self, scraper_type: str) -> Dict[str, Any]:
        """Get scraper metrics filtered by scraper type."""
        with self._lock:
            runs = [run for run in self._scraper_metrics if run['scraper_type'] == scraper_type]
        
        if not runs:
            return {
                'total_runs': 0,
                'successful_runs': 0,
                'success_rate': 0,
                'avg_duration': 0,
                'avg_properties_per_run': 0
            }
        
        successful_runs = [run for run in runs if run['success']]
        
        if successful_runs:
            avg_properties = statistics.mean(run['properties_found'] for run in successful_runs)
        else:
            avg_properties = 0
        
        return {
            'total_runs': len(runs),
            'successful_runs': len(successful_runs),
            'success_rate': len(successful_runs) / len(runs),
            'avg_duration': statistics.mean(run['duration'] for run in runs),
            'avg_properties_per_run': avg_properties
        }
    
    def get_metrics_by_hour(self, endpoint: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get metrics aggregated by hour."""
        with self._lock:
            hourly_data = self._hourly_metrics.get(endpoint, {})
        
        results = []
        current_time = start_time.replace(minute=0, second=0, microsecond=0)
        
        while current_time <= end_time:
            hour_data = hourly_data.get(current_time, [])
            
            if hour_data:
                results.append({
                    'timestamp': current_time,
                    'requests': len(hour_data),
                    'avg_response_time': statistics.mean(hour_data),
                    'min_response_time': min(hour_data),
                    'max_response_time': max(hour_data)
                })
            else:
                results.append({
                    'timestamp': current_time,
                    'requests': 0,
                    'avg_response_time': 0,
                    'min_response_time': 0,
                    'max_response_time': 0
                })
            
            current_time += timedelta(hours=1)
        
        return results
    
    def get_metrics_by_day(self, endpoint: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get metrics aggregated by day."""
        with self._lock:
            daily_data = self._daily_metrics.get(endpoint, {})
        
        results = []
        current_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        while current_time <= end_time:
            day_data = daily_data.get(current_time, [])
            
            if day_data:
                results.append({
                    'timestamp': current_time,
                    'requests': len(day_data),
                    'avg_response_time': statistics.mean(day_data),
                    'min_response_time': min(day_data),
                    'max_response_time': max(day_data)
                })
            else:
                results.append({
                    'timestamp': current_time,
                    'requests': 0,
                    'avg_response_time': 0,
                    'min_response_time': 0,
                    'max_response_time': 0
                })
            
            current_time += timedelta(days=1)
        
        return results
    
    def set_alert_threshold(self, metric: str, threshold: float):
        """Set alert threshold for a metric."""
        self._alert_thresholds[metric] = threshold
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts."""
        with self._lock:
            return self._alerts.copy()
    
    def _check_response_time_alert(self, endpoint: str, response_time: float):
        """Check if response time exceeds threshold."""
        threshold = self._alert_thresholds.get('response_time')
        if threshold and response_time > threshold:
            alert = {
                'metric': 'response_time',
                'endpoint': endpoint,
                'value': response_time,
                'threshold': threshold,
                'timestamp': datetime.utcnow()
            }
            self._alerts.append(alert)
    
    def _check_error_rate_alert(self, endpoint: str):
        """Check if error rate exceeds threshold."""
        threshold = self._alert_thresholds.get('error_rate')
        if not threshold:
            return
        
        # Calculate current error rate for endpoint
        # This is simplified; in practice, you'd track errors separately
        pass
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0.0
        
        index = (percentile / 100.0) * (len(data) - 1)
        lower_index = int(index)
        upper_index = min(lower_index + 1, len(data) - 1)
        
        if lower_index == upper_index:
            return data[lower_index]
        
        # Linear interpolation
        weight = index - lower_index
        return data[lower_index] * (1 - weight) + data[upper_index] * weight