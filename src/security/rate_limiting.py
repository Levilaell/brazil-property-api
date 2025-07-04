"""
Rate limiting system for API endpoints.
"""
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from collections import defaultdict
import hashlib

from src.security.exceptions import RateLimitExceeded, InvalidAPIKey


logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiting system with sliding window implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.storage_type = config.get('RATE_LIMIT_STORAGE', 'memory')
        
        # In-memory storage for rate limiting
        self._requests = defaultdict(list)  # ip -> [timestamp, timestamp, ...]
        self._endpoint_limits = {}
        
        # Default rate limits
        self.default_limit = self._parse_limit(config.get('RATE_LIMIT_DEFAULT', '100/hour'))
        
        # Endpoint-specific limits
        self._setup_endpoint_limits()
        
        # Exempt IPs (localhost, etc.)
        self.exempt_ips = config.get('RATE_LIMIT_EXEMPT_IPS', ['127.0.0.1', '::1'])
        
        logger.info(f"RateLimiter initialized with {self.storage_type} storage")
    
    def _setup_endpoint_limits(self):
        """Setup endpoint-specific rate limits."""
        endpoint_configs = {
            '/api/v1/search': self.config.get('RATE_LIMIT_SEARCH', '50/hour'),
            '/api/v1/market-analysis': self.config.get('RATE_LIMIT_ANALYSIS', '20/hour'),
            '/api/v1/price-history': self.config.get('RATE_LIMIT_HISTORY', '30/hour'),
            '/api/v1/neighborhood-stats': self.config.get('RATE_LIMIT_STATS', '25/hour')
        }
        
        for endpoint, limit_str in endpoint_configs.items():
            self._endpoint_limits[endpoint] = self._parse_limit(limit_str)
    
    def _parse_limit(self, limit_str: str) -> int:
        """Parse rate limit string like '100/hour' to requests per hour."""
        if '/' not in limit_str:
            return int(limit_str)
        
        rate, period = limit_str.split('/')
        rate = int(rate)
        
        if period.startswith('sec'):
            return rate * 3600  # Convert to per hour
        elif period.startswith('min'):
            return rate * 60  # Convert to per hour
        elif period.startswith('hour'):
            return rate
        elif period.startswith('day'):
            return rate // 24  # Convert to per hour
        else:
            return rate
    
    def is_exempt(self, ip_address: str) -> bool:
        """Check if IP address is exempt from rate limiting."""
        return ip_address in self.exempt_ips
    
    def is_allowed(self, ip_address: str, endpoint: str) -> bool:
        """Check if request is allowed based on rate limits."""
        if self.is_exempt(ip_address):
            return True
        
        current_usage = self._get_current_usage(ip_address, endpoint)
        limit = self.get_endpoint_limit(endpoint)
        
        return current_usage < limit
    
    def record_request(self, ip_address: str, endpoint: str, timestamp: Optional[datetime] = None):
        """Record a request for rate limiting."""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        key = self._get_key(ip_address, endpoint)
        self._requests[key].append(timestamp)
        
        # Clean old requests outside the window
        self._clean_old_requests(key)
    
    def get_endpoint_limit(self, endpoint: str) -> int:
        """Get rate limit for specific endpoint."""
        return self._endpoint_limits.get(endpoint, self.default_limit)
    
    def set_endpoint_limit(self, endpoint: str, limit: int):
        """Set custom rate limit for endpoint."""
        self._endpoint_limits[endpoint] = limit
    
    def get_current_usage(self, ip_address: str, endpoint: str) -> int:
        """Get current usage count for IP and endpoint."""
        return self._get_current_usage(ip_address, endpoint)
    
    def _get_current_usage(self, ip_address: str, endpoint: str) -> int:
        """Internal method to get current usage."""
        key = self._get_key(ip_address, endpoint)
        self._clean_old_requests(key)
        return len(self._requests[key])
    
    def get_remaining_requests(self, ip_address: str, endpoint: str) -> int:
        """Get remaining requests for IP and endpoint."""
        current = self.get_current_usage(ip_address, endpoint)
        limit = self.get_endpoint_limit(endpoint)
        return max(0, limit - current)
    
    def get_reset_time(self, ip_address: str, endpoint: str) -> datetime:
        """Get when rate limit resets."""
        key = self._get_key(ip_address, endpoint)
        requests = self._requests[key]
        
        if not requests:
            return datetime.utcnow()
        
        # Find oldest request in current window
        oldest = min(requests)
        return oldest + timedelta(hours=1)
    
    def reset_limits(self, ip_address: str, endpoint: Optional[str] = None):
        """Reset rate limits for IP (and optionally specific endpoint)."""
        if endpoint:
            key = self._get_key(ip_address, endpoint)
            self._requests[key] = []
        else:
            # Reset all endpoints for this IP
            keys_to_reset = [k for k in self._requests.keys() if k.startswith(f"{ip_address}:")]
            for key in keys_to_reset:
                self._requests[key] = []
    
    def _get_key(self, ip_address: str, endpoint: str) -> str:
        """Generate cache key for IP and endpoint."""
        return f"{ip_address}:{endpoint}"
    
    def _clean_old_requests(self, key: str):
        """Remove requests older than the time window."""
        cutoff = datetime.utcnow() - timedelta(hours=1)
        self._requests[key] = [req for req in self._requests[key] if req > cutoff]


