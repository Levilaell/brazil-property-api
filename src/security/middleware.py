"""
Security middleware for the Brazil Property API.
"""
import logging
import time
from functools import wraps
from typing import Dict, Any, Optional

from flask import request, jsonify, current_app

from src.security.rate_limiting import RateLimiter, APIKeyManager, get_client_ip, extract_api_key
from src.security.input_validation import InputValidator, SecurityValidator
from src.security.exceptions import (
    RateLimitExceeded, InvalidAPIKey, SecurityViolation, 
    InvalidInput, AccessDenied, SuspiciousActivity
)


logger = logging.getLogger(__name__)
security_logger = logging.getLogger('security')


class SecurityMiddleware:
    """Security middleware for Flask application."""
    
    def __init__(self, app=None, config: Optional[Dict[str, Any]] = None):
        self.app = app
        self.config = config or {}
        
        # Initialize security components
        self.rate_limiter = None
        self.api_key_manager = None
        self.input_validator = InputValidator()
        self.security_validator = SecurityValidator()
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security middleware with Flask app."""
        self.app = app
        self.config.update(app.config)
        
        # Initialize rate limiter and API key manager
        self.rate_limiter = RateLimiter(self.config)
        self.api_key_manager = APIKeyManager(self.config)
        
        # Register error handlers
        self._register_error_handlers(app)
        
        # Register before_request handlers
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        
        logger.info("SecurityMiddleware initialized")
    
    def _register_error_handlers(self, app):
        """Register security-related error handlers."""
        
        @app.errorhandler(RateLimitExceeded)
        def handle_rate_limit_exceeded(error):
            response = jsonify({
                'error': 'Rate Limit Exceeded',
                'message': str(error),
                'status_code': 429
            })
            response.status_code = 429
            response.headers['Retry-After'] = str(getattr(error, 'retry_after', 3600))
            return response
        
        @app.errorhandler(InvalidAPIKey)
        def handle_invalid_api_key(error):
            return jsonify({
                'error': 'Invalid API Key',
                'message': str(error),
                'status_code': 401
            }), 401
        
        @app.errorhandler(SecurityViolation)
        def handle_security_violation(error):
            # Log security violation
            security_logger.warning(f"Security violation: {error} - IP: {get_client_ip(request)}")
            
            return jsonify({
                'error': 'Security Violation',
                'message': 'Request blocked for security reasons',
                'status_code': 403
            }), 403
        
        @app.errorhandler(AccessDenied)
        def handle_access_denied(error):
            return jsonify({
                'error': 'Access Denied',
                'message': str(error),
                'status_code': 403
            }), 403
        
        @app.errorhandler(413)
        def handle_request_too_large(error):
            return jsonify({
                'error': 'Request Too Large',
                'message': 'Request payload too large',
                'status_code': 413
            }), 413
    
    def _before_request(self):
        """Security checks before each request."""
        try:
            # Get client information
            client_ip = get_client_ip(request)
            user_agent = request.headers.get('User-Agent', '')
            api_key = extract_api_key(request)
            
            # Check if IP is blocked
            if self.security_validator.is_blocked_ip(client_ip):
                raise AccessDenied("IP address is blocked")
            
            # Check for suspicious user agent
            if self.security_validator.is_suspicious_user_agent(user_agent):
                security_logger.warning(f"Suspicious user agent: {user_agent} - IP: {client_ip}")
                # Don't block immediately, just log
            
            # Check request size
            content_length = request.content_length or 0
            if not self.security_validator.validate_request_size(content_length):
                raise InvalidInput("Request too large")
            
            # Rate limiting check
            endpoint = request.endpoint or request.path
            
            # Skip rate limiting for health checks and static files
            if self._should_skip_rate_limiting(endpoint):
                return
            
            # Check API key rate limits
            if api_key:
                if not self.api_key_manager.is_valid_key(api_key):
                    raise InvalidAPIKey("Invalid API key")
                
                if self.api_key_manager.is_rate_limited(api_key, endpoint):
                    raise RateLimitExceeded("API key rate limit exceeded")
                
                # Check permissions
                permission = self._get_required_permission(endpoint)
                if permission and not self.api_key_manager.has_permission(api_key, permission):
                    raise AccessDenied(f"API key does not have {permission} permission")
            
            # Check IP-based rate limits
            elif not self.rate_limiter.is_allowed(client_ip, endpoint):
                raise RateLimitExceeded("Rate limit exceeded")
            
            # Validate request parameters
            if request.method in ['GET', 'POST'] and request.args:
                self._validate_request_parameters(request.args)
            
            # Validate JSON payload for POST requests
            if request.method == 'POST' and request.is_json:
                try:
                    json_data = request.get_json()
                    if json_data:
                        self.input_validator.validate_json_payload(json_data)
                except Exception as e:
                    raise InvalidInput(f"Invalid JSON payload: {str(e)}")
            
        except Exception as e:
            # Log the security event
            security_logger.warning(f"Security check failed: {e} - IP: {client_ip} - Endpoint: {request.endpoint}")
            raise
    
    def _after_request(self, response):
        """Add security headers and record usage after request."""
        try:
            # Add security headers
            self._add_security_headers(response)
            
            # Record usage for rate limiting
            client_ip = get_client_ip(request)
            api_key = extract_api_key(request)
            endpoint = request.endpoint or request.path
            
            if not self._should_skip_rate_limiting(endpoint):
                if api_key and self.api_key_manager.is_valid_key(api_key):
                    self.api_key_manager.record_usage(api_key, endpoint)
                    
                    # Add API key rate limit headers
                    limit = self.api_key_manager.get_rate_limit(api_key)
                    remaining = max(0, limit - self.api_key_manager.get_usage(api_key, endpoint))
                    
                    response.headers['X-RateLimit-Limit'] = str(limit)
                    response.headers['X-RateLimit-Remaining'] = str(remaining)
                    response.headers['X-RateLimit-Reset'] = str(int(time.time()) + 3600)
                else:
                    self.rate_limiter.record_request(client_ip, endpoint)
                    
                    # Add IP rate limit headers
                    limit = self.rate_limiter.get_endpoint_limit(endpoint)
                    remaining = self.rate_limiter.get_remaining_requests(client_ip, endpoint)
                    
                    response.headers['X-RateLimit-Limit'] = str(limit)
                    response.headers['X-RateLimit-Remaining'] = str(remaining)
                    response.headers['X-RateLimit-Reset'] = str(int(time.time()) + 3600)
            
        except Exception as e:
            logger.error(f"Error in after_request security middleware: {e}")
        
        return response
    
    def _add_security_headers(self, response):
        """Add security headers to response."""
        # Content Security Policy
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        
        # Other security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=();"
        )
        
        # HSTS (only for HTTPS)
        if request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Hide server information
        response.headers.pop('Server', None)
        
        # Cache control for security
        if 'Cache-Control' not in response.headers:
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
    
    def _should_skip_rate_limiting(self, endpoint: str) -> bool:
        """Check if endpoint should skip rate limiting."""
        skip_endpoints = [
            '/health',
            '/metrics',
            '/static/',
            '/favicon.ico'
        ]
        
        return any(skip in (endpoint or '') for skip in skip_endpoints)
    
    def _get_required_permission(self, endpoint: str) -> Optional[str]:
        """Get required permission for endpoint."""
        permission_map = {
            '/api/v1/search': 'search',
            '/api/v1/market-analysis': 'analysis',
            '/api/v1/price-history': 'history',
            '/api/v1/neighborhood-stats': 'stats'
        }
        
        return permission_map.get(endpoint)
    
    def _validate_request_parameters(self, args):
        """Validate request parameters."""
        for key, value in args.items():
            try:
                # Basic validation for common parameters
                if key in ['city', 'neighborhood']:
                    self.input_validator.validate_search_query(value)
                elif key in ['min_price', 'max_price', 'bedrooms']:
                    # Validate numeric parameters
                    if not value.isdigit() and not (value.startswith('-') and value[1:].isdigit()):
                        raise InvalidInput(f"Parameter {key} must be a number")
            except Exception as e:
                raise InvalidInput(f"Invalid parameter {key}: {str(e)}")


# Decorator functions for easy use
def require_api_key(permission: Optional[str] = None):
    """Decorator to require API key authentication."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            api_key = extract_api_key(request)
            
            if not api_key:
                raise InvalidAPIKey("API key required")
            
            # Get security middleware from app
            security_middleware = getattr(current_app, 'security_middleware', None)
            if not security_middleware:
                raise InvalidAPIKey("Security not configured")
            
            api_key_manager = security_middleware.api_key_manager
            
            if not api_key_manager.is_valid_key(api_key):
                raise InvalidAPIKey("Invalid API key")
            
            if permission and not api_key_manager.has_permission(api_key, permission):
                raise AccessDenied(f"API key does not have {permission} permission")
            
            return f(*args, **kwargs)
        
        return wrapper
    return decorator


def rate_limit(limit: Optional[int] = None):
    """Decorator for custom rate limiting."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Rate limiting is handled by middleware
            # This decorator is mainly for custom limits
            return f(*args, **kwargs)
        
        return wrapper
    return decorator


# Global security functions
def is_blocked_ip(ip_address: str) -> bool:
    """Check if IP is blocked globally."""
    # This could check a database or cache
    return False


def detect_suspicious_pattern(ip_address: str) -> bool:
    """Detect suspicious patterns globally."""
    # This could implement more sophisticated detection
    return False