"""
Analytics system for the Brazil Property API.
"""
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
import statistics
import threading

from src.analytics.exceptions import AnalyticsError, StorageError


logger = logging.getLogger(__name__)


class Analytics:
    """Main analytics class for tracking and analyzing API usage."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('ANALYTICS_ENABLED', True)
        self.storage_type = config.get('ANALYTICS_STORAGE', 'memory')
        self.batch_size = config.get('ANALYTICS_BATCH_SIZE', 100)
        self.flush_interval = config.get('ANALYTICS_FLUSH_INTERVAL', 60)
        
        # In-memory storage for analytics data
        self._requests = defaultdict(list)
        self._errors = defaultdict(list)
        self._user_events = defaultdict(list)
        self._business_metrics = defaultdict(list)
        self._custom_events = defaultdict(list)
        
        # Batching system
        self._pending_events = []
        self._batch_count = 0
        self._lock = threading.Lock()
        
        # Start background flush if enabled (but never in testing)
        self._background_thread = None
        if self.enabled and self.flush_interval > 0 and not config.get('TESTING', False):
            self._start_background_flush()
        
        logger.info("Analytics system initialized")
    
    def track_request(self, endpoint: str, method: str, status_code: int, response_time: float,
                     user_ip: Optional[str] = None, user_agent: Optional[str] = None,
                     timestamp: Optional[datetime] = None):
        """Track an API request."""
        if not self.enabled:
            return
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        request_data = {
            'endpoint': endpoint,
            'method': method,
            'status_code': status_code,
            'response_time': response_time,
            'user_ip': user_ip,
            'user_agent': user_agent,
            'timestamp': timestamp
        }
        
        with self._lock:
            self._requests[endpoint].append(request_data)
            self._add_to_batch('request', request_data)
    
    def track_error(self, endpoint: str, error_type: str, error_message: str,
                   stack_trace: Optional[str] = None, timestamp: Optional[datetime] = None):
        """Track an error occurrence."""
        if not self.enabled:
            return
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        error_data = {
            'endpoint': endpoint,
            'error_type': error_type,
            'error_message': error_message,
            'stack_trace': stack_trace,
            'timestamp': timestamp
        }
        
        with self._lock:
            self._errors[endpoint].append(error_data)
            self._add_to_batch('error', error_data)
    
    def track_user_event(self, user_id: str, event_type: str, event_data: Dict[str, Any],
                        timestamp: Optional[datetime] = None):
        """Track a user behavior event."""
        if not self.enabled:
            return
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        user_event = {
            'user_id': user_id,
            'event_type': event_type,
            'event_data': event_data,
            'timestamp': timestamp
        }
        
        with self._lock:
            self._user_events[user_id].append(user_event)
            self._add_to_batch('user_event', user_event)
    
    def track_business_metric(self, metric_name: str, value: float, dimensions: Optional[Dict[str, Any]] = None):
        """Track a business metric."""
        if not self.enabled:
            return
        
        business_metric = {
            'metric_name': metric_name,
            'value': value,
            'dimensions': dimensions or {},
            'timestamp': datetime.utcnow()
        }
        
        with self._lock:
            self._business_metrics[metric_name].append(business_metric)
            self._add_to_batch('business_metric', business_metric)
    
    def track_custom_event(self, event_name: str, event_data: Dict[str, Any],
                          timestamp: Optional[datetime] = None):
        """Track a custom event."""
        if not self.enabled:
            return
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        custom_event = {
            'event_name': event_name,
            'event_data': event_data,
            'timestamp': timestamp
        }
        
        with self._lock:
            self._custom_events[event_name].append(custom_event)
            self._add_to_batch('custom_event', custom_event)
    
    def get_request_stats(self, endpoint: str, start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None, status_codes: Optional[List[int]] = None) -> Dict[str, Any]:
        """Get request statistics for an endpoint."""
        with self._lock:
            requests = self._requests.get(endpoint, [])
        
        # Filter by time range
        if start_time or end_time:
            requests = [r for r in requests if self._is_in_time_range(r['timestamp'], start_time, end_time)]
        
        # Filter by status codes
        if status_codes:
            requests = [r for r in requests if r['status_code'] in status_codes]
        
        if not requests:
            return {
                'total_requests': 0,
                'avg_response_time': 0,
                'status_codes': {}
            }
        
        # Calculate statistics
        total_requests = len(requests)
        response_times = [r['response_time'] for r in requests]
        avg_response_time = sum(response_times) / len(response_times)
        
        # Status code distribution
        status_codes_count = defaultdict(int)
        for request in requests:
            status_codes_count[str(request['status_code'])] += 1
        
        return {
            'total_requests': total_requests,
            'avg_response_time': avg_response_time,
            'status_codes': dict(status_codes_count)
        }
    
    def get_performance_metrics(self, endpoint: str) -> Dict[str, Any]:
        """Get performance metrics for an endpoint."""
        with self._lock:
            requests = self._requests.get(endpoint, [])
        
        if not requests:
            return {
                'total_requests': 0,
                'avg_response_time': 0,
                'min_response_time': 0,
                'max_response_time': 0,
                'p95_response_time': 0,
                'p99_response_time': 0
            }
        
        response_times = [r['response_time'] for r in requests]
        response_times.sort()
        
        return {
            'total_requests': len(requests),
            'avg_response_time': statistics.mean(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'p95_response_time': self._percentile(response_times, 95),
            'p99_response_time': self._percentile(response_times, 99)
        }
    
    def get_error_stats(self, endpoint: str) -> Dict[str, Any]:
        """Get error statistics for an endpoint."""
        with self._lock:
            errors = self._errors.get(endpoint, [])
        
        if not errors:
            return {
                'total_errors': 0,
                'error_types': {}
            }
        
        # Error type distribution
        error_types_count = defaultdict(int)
        for error in errors:
            error_types_count[error['error_type']] += 1
        
        return {
            'total_errors': len(errors),
            'error_types': dict(error_types_count)
        }
    
    def get_error_rate(self, endpoint: str) -> float:
        """Get error rate for an endpoint."""
        with self._lock:
            errors = len(self._errors.get(endpoint, []))
            requests = len(self._requests.get(endpoint, []))
        
        total_events = errors + requests
        if total_events == 0:
            return 0.0
        
        return errors / total_events
    
    def get_user_behavior_stats(self) -> Dict[str, Any]:
        """Get user behavior statistics."""
        with self._lock:
            all_events = []
            for user_events in self._user_events.values():
                all_events.extend(user_events)
        
        if not all_events:
            return {
                'total_users': 0,
                'total_events': 0,
                'events_by_type': {}
            }
        
        # Event type distribution
        events_by_type = defaultdict(int)
        for event in all_events:
            events_by_type[event['event_type']] += 1
        
        return {
            'total_users': len(self._user_events),
            'total_events': len(all_events),
            'events_by_type': dict(events_by_type)
        }
    
    def get_user_events(self, user_id: str) -> List[Dict[str, Any]]:
        """Get events for a specific user."""
        with self._lock:
            return self._user_events.get(user_id, []).copy()
    
    def get_business_metrics(self) -> Dict[str, float]:
        """Get aggregated business metrics."""
        with self._lock:
            metrics = {}
            for metric_name, metric_list in self._business_metrics.items():
                metrics[metric_name] = sum(m['value'] for m in metric_list)
        
        return metrics
    
    def get_business_metric_by_dimension(self, metric_name: str, dimension: str) -> Dict[str, float]:
        """Get business metric aggregated by dimension."""
        with self._lock:
            metric_list = self._business_metrics.get(metric_name, [])
        
        dimension_values = defaultdict(float)
        for metric in metric_list:
            if dimension in metric['dimensions']:
                dimension_values[metric['dimensions'][dimension]] += metric['value']
        
        return dict(dimension_values)
    
    def get_custom_event_stats(self) -> Dict[str, Any]:
        """Get custom event statistics."""
        with self._lock:
            all_events = []
            for event_list in self._custom_events.values():
                all_events.extend(event_list)
        
        event_types = set(event['event_name'] for event in all_events)
        
        return {
            'total_events': len(all_events),
            'event_types': list(event_types)
        }
    
    def get_custom_events_by_type(self, event_name: str) -> List[Dict[str, Any]]:
        """Get custom events by type."""
        with self._lock:
            return self._custom_events.get(event_name, []).copy()
    
    def get_batch_count(self) -> int:
        """Get number of batches processed."""
        return self._batch_count
    
    def get_pending_events_count(self) -> int:
        """Get number of pending events."""
        with self._lock:
            return len(self._pending_events)
    
    def flush(self):
        """Flush pending analytics data."""
        with self._lock:
            self._flush_unlocked()
    
    def _flush_unlocked(self):
        """Flush pending analytics data without acquiring lock."""
        if self._pending_events:
            # In a real implementation, this would send data to external storage
            logger.info(f"Flushing {len(self._pending_events)} analytics events")
            self._pending_events.clear()
            self._batch_count += 1
    
    def _add_to_batch(self, event_type: str, event_data: Dict[str, Any]):
        """Add event to batch queue."""
        self._pending_events.append({
            'type': event_type,
            'data': event_data
        })
        
        if len(self._pending_events) >= self.batch_size:
            self._flush_unlocked()
    
    def _start_background_flush(self):
        """Start background flush timer."""
        def flush_periodically():
            while self.enabled and not self.config.get('TESTING', False):
                try:
                    time.sleep(self.flush_interval)
                    if self.enabled and not self.config.get('TESTING', False):  # Check again after sleep
                        self.flush()
                except Exception as e:
                    logger.error(f"Background flush error: {e}")
                    break
        
        self._background_thread = threading.Thread(target=flush_periodically, daemon=True)
        self._background_thread.start()
    
    def stop(self):
        """Stop analytics system and cleanup resources."""
        self.enabled = False
        if self._background_thread and self._background_thread.is_alive():
            self._background_thread.join(timeout=1.0)
    
    def _is_in_time_range(self, timestamp: datetime, start_time: Optional[datetime], 
                         end_time: Optional[datetime]) -> bool:
        """Check if timestamp is in specified time range."""
        if start_time and timestamp < start_time:
            return False
        if end_time and timestamp > end_time:
            return False
        return True
    
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