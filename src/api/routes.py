from flask import Blueprint
from src.api.base import register_health_check, register_metrics

# Create the API blueprint
api_v1 = Blueprint('api_v1', __name__)

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