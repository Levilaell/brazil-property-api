"""
Search endpoint for property listings.
"""
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import time
import logging

from src.api.exceptions import ValidationError, DatabaseError
from src.scrapers.coordinator import ScraperCoordinator
from src.cache import CacheManager, SmartCache
from src.database import MongoDBHandler


logger = logging.getLogger(__name__)

search_bp = Blueprint('search', __name__)


@search_bp.route('/search', methods=['GET'])
def search_properties():
    """
    Search for properties based on filters.
    
    Query Parameters:
        - city: Required. City name for the search
        - min_price: Minimum price filter
        - max_price: Maximum price filter
        - min_size: Minimum size in square meters
        - max_size: Maximum size in square meters
        - bedrooms: Number of bedrooms
        - property_type: Type of property (apartment, house, etc.)
        - page: Page number for pagination (default: 1)
        - per_page: Results per page (default: 20, max: 100)
    
    Returns:
        JSON response with property listings and metadata
    """
    start_time = time.time()
    
    try:
        # Extract and validate query parameters
        search_params = extract_search_params(request.args)
        validate_search_params(search_params)
        
        # Pagination parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        
        # Check cache
        cache_manager = CacheManager(current_app.config)
        cache_key = generate_cache_key(search_params, page, per_page)
        cached_result = cache_manager.get(cache_key)
        
        if cached_result:
            current_app.cache_hits += 1
            response_time = time.time() - start_time
            return format_response(cached_result, True, response_time)
        
        current_app.cache_total += 1
        
        # Initialize scraper coordinator
        scraper_coordinator = ScraperCoordinator(current_app.config)
        
        # Perform search
        all_properties = scraper_coordinator.scrape_properties(search_params, use_cache=True)
        
        # Apply additional filters if needed
        filtered_properties = apply_filters(all_properties, search_params)
        
        # Calculate statistics
        statistics = calculate_statistics(filtered_properties)
        
        # Paginate results
        total = len(filtered_properties)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_properties = filtered_properties[start_idx:end_idx]
        
        # Prepare response
        result = {
            'properties': paginated_properties,
            'total': total,
            'statistics': statistics,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            },
            'sources': list(set(p.get('source', 'unknown') for p in paginated_properties))
        }
        
        # Cache the result
        cache_manager.set(cache_key, result, ttl=300)  # 5 minutes cache
        
        response_time = time.time() - start_time
        return format_response(result, False, response_time)
        
    except ValidationError as e:
        return jsonify({
            'error': 'Validation Error',
            'message': str(e),
            'status_code': 400
        }), 400
        
    except Exception as e:
        logger.error(f"Error in search endpoint: {str(e)}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An error occurred while processing your request',
            'status_code': 500
        }), 500


def extract_search_params(args):
    """Extract search parameters from request arguments."""
    params = {
        'city': args.get('city', '').strip(),
        'state': 'SP'  # Default to São Paulo state
    }
    
    # Price filters
    if args.get('min_price'):
        params['min_price'] = int(args.get('min_price'))
    if args.get('max_price'):
        params['max_price'] = int(args.get('max_price'))
    
    # Size filters
    if args.get('min_size'):
        params['min_size'] = int(args.get('min_size'))
    if args.get('max_size'):
        params['max_size'] = int(args.get('max_size'))
    
    # Other filters
    if args.get('bedrooms'):
        params['bedrooms'] = int(args.get('bedrooms'))
    if args.get('property_type'):
        params['property_type'] = args.get('property_type')
    
    return params


def validate_search_params(params):
    """Validate search parameters."""
    if not params.get('city'):
        raise ValidationError('City is required')
    
    # Validate price range
    if 'min_price' in params and 'max_price' in params:
        if params['min_price'] > params['max_price']:
            raise ValidationError('Minimum price cannot be greater than maximum price')
    
    # Validate size range
    if 'min_size' in params and 'max_size' in params:
        if params['min_size'] > params['max_size']:
            raise ValidationError('Minimum size cannot be greater than maximum size')


def apply_filters(properties, search_params):
    """Apply additional filters to properties."""
    filtered = properties
    
    # The coordinator already applies most filters, but we can add more here if needed
    # For now, just return the properties as-is
    return filtered


def calculate_statistics(properties):
    """Calculate statistics for the property list."""
    if not properties:
        return {}
    
    prices = [p['price'] for p in properties if p.get('price')]
    sizes = [p['size'] for p in properties if p.get('size')]
    
    stats = {}
    
    if prices:
        stats['avg_price'] = sum(prices) / len(prices)
        stats['min_price'] = min(prices)
        stats['max_price'] = max(prices)
    
    if sizes:
        stats['avg_size'] = sum(sizes) / len(sizes)
        
    if prices and sizes:
        price_per_sqm = []
        for p in properties:
            if p.get('price') and p.get('size') and p['size'] > 0:
                price_per_sqm.append(p['price'] / p['size'])
        
        if price_per_sqm:
            stats['avg_price_per_sqm'] = sum(price_per_sqm) / len(price_per_sqm)
    
    return stats


def generate_cache_key(params, page, per_page):
    """Generate cache key for search results."""
    import hashlib
    key_parts = []
    
    # Add all parameters to key
    for k, v in sorted(params.items()):
        key_parts.append(f"{k}:{v}")
    
    key_parts.append(f"page:{page}")
    key_parts.append(f"per_page:{per_page}")
    
    key_string = '|'.join(key_parts)
    return f"search:{hashlib.md5(key_string.encode()).hexdigest()}"


def format_response(data, cache_hit, response_time):
    """Format the API response."""
    return jsonify({
        'status': 'success',
        'data': data,
        'meta': {
            'timestamp': datetime.utcnow().isoformat(),
            'response_time': round(response_time, 3),
            'cache_hit': cache_hit,
            'sources': data.get('sources', [])
        }
    })


# Mock implementations for testing
# These will be replaced when we implement the actual services
class MockScraperCoordinator:
    def __init__(self, config):
        self.config = config
    
    def search_all(self, **kwargs):
        # Return mock data for testing
        return {
            'properties': [],
            'total': 0,
            'sources': ['zap', 'vivareal']
        }


# For testing purposes, we'll use a global instance
scraper_coordinator = None
cache_manager = None
rate_limiter = None


def init_search_endpoint(app):
    """Initialize the search endpoint with app context."""
    global scraper_coordinator, cache_manager, rate_limiter
    
    scraper_coordinator = ScraperCoordinator(app.config)
    cache_manager = CacheManager(app.config)
    
    # Rate limiter would be initialized here
    # rate_limiter = RateLimiter(app.config)