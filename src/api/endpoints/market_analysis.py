"""
Market analysis endpoint for comprehensive market insights and investment opportunities.
"""
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import time
import logging

from src.api.exceptions import ValidationError, DatabaseError
from src.database import MongoDBHandler
from src.cache import CacheManager


logger = logging.getLogger(__name__)

market_analysis_bp = Blueprint('market_analysis', __name__)


@market_analysis_bp.route('/market-analysis', methods=['GET'])
def get_market_analysis():
    """
    Get comprehensive market analysis for a city.
    
    Query Parameters:
        - city: Required. City name for analysis
    
    Returns:
        JSON response with market analysis data including:
        - Price trends
        - Market velocity
        - Neighborhood rankings
        - Investment opportunities
        - Market insights
    """
    start_time = time.time()
    
    try:
        # Extract and validate parameters
        city = request.args.get('city', '').strip()
        
        # Validate city
        if not city:
            raise ValidationError('City is required')
        
        # Check cache
        cache_manager = CacheManager(current_app.config)
        cache_key = generate_cache_key(city)
        cached_result = cache_manager.get(cache_key)
        
        if cached_result:
            current_app.cache_hits += 1
            response_time = time.time() - start_time
            return format_response(cached_result, True, response_time)
        
        current_app.cache_total += 1
        
        # Initialize database handler
        mongodb_handler = MongoDBHandler(current_app.config)
        
        # Get basic market analysis
        market_data = mongodb_handler.get_market_analysis(city)
        
        # Get price trends
        price_trends = calculate_price_trends(mongodb_handler, city)
        
        # Get market velocity metrics
        market_velocity = calculate_market_velocity(mongodb_handler, city)
        
        # Get neighborhood rankings
        neighborhood_rankings = get_neighborhood_rankings(mongodb_handler, city)
        
        # Get investment opportunities
        investment_opportunities = get_investment_opportunities(mongodb_handler, city)
        
        # Generate market insights
        insights = generate_market_insights(market_data, price_trends, market_velocity)
        
        # Prepare comprehensive response
        result = {
            'city': city,
            'analysis_date': datetime.utcnow().strftime('%Y-%m-%d'),
            'market_overview': market_data,
            'price_trends': price_trends,
            'market_velocity': market_velocity,
            'neighborhood_rankings': neighborhood_rankings,
            'investment_opportunities': investment_opportunities,
            'insights': insights
        }
        
        # Cache the result for 4 hours (longer cache for complex analysis)
        cache_manager.set(cache_key, result, ttl=14400)
        
        response_time = time.time() - start_time
        return format_response(result, False, response_time)
        
    except ValidationError as e:
        return jsonify({
            'error': 'Validation Error',
            'message': str(e),
            'status_code': 400
        }), 400
        
    except Exception as e:
        logger.error(f"Error in market analysis endpoint: {str(e)}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An error occurred while processing your request',
            'status_code': 500
        }), 500


def calculate_price_trends(mongodb_handler, city):
    """Calculate price trends and growth rates."""
    try:
        # Get recent price history
        price_history = list(mongodb_handler.get_price_history(city))
        
        if len(price_history) < 2:
            return {
                'growth_rate': 0,
                'trend_direction': 'insufficient_data',
                'monthly_growth': 0,
                'quarterly_growth': 0,
                'yearly_growth': 0
            }
        
        # Sort by date to ensure correct ordering
        price_history.sort(key=lambda x: x.get('date', ''))
        
        # Calculate growth rates
        current_price = price_history[-1].get('avg_price', 0)
        previous_price = price_history[0].get('avg_price', 0)
        
        if previous_price == 0:
            return {
                'growth_rate': 0,
                'trend_direction': 'insufficient_data',
                'monthly_growth': 0,
                'quarterly_growth': 0,
                'yearly_growth': 0
            }
        
        overall_growth = ((current_price - previous_price) / previous_price) * 100
        
        # Determine trend direction
        if overall_growth > 5:
            trend_direction = 'up'
        elif overall_growth < -5:
            trend_direction = 'down'
        else:
            trend_direction = 'stable'
        
        return {
            'growth_rate': round(overall_growth, 2),
            'trend_direction': trend_direction,
            'monthly_growth': round(overall_growth / 12, 2),
            'quarterly_growth': round(overall_growth / 4, 2),
            'yearly_growth': round(overall_growth, 2),
            'current_avg_price': current_price,
            'previous_avg_price': previous_price
        }
        
    except Exception as e:
        logger.error(f"Error calculating price trends: {e}")
        return {'growth_rate': 0, 'trend_direction': 'error'}


def calculate_market_velocity(mongodb_handler, city):
    """Calculate market velocity metrics."""
    try:
        # Get aggregated market metrics
        metrics = mongodb_handler.aggregate_market_metrics(city)
        
        if not metrics:
            return {
                'avg_days_on_market': 0,
                'properties_sold_30d': 0,
                'new_listings_30d': 0,
                'absorption_rate': 0,
                'market_heat': 'cold'
            }
        
        # Calculate absorption rate (properties sold / new listings)
        sold = metrics.get('properties_sold_30d', 0)
        new_listings = metrics.get('new_listings_30d', 1)  # Avoid division by zero
        absorption_rate = sold / new_listings if new_listings > 0 else 0
        
        # Determine market heat
        if absorption_rate > 0.8:
            market_heat = 'hot'
        elif absorption_rate > 0.6:
            market_heat = 'warm'
        elif absorption_rate > 0.4:
            market_heat = 'balanced'
        else:
            market_heat = 'cold'
        
        return {
            'avg_days_on_market': metrics.get('avg_days_on_market', 0),
            'properties_sold_30d': sold,
            'new_listings_30d': new_listings,
            'absorption_rate': round(absorption_rate, 2),
            'market_heat': market_heat,
            'inventory_months': round((new_listings - sold) / max(sold, 1), 1)
        }
        
    except Exception as e:
        logger.error(f"Error calculating market velocity: {e}")
        return {'market_heat': 'unknown'}


