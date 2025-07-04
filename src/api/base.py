from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
import logging
import time
from datetime import datetime
import os

from src.config.settings import Config
from src.api.exceptions import ValidationError, DatabaseError
from src.security import SecurityMiddleware


logger = logging.getLogger(__name__)


def create_app(testing=False):
    app = Flask(__name__)
    
    # Load configuration
    if testing:
        app.config['TESTING'] = True
        app.config.from_object('src.config.settings.TestingConfig')
    else:
        app.config['TESTING'] = False
        app.config.from_object('src.config.settings.Config')
    
    # Setup components
    configure_cors(app)
    setup_security(app)
    setup_error_handlers(app)
    setup_logging(app)
    register_blueprints(app)
    setup_request_handlers(app)
    
    return app


def configure_cors(app):
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-API-Key"]
        }
    })


def setup_security(app):
    """Setup security middleware with default configuration."""
    # Default security configuration
    default_config = {
        'RATE_LIMIT_STORAGE': 'memory',
        'RATE_LIMIT_DEFAULT': '100/hour',
        'RATE_LIMIT_SEARCH': '50/hour',
        'RATE_LIMIT_ANALYSIS': '20/hour',
        'RATE_LIMIT_HISTORY': '30/hour',
        'RATE_LIMIT_STATS': '25/hour',
        'RATE_LIMIT_EXEMPT_IPS': ['127.0.0.1', '::1'],
        'API_KEYS': {
            'valid_key_123': {
                'name': 'Test App',
                'rate_limit': '1000/hour',
                'permissions': ['search', 'analysis', 'history']
            },
            'limited_key_456': {
                'name': 'Limited App',
                'rate_limit': '100/hour',
                'permissions': ['search']
            }
        }
    }
    
    # Update app config with security defaults if not set
    for key, value in default_config.items():
        if key not in app.config:
            app.config[key] = value
    
    # Initialize security middleware
    security_middleware = SecurityMiddleware(app)
    app.security_middleware = security_middleware


def setup_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found',
            'status_code': 404
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {str(error)}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred',
            'status_code': 500
        }), 500
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'error': 'Bad Request',
            'message': str(error),
            'status_code': 400
        }), 400
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({
            'error': 'Too Many Requests',
            'message': 'Rate limit exceeded',
            'retry_after': 60,
            'status_code': 429
        }), 429
    
    @app.errorhandler(ValidationError)
    def validation_error(error):
        response = {
            'error': 'Validation Error',
            'message': error.message if hasattr(error, 'message') else str(error),
            'status_code': 400
        }
        if hasattr(error, 'field'):
            response['field'] = error.field
        return jsonify(response), 400
    
    @app.errorhandler(DatabaseError)
    def database_error(error):
        logger.error(f"Database error: {str(error)}")
        return jsonify({
            'error': 'Service Unavailable',
            'message': 'Database service is temporarily unavailable',
            'status_code': 503
        }), 503


def setup_logging(app):
    if not app.debug and not app.testing:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Request logging
    @app.before_request
    def log_request():
        logger.info(f"{request.method} {request.path} - {request.remote_addr}")


def register_blueprints(app):
    # Register API routes
    from src.api.routes import api_v1
    app.register_blueprint(api_v1, url_prefix='/api/v1')


def setup_request_handlers(app):
    app.start_time = time.time()
    app.request_count = 0
    app.cache_hits = 0
    app.cache_total = 0
    
    @app.before_request
    def before_request():
        request.start_time = time.time()
        app.request_count += 1
    
    @app.after_request
    def after_request(response):
        # Add response time header
        if hasattr(request, 'start_time'):
            response_time = time.time() - request.start_time
            response.headers['X-Response-Time'] = f"{response_time:.3f}s"
        
        # Ensure JSON responses
        if response.content_type == 'application/json':
            # Already JSON
            pass
        elif hasattr(response, 'json'):
            # Convert to JSON if possible
            response.content_type = 'application/json'
        
        return response


# Health check endpoint
def register_health_check(app):
    @app.route('/api/v1/health')
    def health_check():
        uptime = time.time() - app.start_time
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'uptime_seconds': round(uptime, 2)
        })


# Metrics endpoint
def register_metrics(app):
    @app.route('/api/v1/metrics')
    def metrics():
        uptime = time.time() - app.start_time
        cache_hit_ratio = 0
        if app.cache_total > 0:
            cache_hit_ratio = app.cache_hits / app.cache_total
        
        return jsonify({
            'uptime': round(uptime, 2),
            'requests_total': app.request_count,
            'cache_hit_ratio': round(cache_hit_ratio, 3),
            'database_status': 'connected',  # TODO: Implement actual check
            'scrapers_status': 'operational',
            'memory_usage_mb': get_memory_usage(),
            'timestamp': datetime.utcnow().isoformat()
        })


def get_memory_usage():
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return round(process.memory_info().rss / 1024 / 1024, 2)
    except:
        return 0