"""
Price history endpoint for historical property price data.
"""
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import time
import logging

from src.api.exceptions import ValidationError, DatabaseError
from src.database import MongoDBHandler
from src.cache import CacheManager


logger = logging.getLogger(__name__)

price_history_bp = Blueprint('price_history', __name__)


@price_history_bp.route('/price-history', methods=['GET'])
def get_price_history():
    """
    Get price history for a city or neighborhood.
    
    Query Parameters:
        - city: Required. City name
        - neighborhood: Optional. Specific neighborhood
        - period: Time period ('1m', '3m', '6m', '1y', 'all')
    
    Returns:
        JSON response with price history data and trends
    """
    start_time = time.time()
    
    try:
        # Extract and validate parameters
        city = request.args.get('city', '').strip()
        neighborhood = request.args.get('neighborhood', '').strip()
        period = request.args.get('period', '3m').lower()
        
        # Validate city
        if not city:
            raise ValidationError('City is required')
        
        # Check cache
        cache_manager = CacheManager(current_app.config)
        cache_key = generate_cache_key(city, neighborhood, period)
        cached_result = cache_manager.get(cache_key)
        
        if cached_result:
            current_app.cache_hits += 1
            response_time = time.time() - start_time
            return format_response(cached_result, True, response_time)
        
        current_app.cache_total += 1
        
        # Initialize database handler
        mongodb_handler = MongoDBHandler(current_app.config)
        
        # Calculate date range based on period
        start_date = calculate_start_date(period)
        
        # Get price history data
        if neighborhood:
            history_cursor = mongodb_handler.get_price_history_by_neighborhood(city, neighborhood)
        else:
            history_cursor = mongodb_handler.get_price_history(city)
        
        # Convert cursor to list and filter by date
        history_data = []
        # Handle both cursors (from MongoDB) and lists (from tests)
        history_items = list(history_cursor) if hasattr(history_cursor, '__iter__') else history_cursor
        
        for doc in history_items:
            # Create a copy to avoid modifying original
            doc_copy = dict(doc)
            
            # Remove MongoDB ObjectId
            doc_copy.pop('_id', None)
            
            # Convert date to string if it's datetime
            if isinstance(doc_copy.get('date'), datetime):
                doc_copy['date'] = doc_copy['date'].strftime('%Y-%m-%d')
            
            # Filter by date range if not 'all'
            if period != 'all' and start_date:
                try:
                    doc_date = datetime.strptime(doc_copy['date'], '%Y-%m-%d')
                    if doc_date < start_date:
                        continue
                except:
                    continue
            
            history_data.append(doc_copy)
        
        # Calculate trend and statistics
        trend_info = calculate_trend(history_data)
        growth_percentage = calculate_growth_percentage(history_data)
        statistics = calculate_statistics(history_data)
        
        # Format data for charts
        chart_data = format_chart_data(history_data)
        
        # Prepare response
        result = {
            'city': city,
            'neighborhood': neighborhood if neighborhood else None,
            'period': period,
            'history': history_data,
            'trend': trend_info,
            'growth_percentage': growth_percentage,
            'statistics': statistics,
            'chart_data': chart_data
        }
        
        # Cache the result
        cache_manager.set(cache_key, result, ttl=3600)  # 1 hour cache
        
        response_time = time.time() - start_time
        return format_response(result, False, response_time)
        
    except ValidationError as e:
        return jsonify({
            'error': 'Validation Error',
            'message': str(e),
            'status_code': 400
        }), 400
        
    except Exception as e:
        logger.error(f"Error in price history endpoint: {str(e)}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An error occurred while processing your request',
            'status_code': 500
        }), 500


def calculate_start_date(period):
    """Calculate start date based on period."""
    now = datetime.utcnow()
    
    periods = {
        '1m': timedelta(days=30),
        '3m': timedelta(days=90),
        '6m': timedelta(days=180),
        '1y': timedelta(days=365)
    }
    
    if period in periods:
        return now - periods[period]
    
    return None  # 'all' period


def calculate_trend(history_data):
    """Calculate price trend from history data."""
    if len(history_data) < 2:
        return 'insufficient_data'
    
    # Sort by date
    sorted_data = sorted(history_data, key=lambda x: x.get('date', ''))
    
    if not sorted_data:
        return 'insufficient_data'
    
    # Compare first and last prices
    first_price = sorted_data[0].get('avg_price', 0)
    last_price = sorted_data[-1].get('avg_price', 0)
    
    if first_price == 0:
        return 'insufficient_data'
    
    change_percent = ((last_price - first_price) / first_price) * 100
    
    if change_percent > 5:
        return 'up'
    elif change_percent < -5:
        return 'down'
    else:
        return 'stable'


def calculate_growth_percentage(history_data):
    """Calculate growth percentage from history data."""
    if len(history_data) < 2:
        return 0
    
    # Sort by date
    sorted_data = sorted(history_data, key=lambda x: x.get('date', ''))
    
    if not sorted_data:
        return 0
    
    # Compare first and last prices
    first_price = sorted_data[0].get('avg_price', 0)
    last_price = sorted_data[-1].get('avg_price', 0)
    
    if first_price == 0:
        return 0
    
    return round(((last_price - first_price) / first_price) * 100, 1)


def calculate_statistics(history_data):
    """Calculate statistics from history data."""
    if not history_data:
        return {}
    
    prices = [d.get('avg_price', 0) for d in history_data if d.get('avg_price')]
    
    if not prices:
        return {}
    
    stats = {
        'current_avg_price': prices[-1] if prices else 0,
        'previous_avg_price': prices[0] if prices else 0,
        'max_price': max(prices),
        'min_price': min(prices),
        'price_volatility': calculate_volatility(prices)
    }
    
    return stats


def calculate_volatility(prices):
    """Calculate price volatility as standard deviation percentage."""
    if len(prices) < 2:
        return 0
    
    avg_price = sum(prices) / len(prices)
    variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
    std_dev = variance ** 0.5
    
    return round((std_dev / avg_price) * 100, 2) if avg_price > 0 else 0


def format_chart_data(history_data):
    """Format data for chart visualization."""
    if not history_data:
        return {'labels': [], 'datasets': []}
    
    # Sort by date
    sorted_data = sorted(history_data, key=lambda x: x.get('date', ''))
    
    labels = [d.get('date', '') for d in sorted_data]
    prices = [d.get('avg_price', 0) for d in sorted_data]
    
    return {
        'labels': labels,
        'datasets': [
            {
                'label': 'Average Price',
                'data': prices,
                'borderColor': 'rgb(75, 192, 192)',
                'tension': 0.1
            }
        ]
    }


def generate_cache_key(city, neighborhood, period):
    """Generate cache key for price history."""
    import hashlib
    key_parts = [f"city:{city}", f"period:{period}"]
    
    if neighborhood:
        key_parts.append(f"neighborhood:{neighborhood}")
    
    key_string = '|'.join(key_parts)
    return f"price_history:{hashlib.md5(key_string.encode()).hexdigest()}"


def format_response(data, cache_hit, response_time):
    """Format the API response."""
    return jsonify({
        'status': 'success',
        'data': data,
        'meta': {
            'timestamp': datetime.utcnow().isoformat(),
            'response_time': round(response_time, 3),
            'cache_hit': cache_hit
        }
    })