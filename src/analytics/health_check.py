"""
Health check system for the Brazil Property API.
"""
import logging
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from collections import defaultdict
import threading

from src.analytics.exceptions import HealthCheckError


logger = logging.getLogger(__name__)


@dataclass
class ComponentHealth:
    """Health status of a system component."""
    component: str
    status: str  # 'healthy', 'degraded', 'unhealthy'
    details: Dict[str, Any]
    error_message: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class HealthChecker:
    """Health check system for monitoring system components."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('HEALTH_CHECK_ENABLED', True)
        self.timeout = config.get('HEALTH_CHECK_TIMEOUT', 5)
        self.cache_ttl = config.get('HEALTH_CHECK_CACHE_TTL', 60)
        self.components = config.get('HEALTH_CHECK_COMPONENTS', ['database', 'cache', 'scrapers'])
        
        # Health check cache
        self._health_cache = {}
        self._cache_timestamps = {}
        
        # Health history tracking
        self._health_history = defaultdict(list)
        self._history_enabled = False
        
        # Alert thresholds
        self._alert_thresholds = {}
        self._active_alerts = []
        
        # Component dependencies
        self._component_dependencies = {}
        
        self._lock = threading.Lock()
        
        logger.info("HealthChecker initialized")
    
    def check_database_health(self) -> ComponentHealth:
        """Check database health."""
        if not self.enabled:
            return ComponentHealth('database', 'unknown', {})
        
        try:
            from src.database import MongoDBHandler
            
            # Create database handler
            db_handler = MongoDBHandler(self.config)
            
            # Test connection with timeout
            start_time = time.time()
            
            # Use a timeout mechanism
            result = self._execute_with_timeout(
                lambda: db_handler.ping(),
                self.timeout
            )
            
            if not result:
                raise Exception("Database ping failed")
            
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Get additional connection stats
            try:
                connection_stats = db_handler.get_connection_stats()
            except:
                connection_stats = {
                    'active_connections': 'unknown',
                    'max_connections': 'unknown'
                }
            
            details = {
                'response_time_ms': response_time,
                **connection_stats
            }
            
            # Check if response time exceeds threshold
            threshold = self._alert_thresholds.get('database_response_time_ms')
            if threshold and response_time > threshold:
                self._add_alert('database_response_time_ms', response_time, threshold)
            
            health_status = ComponentHealth('database', 'healthy', details)
            
        except Exception as e:
            error_msg = str(e)
            if 'timeout' in error_msg.lower():
                error_msg = f"Database health check timeout after {self.timeout}s"
            
            health_status = ComponentHealth('database', 'unhealthy', {}, error_msg)
        
        # Add to history if enabled
        if self._history_enabled:
            with self._lock:
                self._health_history['database'].append(health_status)
        
        return health_status
    
    def check_cache_health(self) -> ComponentHealth:
        """Check cache health."""
        if not self.enabled:
            return ComponentHealth('cache', 'unknown', {})
        
        try:
            from src.cache import CacheManager
            
            # Create cache manager
            cache_manager = CacheManager(self.config)
            
            # Execute health check with timeout
            health_result = self._execute_with_timeout(
                lambda: cache_manager.health_check(),
                self.timeout
            )
            
            if not health_result:
                raise Exception("Cache health check failed")
            
            # Check cache-specific thresholds
            memory_usage = health_result.get('memory_usage_mb', 0)
            hit_ratio = health_result.get('hit_ratio', 0)
            
            memory_threshold = self._alert_thresholds.get('cache_memory_usage_mb')
            if memory_threshold and memory_usage > memory_threshold:
                self._add_alert('cache_memory_usage_mb', memory_usage, memory_threshold)
            
            hit_ratio_threshold = self._alert_thresholds.get('cache_hit_ratio')
            if hit_ratio_threshold and hit_ratio < hit_ratio_threshold:
                self._add_alert('cache_hit_ratio', hit_ratio, hit_ratio_threshold)
            
            health_status = ComponentHealth('cache', 'healthy', health_result)
            
        except Exception as e:
            error_msg = str(e)
            if 'timeout' in error_msg.lower():
                error_msg = f"Cache health check timeout after {self.timeout}s"
            
            health_status = ComponentHealth('cache', 'unhealthy', {}, error_msg)
        
        # Add to history if enabled
        if self._history_enabled:
            with self._lock:
                self._health_history['cache'].append(health_status)
        
        return health_status
    
    def check_external_services_health(self) -> ComponentHealth:
        """Check external services health."""
        if not self.enabled:
            return ComponentHealth('external_services', 'unknown', {})
        
        services_status = {}
        overall_status = 'healthy'
        
        # List of external services to check
        external_services = {
            'zap': 'https://www.zapimoveis.com.br',
            'vivareal': 'https://www.vivareal.com.br'
        }
        
        for service_name, service_url in external_services.items():
            try:
                response = requests.get(service_url, timeout=self.timeout)
                
                services_status[service_name] = {
                    'status': 'healthy' if response.status_code == 200 else 'degraded',
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds()
                }
                
                if response.status_code != 200:
                    overall_status = 'degraded'
                    
            except Exception as e:
                services_status[service_name] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                overall_status = 'degraded'  # Not completely unhealthy, as other services might work
        
        health_status = ComponentHealth('external_services', overall_status, services_status)
        
        # Add to history if enabled
        if self._history_enabled:
            with self._lock:
                self._health_history['external_services'].append(health_status)
        
        return health_status
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        components_health = []
        overall_status = 'healthy'
        
        # Check all configured components
        if 'database' in self.components:
            db_health = self.check_database_health()
            components_health.append({
                'component': db_health.component,
                'status': db_health.status,
                'details': db_health.details,
                'error_message': db_health.error_message
            })
            
            if db_health.status == 'unhealthy':
                overall_status = 'degraded'
            elif db_health.status == 'degraded' and overall_status == 'healthy':
                overall_status = 'degraded'
        
        if 'cache' in self.components:
            cache_health = self.check_cache_health()
            components_health.append({
                'component': cache_health.component,
                'status': cache_health.status,
                'details': cache_health.details,
                'error_message': cache_health.error_message
            })
            
            if cache_health.status == 'unhealthy':
                overall_status = 'degraded'
            elif cache_health.status == 'degraded' and overall_status == 'healthy':
                overall_status = 'degraded'
        
        if 'external_services' in self.components:
            services_health = self.check_external_services_health()
            components_health.append({
                'component': services_health.component,
                'status': services_health.status,
                'details': services_health.details,
                'error_message': services_health.error_message
            })
            
            if services_health.status == 'degraded' and overall_status == 'healthy':
                overall_status = 'degraded'
        
        return {
            'status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'components': components_health
        }
    
    def get_cached_health_check(self, component: str, force_refresh: bool = False) -> ComponentHealth:
        """Get cached health check result for a component."""
        current_time = datetime.utcnow()
        
        # Check if we have a valid cached result
        if not force_refresh and component in self._health_cache:
            cache_time = self._cache_timestamps.get(component)
            if cache_time and (current_time - cache_time).total_seconds() < self.cache_ttl:
                return self._health_cache[component]
        
        # Perform fresh health check
        if component == 'database':
            health_result = self.check_database_health()
        elif component == 'cache':
            health_result = self.check_cache_health()
        elif component == 'external_services':
            health_result = self.check_external_services_health()
        else:
            raise HealthCheckError(f"Unknown component: {component}")
        
        # Cache the result
        self._health_cache[component] = health_result
        self._cache_timestamps[component] = current_time
        
        return health_result
    
    def get_detailed_health_info(self) -> Dict[str, Any]:
        """Get detailed health information for all components."""
        detailed_info = {}
        
        # Database details
        try:
            db_health = self.check_database_health()
            detailed_info['database'] = db_health.details
        except Exception as e:
            detailed_info['database'] = {'error': str(e)}
        
        # Cache details
        try:
            cache_health = self.check_cache_health()
            detailed_info['cache'] = cache_health.details
        except Exception as e:
            detailed_info['cache'] = {'error': str(e)}
        
        # External services details
        try:
            services_health = self.check_external_services_health()
            detailed_info['external_services'] = services_health.details
        except Exception as e:
            detailed_info['external_services'] = {'error': str(e)}
        
        # System information
        detailed_info['system'] = {
            'timestamp': datetime.utcnow().isoformat(),
            'health_check_version': '1.0.0',
            'uptime_seconds': time.time() - getattr(self, '_start_time', time.time())
        }
        
        return detailed_info
    
    def set_alert_thresholds(self, thresholds: Dict[str, float]):
        """Set alert thresholds for health metrics."""
        self._alert_thresholds.update(thresholds)
    
    def get_health_alerts(self) -> List[Dict[str, Any]]:
        """Get active health alerts."""
        with self._lock:
            return self._active_alerts.copy()
    
    def enable_history_tracking(self):
        """Enable health check history tracking."""
        self._history_enabled = True
    
    def get_health_history(self, component: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get health check history for a component."""
        if not self._history_enabled:
            return []
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        with self._lock:
            component_history = self._health_history.get(component, [])
        
        # Filter by time and format for output
        recent_history = [
            {
                'status': health.status,
                'timestamp': health.timestamp.isoformat(),
                'error_message': health.error_message
            }
            for health in component_history
            if health.timestamp >= cutoff_time
        ]
        
        return recent_history
    
    def get_health_trends(self, component: str) -> Dict[str, Any]:
        """Get health trends for a component."""
        if not self._history_enabled:
            return {}
        
        with self._lock:
            component_history = self._health_history.get(component, [])
        
        if not component_history:
            return {}
        
        # Calculate uptime percentage
        total_checks = len(component_history)
        healthy_checks = sum(1 for h in component_history if h.status == 'healthy')
        uptime_percentage = (healthy_checks / total_checks) * 100 if total_checks > 0 else 0
        
        # Count status changes
        status_changes = 0
        for i in range(1, len(component_history)):
            if component_history[i].status != component_history[i-1].status:
                status_changes += 1
        
        return {
            'avg_uptime_percentage': uptime_percentage,
            'total_checks': total_checks,
            'status_changes': status_changes,
            'current_status': component_history[-1].status if component_history else 'unknown'
        }
    
    def calculate_health_score(self, component_health: ComponentHealth) -> int:
        """Calculate a health score (0-100) for a component."""
        if component_health.status == 'healthy':
            base_score = 100
        elif component_health.status == 'degraded':
            base_score = 60
        else:  # unhealthy
            base_score = 0
        
        # Adjust score based on response time (if available)
        response_time = component_health.details.get('response_time_ms', 0)
        if response_time > 0:
            if response_time < 50:
                response_modifier = 0
            elif response_time < 100:
                response_modifier = -10
            elif response_time < 500:
                response_modifier = -20
            else:
                response_modifier = -40
            
            base_score = max(0, base_score + response_modifier)
        
        return base_score
    
    def set_component_dependencies(self, dependencies: Dict[str, List[str]]):
        """Set component dependencies."""
        self._component_dependencies = dependencies
    
    def check_dependent_component_health(self, component: str) -> ComponentHealth:
        """Check health of a component considering its dependencies."""
        dependencies = self._component_dependencies.get(component, [])
        
        if not dependencies:
            # No dependencies, return healthy
            return ComponentHealth(component, 'healthy', {})
        
        dependency_statuses = []
        for dependency in dependencies:
            dep_health = self.get_cached_health_check(dependency)
            dependency_statuses.append(dep_health.status)
        
        # Determine overall status based on dependencies
        if all(status == 'healthy' for status in dependency_statuses):
            overall_status = 'healthy'
        elif any(status == 'unhealthy' for status in dependency_statuses):
            if len([s for s in dependency_statuses if s == 'unhealthy']) == len(dependency_statuses):
                overall_status = 'unhealthy'
            else:
                overall_status = 'degraded'
        else:
            overall_status = 'degraded'
        
        return ComponentHealth(
            component,
            overall_status,
            {'dependencies': dependencies, 'dependency_statuses': dependency_statuses}
        )
    
    def _execute_with_timeout(self, func, timeout_seconds: int):
        """Execute a function with timeout."""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")
        
        # Set the timeout (signal.alarm expects integer seconds)
        timeout_int = max(1, int(timeout_seconds))  # At least 1 second
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_int)
        
        try:
            result = func()
            signal.alarm(0)  # Cancel the alarm
            return result
        except TimeoutError:
            raise
        finally:
            signal.signal(signal.SIGALRM, old_handler)
    
    def _add_alert(self, metric: str, value: float, threshold: float):
        """Add an alert for a metric threshold violation."""
        alert = {
            'metric': metric,
            'value': value,
            'threshold': threshold,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        with self._lock:
            self._active_alerts.append(alert)