import pytest
from flask import Flask
from unittest.mock import Mock, patch, MagicMock
import json

from src.api.base import create_app, configure_cors, setup_error_handlers, setup_logging


class TestAPIBase:
    def test_flask_app_creation(self):
        app = create_app()
        assert isinstance(app, Flask)
        assert app.config['TESTING'] is False
        
    def test_flask_app_creation_with_test_config(self):
        app = create_app(testing=True)
        assert isinstance(app, Flask)
        assert app.config['TESTING'] is True
        
    def test_cors_configuration(self):
        app = Flask(__name__)
        configure_cors(app)
        
        # Test that CORS headers are properly set
        with app.test_client() as client:
            @app.route('/test')
            def test_route():
                return {'status': 'ok'}
                
            # CORS headers are only added for cross-origin requests
            response = client.get('/test', headers={'Origin': 'http://example.com'})
            assert 'Access-Control-Allow-Origin' in response.headers
            
    def test_error_handlers(self):
        app = Flask(__name__)
        setup_error_handlers(app)
        
        # Verify error handlers are registered
        assert 404 in app.error_handler_spec[None]
        assert 500 in app.error_handler_spec[None]
        assert 400 in app.error_handler_spec[None]
        assert 429 in app.error_handler_spec[None]
        
    def test_request_logging(self):
        app = create_app(testing=True)
        
        with app.test_client() as client:
            with patch('src.api.base.logger') as mock_logger:
                client.get('/api/v1/health')
                # Verify logging was called
                assert mock_logger.info.called
                
    def test_response_formatting(self):
        app = create_app(testing=True)
        
        @app.route('/test')
        def test_route():
            return {'data': 'test', 'status': 'success'}
            
        with app.test_client() as client:
            response = client.get('/test')
            data = json.loads(response.data)
            assert 'data' in data
            assert 'status' in data
            assert response.content_type == 'application/json'
            
    def test_health_check_endpoint(self):
        app = create_app(testing=True)
        
        with app.test_client() as client:
            response = client.get('/api/v1/health')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'healthy'
            assert 'timestamp' in data
            assert 'version' in data
            
    def test_metrics_endpoint(self):
        app = create_app(testing=True)
        
        with app.test_client() as client:
            response = client.get('/api/v1/metrics')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'uptime' in data
            assert 'requests_total' in data
            assert 'cache_hit_ratio' in data
            assert 'database_status' in data


class TestErrorHandling:
    def test_404_handler(self):
        app = create_app(testing=True)
        
        with app.test_client() as client:
            response = client.get('/non-existent-endpoint')
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['error'] == 'Not Found'
            assert 'message' in data
            
    def test_500_handler(self):
        app = create_app(testing=True)
        app.config['PROPAGATE_EXCEPTIONS'] = False  # Allow error handlers to work
        
        @app.route('/error')
        def error_route():
            raise Exception('Test error')
            
        with app.test_client() as client:
            response = client.get('/error')
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['error'] == 'Internal Server Error'
            
    def test_400_handler(self):
        app = create_app(testing=True)
        
        @app.route('/bad-request', methods=['POST'])
        def bad_request_route():
            from flask import request
            from werkzeug.exceptions import BadRequest
            data = request.get_json(force=True)
            if not data:
                raise BadRequest('Invalid JSON')
            return {'status': 'ok'}
            
        with app.test_client() as client:
            response = client.post('/bad-request', 
                                 data='invalid json',
                                 content_type='application/json')
            assert response.status_code == 400
            
    def test_429_rate_limit_handler(self):
        app = create_app(testing=True)
        
        # Mock rate limit error
        from werkzeug.exceptions import TooManyRequests
        
        @app.route('/rate-limited')
        def rate_limited_route():
            raise TooManyRequests('Rate limit exceeded')
            
        with app.test_client() as client:
            response = client.get('/rate-limited')
            assert response.status_code == 429
            data = json.loads(response.data)
            assert data['error'] == 'Too Many Requests'
            assert 'retry_after' in data
            
    def test_validation_error_handler(self):
        app = create_app(testing=True)
        
        @app.route('/validate', methods=['POST'])
        def validate_route():
            from src.api.exceptions import ValidationError
            raise ValidationError('Invalid input', field='city')
            
        with app.test_client() as client:
            response = client.post('/validate')
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['error'] == 'Validation Error'
            assert data['field'] == 'city'
            
    def test_database_error_handler(self):
        app = create_app(testing=True)
        
        @app.route('/db-error')
        def db_error_route():
            from src.api.exceptions import DatabaseError
            raise DatabaseError('Connection failed')
            
        with app.test_client() as client:
            response = client.get('/db-error')
            assert response.status_code == 503
            data = json.loads(response.data)
            assert data['error'] == 'Service Unavailable'
            assert 'message' in data