def get_neighborhood_rankings(mongodb_handler, city):
    """Get neighborhood rankings with investment scores."""
    try:
        neighborhood_stats = mongodb_handler.calculate_neighborhood_stats(city)
        
        # Add investment scores and rankings
        for i, neighborhood in enumerate(neighborhood_stats):
            # Calculate investment score based on multiple factors
            avg_price = neighborhood.get('avg_price', 0)
            total_properties = neighborhood.get('total_properties', 0)
            
            # Simple scoring algorithm (can be enhanced)
            price_score = min(avg_price / 1000000, 10)  # Max 10 points for price
            volume_score = min(total_properties / 100, 5)  # Max 5 points for volume
            
            investment_score = price_score + volume_score
            neighborhood['investment_score'] = round(investment_score, 1)
            neighborhood['rank'] = i + 1
        
        # Sort by investment score (descending)
        neighborhood_stats.sort(key=lambda x: x.get('investment_score', 0), reverse=True)
        
        # Update ranks after sorting
        for i, neighborhood in enumerate(neighborhood_stats):
            neighborhood['rank'] = i + 1
        
        return neighborhood_stats[:10]  # Return top 10
        
    except Exception as e:
        logger.error(f"Error getting neighborhood rankings: {e}")
        return []


def get_investment_opportunities(mongodb_handler, city):
    """Get investment opportunities with detailed analysis."""
    try:
        opportunities = mongodb_handler.get_investment_opportunities(city)
        
        # Enhance opportunities with additional data
        for opportunity in opportunities:
            # Add ROI projections
            avg_price = opportunity.get('avg_price', 0)
            expected_growth = opportunity.get('expected_growth', 0)
            
            if avg_price > 0 and expected_growth > 0:
                # Simple ROI calculation (can be enhanced)
                annual_roi = expected_growth / 100
                five_year_projection = avg_price * (1 + annual_roi) ** 5
                
                opportunity['roi_projection'] = {
                    'annual_roi': round(annual_roi * 100, 1),
                    'five_year_value': round(five_year_projection, 0),
                    'potential_gain': round(five_year_projection - avg_price, 0)
                }
        
        return opportunities
        
    except Exception as e:
        logger.error(f"Error getting investment opportunities: {e}")
        return []


def generate_market_insights(market_data, price_trends, market_velocity):
    """Generate automated market insights."""
    insights = []
    
    try:
        # Price trend insights
        trend_direction = price_trends.get('trend_direction', '')
        growth_rate = price_trends.get('growth_rate', 0)
        
        if trend_direction == 'up' and growth_rate > 10:
            insights.append({
                'type': 'market_trend',
                'message': f'Strong price growth of {growth_rate}% indicates a hot market with high demand',
                'importance': 'high'
            })
        elif trend_direction == 'down':
            insights.append({
                'type': 'market_trend',
                'message': f'Price decline of {abs(growth_rate)}% may present buying opportunities',
                'importance': 'medium'
            })
        elif trend_direction == 'stable':
            insights.append({
                'type': 'market_trend',
                'message': 'Stable prices indicate a balanced market with steady demand',
                'importance': 'low'
            })
        
        # Market velocity insights
        market_heat = market_velocity.get('market_heat', '')
        absorption_rate = market_velocity.get('absorption_rate', 0)
        
        if market_heat == 'hot':
            insights.append({
                'type': 'market_velocity',
                'message': f'High absorption rate of {absorption_rate:.1%} indicates strong buyer demand',
                'importance': 'high'
            })
        elif market_heat == 'cold':
            insights.append({
                'type': 'market_velocity',
                'message': f'Low absorption rate of {absorption_rate:.1%} suggests buyer caution',
                'importance': 'medium'
            })
        
        # Market overview insights
        total_properties = market_data.get('total_properties', 0)
        avg_price = market_data.get('avg_price', 0)
        
        if total_properties > 1000:
            insights.append({
                'type': 'market_size',
                'message': f'Large inventory of {total_properties:,} properties provides good selection',
                'importance': 'low'
            })
        
        if avg_price > 0:
            insights.append({
                'type': 'pricing',
                'message': f'Average property price is R$ {avg_price:,.0f}',
                'importance': 'low'
            })
        
        return insights
        
    except Exception as e:
        logger.error(f"Error generating insights: {e}")
        return []


def generate_cache_key(city):
    """Generate cache key for market analysis."""
    import hashlib
    key_string = f"market_analysis:{city.lower()}"
    return hashlib.md5(key_string.encode()).hexdigest()


def format_response(data, cache_hit, response_time):
    """Format the API response."""
    return jsonify({
        'status': 'success',
        'data': data,
        'meta': {
            'timestamp': datetime.utcnow().isoformat(),
            'response_time': round(response_time, 3),
            'cache_hit': cache_hit,
            'analysis_complexity': 'comprehensive'
        }
    })