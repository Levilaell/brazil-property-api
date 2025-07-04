from flask import Blueprint, jsonify
from src.api.base import register_health_check, register_metrics
from datetime import datetime

# Create the API blueprint
api_v1 = Blueprint('api_v1', __name__)

# Test endpoint
@api_v1.route('/test')
def test_endpoint():
    return jsonify({
        'message': 'Test endpoint working!',
        'api': 'Brazil Property API',
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'success'
    })

# Register base endpoints
@api_v1.route('/health')
def health():
    from flask import current_app, jsonify
    from datetime import datetime
    import time
    
    uptime = time.time() - current_app.start_time
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
        'uptime_seconds': round(uptime, 2)
    })

@api_v1.route('/metrics')
def metrics():
    from flask import current_app, jsonify
    from datetime import datetime
    import time
    
    uptime = time.time() - current_app.start_time
    cache_hit_ratio = 0
    if current_app.cache_total > 0:
        cache_hit_ratio = current_app.cache_hits / current_app.cache_total
    
    return jsonify({
        'uptime': round(uptime, 2),
        'requests_total': current_app.request_count,
        'cache_hit_ratio': round(cache_hit_ratio, 3),
        'database_status': 'connected',
        'scrapers_status': 'operational',
        'memory_usage_mb': 0,  # TODO: Implement
        'timestamp': datetime.utcnow().isoformat()
    })

# Import and register endpoint blueprints
from src.api.endpoints.search import search_bp
from src.api.endpoints.price_history import price_history_bp
from src.api.endpoints.market_analysis import market_analysis_bp
from src.api.endpoints.neighborhood_stats import neighborhood_stats_bp

api_v1.register_blueprint(search_bp)
api_v1.register_blueprint(price_history_bp)
api_v1.register_blueprint(market_analysis_bp)
api_v1.register_blueprint(neighborhood_stats_bp)

# Demo endpoint that works without database
@api_v1.route('/demo/search')
def demo_search():
    """Demo search endpoint with fake data."""
    from flask import request
    
    city = request.args.get('city', 'São Paulo')
    
    # Fake property data
    fake_properties = [
        {
            "id": "demo_001",
            "title": f"Apartamento em {city}",
            "price": 450000,
            "size": 85,
            "bedrooms": 2,
            "bathrooms": 2,
            "city": city,
            "neighborhood": "Centro",
            "type": "apartment",
            "url": "https://demo.com/property/001"
        },
        {
            "id": "demo_002", 
            "title": f"Casa em {city}",
            "price": 650000,
            "size": 120,
            "bedrooms": 3,
            "bathrooms": 2,
            "city": city,
            "neighborhood": "Zona Sul",
            "type": "house",
            "url": "https://demo.com/property/002"
        },
        {
            "id": "demo_003",
            "title": f"Cobertura em {city}",
            "price": 890000,
            "size": 150,
            "bedrooms": 3,
            "bathrooms": 3,
            "city": city,
            "neighborhood": "Barra",
            "type": "apartment",
            "url": "https://demo.com/property/003"
        }
    ]
    
    return jsonify({
        'status': 'success',
        'data': {
            'properties': fake_properties,
            'total': len(fake_properties),
            'page': 1,
            'per_page': 20,
            'city': city,
            'generated_at': datetime.utcnow().isoformat()
        },
        'demo': True,
        'message': f'Demo data for {city} - Brazil Property API is working!'
    })

@api_v1.route('/demo/analytics')  
def demo_analytics():
    """Demo analytics endpoint."""
    return jsonify({
        'status': 'success',
        'data': {
            'total_requests': 1250,
            'total_properties': 45670,
            'avg_response_time': 0.15,
            'cache_hit_ratio': 0.85,
            'top_cities': ['São Paulo', 'Rio de Janeiro', 'Brasília', 'Belo Horizonte'],
            'generated_at': datetime.utcnow().isoformat()
        },
        'demo': True,
        'message': 'Demo analytics - Brazil Property API is working!'
    })

@api_v1.route('/status')
def api_status():
    """API status endpoint."""
    return jsonify({
        'api': 'Brazil Property API',
        'version': '1.0.0',
        'status': 'operational',
        'features': {
            'search': 'available (demo mode)',
            'analytics': 'available (demo mode)', 
            'health_checks': 'available',
            'monitoring': 'available'
        },
        'endpoints': {
            'health': '/api/v1/health',
            'demo_search': '/api/v1/demo/search?city=Rio de Janeiro',
            'demo_analytics': '/api/v1/demo/analytics',
            'status': '/api/v1/status'
        },
        'timestamp': datetime.utcnow().isoformat()
    })

# Analytics endpoints
@api_v1.route('/analytics/overview')
def analytics_overview():
    from flask import current_app, jsonify
    
    if not hasattr(current_app, 'analytics'):
        return jsonify({'error': 'Analytics not available'}), 503
    
    try:
        # Get overall analytics data
        business_metrics = current_app.analytics.get_business_metrics()
        user_behavior = current_app.analytics.get_user_behavior_stats()
        custom_events = current_app.analytics.get_custom_event_stats()
        
        return jsonify({
            'status': 'success',
            'data': {
                'business_metrics': business_metrics,
                'user_behavior': user_behavior,
                'custom_events': custom_events,
                'generated_at': datetime.utcnow().isoformat()
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_v1.route('/analytics/performance')
def analytics_performance():
    from flask import current_app, jsonify, request
    
    if not hasattr(current_app, 'metrics_collector'):
        return jsonify({'error': 'Metrics not available'}), 503
    
    try:
        endpoint = request.args.get('endpoint', '/api/v1/search')
        
        # Get performance metrics
        response_metrics = current_app.metrics_collector.get_response_time_metrics(endpoint)
        cache_metrics = current_app.metrics_collector.get_cache_metrics()
        db_metrics = current_app.metrics_collector.get_database_metrics()
        
        return jsonify({
            'status': 'success',
            'data': {
                'endpoint': endpoint,
                'response_time_metrics': response_metrics,
                'cache_metrics': cache_metrics,
                'database_metrics': db_metrics,
                'generated_at': datetime.utcnow().isoformat()
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_v1.route('/health/detailed')
def health_detailed():
    from flask import current_app, jsonify
    
    if not hasattr(current_app, 'health_checker'):
        return jsonify({'error': 'Health checker not available'}), 503
    
    try:
        detailed_health = current_app.health_checker.get_detailed_health_info()
        overall_health = current_app.health_checker.get_overall_health()
        
        return jsonify({
            'status': 'success',
            'overall_health': overall_health,
            'detailed_info': detailed_health,
            'generated_at': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500