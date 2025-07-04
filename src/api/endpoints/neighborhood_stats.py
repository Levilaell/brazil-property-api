"""
Neighborhood statistics endpoint for detailed area analysis and ratings.
"""
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import time
import logging

from src.api.exceptions import ValidationError, DatabaseError
from src.database import MongoDBHandler
from src.cache import CacheManager


logger = logging.getLogger(__name__)

neighborhood_stats_bp = Blueprint('neighborhood_stats', __name__)


@neighborhood_stats_bp.route('/neighborhood-stats', methods=['GET'])
def get_neighborhood_stats():
    """
    Get comprehensive neighborhood statistics and analysis.
    
    Query Parameters:
        - city: Required. City name
        - neighborhood: Required or multiple neighborhoods for comparison
        - enriched: Optional. Include enriched data (walkability, safety, etc.)
        - compare: Optional. Enable comparison mode for multiple neighborhoods
        - metrics: Optional. Specific metrics to include (walkability, safety, infrastructure)
    
    Returns:
        JSON response with neighborhood statistics, ratings, and analysis
    """
    start_time = time.time()
    
    try:
        # Extract and validate parameters
        city = request.args.get('city', '').strip()
        neighborhood = request.args.get('neighborhood', '').strip()
        enriched = request.args.get('enriched', '').lower() == 'true'
        compare = request.args.get('compare', '').lower() == 'true'
        metrics = request.args.get('metrics', '').strip()
        
        # Validate required parameters
        if not city:
            raise ValidationError('City is required')
        if not neighborhood:
            raise ValidationError('Neighborhood is required')
        
        # Handle multiple neighborhoods for comparison
        neighborhoods = [n.strip() for n in neighborhood.split(',') if n.strip()]
        
        # Check cache
        cache_manager = CacheManager(current_app.config)
        cache_key = generate_cache_key(city, neighborhoods, enriched, compare, metrics)
        cached_result = cache_manager.get(cache_key)
        
        if cached_result:
            current_app.cache_hits += 1
            response_time = time.time() - start_time
            return format_response(cached_result, True, response_time)
        
        current_app.cache_total += 1
        
        # Initialize database handler
        mongodb_handler = MongoDBHandler(current_app.config)
        
        if compare and len(neighborhoods) > 1:
            # Comparison mode
            result = get_neighborhood_comparison(mongodb_handler, city, neighborhoods, enriched)
        else:
            # Single neighborhood analysis
            result = get_single_neighborhood_stats(
                mongodb_handler, city, neighborhoods[0], enriched, metrics
            )
        
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
        logger.error(f"Error in neighborhood stats endpoint: {str(e)}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An error occurred while processing your request',
            'status_code': 500
        }), 500


def get_single_neighborhood_stats(mongodb_handler, city, neighborhood, enriched, metrics):
    """Get statistics for a single neighborhood."""
    try:
        # Get basic neighborhood statistics
        neighborhood_data = get_basic_neighborhood_stats(mongodb_handler, city, neighborhood)
        
        result = {
            'city': city,
            'neighborhood': neighborhood,
            'analysis_date': datetime.utcnow().strftime('%Y-%m-%d'),
            **neighborhood_data
        }
        
        # Add enriched data if requested
        if enriched:
            enriched_data = enrich_neighborhood_data(neighborhood, city)
            result.update(enriched_data)
        
        # Add specific metrics if requested
        if metrics:
            metric_types = [m.strip() for m in metrics.split(',') if m.strip()]
            for metric_type in metric_types:
                if metric_type == 'walkability':
                    result['walkability'] = calculate_walkability_score(neighborhood, city)
                elif metric_type == 'safety':
                    result['safety'] = calculate_safety_index(neighborhood, city)
                elif metric_type == 'infrastructure':
                    result['infrastructure'] = calculate_infrastructure_rating(neighborhood, city)
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting single neighborhood stats: {e}")
        return {'city': city, 'neighborhood': neighborhood, 'error': str(e)}