class APIKeyManager:
    """API key authentication and management."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_keys = config.get('API_KEYS', {})
        
        # Usage tracking
        self._usage = defaultdict(lambda: defaultdict(int))  # api_key -> endpoint -> count
        self._usage_timestamps = defaultdict(lambda: defaultdict(list))  # api_key -> endpoint -> [timestamps]
        
        logger.info(f"APIKeyManager initialized with {len(self.api_keys)} keys")
    
    def is_valid_key(self, api_key: str) -> bool:
        """Check if API key is valid."""
        return api_key in self.api_keys
    
    def get_key_info(self, api_key: str) -> Dict[str, Any]:
        """Get API key information."""
        if not self.is_valid_key(api_key):
            raise InvalidAPIKey(f"Invalid API key: {api_key}")
        
        return self.api_keys[api_key].copy()
    
    def get_rate_limit(self, api_key: str) -> int:
        """Get rate limit for API key."""
        if not self.is_valid_key(api_key):
            return 100  # Default limit for invalid keys
        
        key_info = self.api_keys[api_key]
        limit_str = key_info.get('rate_limit', '100/hour')
        
        return self._parse_limit(limit_str)
    
    def has_permission(self, api_key: str, permission: str) -> bool:
        """Check if API key has specific permission."""
        if not self.is_valid_key(api_key):
            return False
        
        key_info = self.api_keys[api_key]
        permissions = key_info.get('permissions', [])
        
        return permission in permissions
    
    def record_usage(self, api_key: str, endpoint: str, timestamp: Optional[datetime] = None):
        """Record API key usage."""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        self._usage[api_key][endpoint] += 1
        self._usage_timestamps[api_key][endpoint].append(timestamp)
        
        # Clean old timestamps
        self._clean_old_usage(api_key, endpoint)
    
    def get_usage(self, api_key: str, endpoint: str) -> int:
        """Get current usage for API key and endpoint."""
        self._clean_old_usage(api_key, endpoint)
        return len(self._usage_timestamps[api_key][endpoint])
    
    def is_rate_limited(self, api_key: str, endpoint: str) -> bool:
        """Check if API key is rate limited."""
        current_usage = self.get_usage(api_key, endpoint)
        limit = self.get_rate_limit(api_key)
        
        return current_usage >= limit
    
    def _parse_limit(self, limit_str: str) -> int:
        """Parse rate limit string."""
        if '/' not in limit_str:
            return int(limit_str)
        
        rate, period = limit_str.split('/')
        rate = int(rate)
        
        # For simplicity, return the rate as is (assuming per hour)
        return rate
    
    def _clean_old_usage(self, api_key: str, endpoint: str):
        """Clean old usage timestamps outside the window."""
        cutoff = datetime.utcnow() - timedelta(hours=1)
        timestamps = self._usage_timestamps[api_key][endpoint]
        self._usage_timestamps[api_key][endpoint] = [t for t in timestamps if t > cutoff]


def get_client_ip(request) -> str:
    """Extract client IP from request, considering proxies."""
    # Check X-Forwarded-For header first
    if request.headers.get('X-Forwarded-For'):
        # Take the first IP in the chain
        ips = request.headers['X-Forwarded-For'].split(',')
        return ips[0].strip()
    
    # Check other common headers
    headers_to_check = [
        'X-Real-IP',
        'X-Originating-IP',
        'CF-Connecting-IP',
        'True-Client-IP'
    ]
    
    for header in headers_to_check:
        if request.headers.get(header):
            return request.headers[header].strip()
    
    # Fall back to remote_addr
    return request.remote_addr or '127.0.0.1'


def extract_api_key(request) -> Optional[str]:
    """Extract API key from request headers or query parameters."""
    # Check Authorization header
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]  # Remove 'Bearer ' prefix
    
    # Check X-API-Key header
    api_key = request.headers.get('X-API-Key')
    if api_key:
        return api_key
    
    # Check query parameter
    api_key = request.args.get('api_key')
    if api_key:
        return api_key
    
    return None


def rate_limit_decorator(rate_limiter: RateLimiter, api_key_manager: APIKeyManager):
    """Decorator for rate limiting endpoints."""
    def decorator(f):
        def wrapper(*args, **kwargs):
            from flask import request, jsonify
            
            # Get client IP and API key
            client_ip = get_client_ip(request)
            api_key = extract_api_key(request)
            endpoint = request.endpoint or request.path
            
            # Check API key rate limits first
            if api_key and api_key_manager.is_valid_key(api_key):
                if api_key_manager.is_rate_limited(api_key, endpoint):
                    raise RateLimitExceeded("API key rate limit exceeded")
                api_key_manager.record_usage(api_key, endpoint)
            else:
                # Check IP-based rate limits
                if not rate_limiter.is_allowed(client_ip, endpoint):
                    raise RateLimitExceeded("Rate limit exceeded")
                rate_limiter.record_request(client_ip, endpoint)
            
            # Add rate limit headers to response
            response = f(*args, **kwargs)
            
            # Add rate limit headers
            if api_key and api_key_manager.is_valid_key(api_key):
                limit = api_key_manager.get_rate_limit(api_key)
                remaining = max(0, limit - api_key_manager.get_usage(api_key, endpoint))
            else:
                limit = rate_limiter.get_endpoint_limit(endpoint)
                remaining = rate_limiter.get_remaining_requests(client_ip, endpoint)
            
            response.headers['X-RateLimit-Limit'] = str(limit)
            response.headers['X-RateLimit-Remaining'] = str(remaining)
            response.headers['X-RateLimit-Reset'] = str(int(time.time()) + 3600)
            
            return response
        
        return wrapper
    return decorator