def get_neighborhood_comparison(mongodb_handler, city, neighborhoods, enriched):
    """Get comparison data for multiple neighborhoods."""
    try:
        comparison_data = []
        
        for neighborhood in neighborhoods:
            neighborhood_data = get_basic_neighborhood_stats(mongodb_handler, city, neighborhood)
            neighborhood_data['neighborhood'] = neighborhood
            
            if enriched:
                enriched_data = enrich_neighborhood_data(neighborhood, city)
                neighborhood_data.update(enriched_data)
            
            comparison_data.append(neighborhood_data)
        
        # Add comparison rankings
        add_comparison_rankings(comparison_data)
        
        result = {
            'city': city,
            'comparison_type': 'neighborhoods',
            'analysis_date': datetime.utcnow().strftime('%Y-%m-%d'),
            'comparison': comparison_data,
            'summary': generate_comparison_summary(comparison_data)
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting neighborhood comparison: {e}")
        return {'city': city, 'neighborhoods': neighborhoods, 'error': str(e)}


def get_basic_neighborhood_stats(mongodb_handler, city, neighborhood):
    """Get basic statistics for a neighborhood."""
    try:
        # Get neighborhood stats from database
        stats_list = mongodb_handler.calculate_neighborhood_stats(city)
        
        # Find the specific neighborhood
        neighborhood_stats = None
        for stats in stats_list:
            if stats.get('_id', '').lower() == neighborhood.lower():
                neighborhood_stats = stats
                break
        
        if not neighborhood_stats:
            return {
                'total_properties': 0,
                'avg_price': 0,
                'min_price': 0,
                'max_price': 0,
                'avg_size': 0,
                'avg_price_per_sqm': 0,
                'property_types': {},
                'bedroom_distribution': {}
            }
        
        # Format the stats
        total_properties = neighborhood_stats.get('total_properties', 0)
        avg_price = neighborhood_stats.get('avg_price', 0)
        avg_size = neighborhood_stats.get('avg_size', 0)
        
        return {
            'total_properties': total_properties,
            'avg_price': round(avg_price, 0) if avg_price else 0,
            'min_price': neighborhood_stats.get('min_price', 0),
            'max_price': neighborhood_stats.get('max_price', 0),
            'avg_size': round(avg_size, 1) if avg_size else 0,
            'avg_price_per_sqm': round(avg_price / avg_size, 0) if avg_price and avg_size else 0,
            'property_types': generate_property_type_distribution(total_properties),
            'bedroom_distribution': generate_bedroom_distribution(total_properties)
        }
        
    except Exception as e:
        logger.error(f"Error getting basic neighborhood stats: {e}")
        return {}


def generate_property_type_distribution(total_properties):
    """Generate mock property type distribution."""
    if total_properties == 0:
        return {}
    
    # Mock distribution based on typical Brazilian neighborhoods
    return {
        'apartment': int(total_properties * 0.65),
        'house': int(total_properties * 0.25),
        'commercial': int(total_properties * 0.10)
    }


def generate_bedroom_distribution(total_properties):
    """Generate mock bedroom distribution."""
    if total_properties == 0:
        return {}
    
    # Mock distribution
    return {
        '1': int(total_properties * 0.20),
        '2': int(total_properties * 0.40),
        '3': int(total_properties * 0.30),
        '4+': int(total_properties * 0.10)
    }


def enrich_neighborhood_data(neighborhood, city):
    """Add enriched data like walkability, demographics, amenities."""
    # Mock enriched data - in real implementation, this would integrate with external APIs
    return {
        'walkability_score': 8.5,
        'transit_score': 9.0,
        'safety_index': 7.8,
        'education_quality': 8.2,
        'healthcare_access': 8.7,
        'amenities': {
            'supermarkets': 15,
            'restaurants': 45,
            'schools': 8,
            'hospitals': 3,
            'parks': 5,
            'metro_stations': 2
        },
        'demographics': {
            'avg_income': 12000,
            'population_density': 'high',
            'avg_age': 35
        }
    }


def calculate_walkability_score(neighborhood, city):
    """Calculate walkability score for the neighborhood."""
    # Mock walkability calculation
    return {
        'score': 8.5,
        'components': {
            'transit_access': 9.0,
            'pedestrian_infrastructure': 8.0,
            'amenity_density': 8.5,
            'street_connectivity': 8.5
        },
        'category': 'Very Walkable'
    }


def calculate_safety_index(neighborhood, city):
    """Calculate safety index for the neighborhood."""
    # Mock safety calculation
    return {
        'index': 7.8,
        'components': {
            'crime_rate': 'low',
            'lighting_quality': 'good',
            'police_presence': 'moderate',
            'community_safety': 'high'
        },
        'trend': 'improving',
        'category': 'Safe'
    }


def calculate_infrastructure_rating(neighborhood, city):
    """Calculate infrastructure rating for the neighborhood."""
    # Mock infrastructure calculation
    return {
        'overall_rating': 8.3,
        'categories': {
            'transportation': 9.0,
            'utilities': 8.5,
            'healthcare': 8.0,
            'education': 8.2,
            'commerce': 7.8,
            'recreation': 8.5
        },
        'recent_improvements': [
            'New metro line connection',
            'Hospital renovation completed',
            'Fiber optic internet expansion'
        ]
    }


def add_comparison_rankings(comparison_data):
    """Add rankings to comparison data."""
    # Sort by average price and add price rankings
    sorted_by_price = sorted(comparison_data, key=lambda x: x.get('avg_price', 0), reverse=True)
    for i, neighborhood in enumerate(sorted_by_price):
        neighborhood['price_rank'] = i + 1
    
    # Add value score (simple calculation)
    for neighborhood in comparison_data:
        avg_price = neighborhood.get('avg_price', 0)
        total_properties = neighborhood.get('total_properties', 0)
        
        # Simple value score calculation
        price_score = max(0, 10 - (avg_price / 100000))  # Lower price = higher score
        volume_score = min(total_properties / 100, 5)  # More properties = higher score
        
        neighborhood['value_score'] = round(price_score + volume_score, 1)


def generate_comparison_summary(comparison_data):
    """Generate summary of the comparison."""
    if not comparison_data:
        return {}
    
    prices = [n.get('avg_price', 0) for n in comparison_data]
    sizes = [n.get('avg_size', 0) for n in comparison_data if n.get('avg_size', 0) > 0]
    
    return {
        'most_expensive': max(comparison_data, key=lambda x: x.get('avg_price', 0))['neighborhood'],
        'most_affordable': min(comparison_data, key=lambda x: x.get('avg_price', 0) or float('inf'))['neighborhood'],
        'avg_price_range': {
            'min': min(prices) if prices else 0,
            'max': max(prices) if prices else 0
        },
        'avg_size_range': {
            'min': min(sizes) if sizes else 0,
            'max': max(sizes) if sizes else 0
        }
    }


def generate_cache_key(city, neighborhoods, enriched, compare, metrics):
    """Generate cache key for neighborhood stats."""
    import hashlib
    key_parts = [
        f"city:{city.lower()}",
        f"neighborhoods:{','.join(sorted(neighborhoods)).lower()}",
        f"enriched:{enriched}",
        f"compare:{compare}",
        f"metrics:{metrics}"
    ]
    
    key_string = '|'.join(key_parts)
    return f"neighborhood_stats:{hashlib.md5(key_string.encode()).hexdigest()}"


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