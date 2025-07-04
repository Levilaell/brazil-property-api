import pytest
from flask import Flask
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime, timedelta

from src.api.endpoints.market_analysis import get_market_analysis


class TestMarketAnalysisEndpoint:
    @pytest.fixture
    def app(self):
        from src.api.base import create_app
        app = create_app(testing=True)
        return app
        
    @pytest.fixture
    def client(self, app):
        return app.test_client()
        
    def test_market_analysis_complete(self, client):
        with patch('src.api.endpoints.market_analysis.MongoDBHandler') as mock_db_class:
            with patch('src.api.endpoints.market_analysis.CacheManager') as mock_cache_class:
                # Setup mocks
                mock_db = mock_db_class.return_value
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None  # Cache miss
                
                # Mock comprehensive market data
                mock_db.get_market_analysis.return_value = {
                    'city': 'São Paulo',
                    'total_properties': 15000,
                    'avg_price': 520000,
                    'min_price': 200000,
                    'max_price': 2000000,
                    'avg_size': 85
                }
                
                mock_db.get_price_history.return_value = [
                    {'date': '2024-01-01', 'avg_price': 500000},
                    {'date': '2024-02-01', 'avg_price': 510000},
                    {'date': '2024-03-01', 'avg_price': 520000}
                ]
                
                mock_db.calculate_neighborhood_stats.return_value = [
                    {'neighborhood': 'Vila Mariana', 'avg_price': 650000, 'total_properties': 500},
                    {'neighborhood': 'Pinheiros', 'avg_price': 750000, 'total_properties': 450}
                ]
                
                mock_db.get_investment_opportunities.return_value = [
                    {
                        'neighborhood': 'Campo Belo',
                        'avg_price': 480000,
                        'expected_growth': 15.5,
                        'opportunity_score': 9.2
                    }
                ]
                
                mock_db.aggregate_market_metrics.return_value = {
                    'avg_days_on_market': 45,
                    'properties_sold_30d': 1200,
                    'new_listings_30d': 1500
                }
                
                response = client.get('/api/v1/market-analysis?city=São Paulo')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                assert data['status'] == 'success'
                assert data['data']['city'] == 'São Paulo'
                assert 'price_trends' in data['data']
                assert 'market_velocity' in data['data']
                assert 'neighborhood_rankings' in data['data']
                assert 'investment_opportunities' in data['data']
                assert 'insights' in data['data']
            
    def test_price_trends_calculation(self, client):
        with patch('src.api.endpoints.market_analysis.MongoDBHandler') as mock_db_class:
            with patch('src.api.endpoints.market_analysis.CacheManager') as mock_cache_class:
                mock_db = mock_db_class.return_value
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                mock_db.get_market_analysis.return_value = {'city': 'São Paulo', 'avg_price': 530000}
                
                mock_db.get_price_history.return_value = [
                    {'date': '2024-01-01', 'avg_price': 500000},
                    {'date': '2024-02-01', 'avg_price': 510000},
                    {'date': '2024-03-01', 'avg_price': 530000}  # 6% growth > 5% threshold
                ]
                
                mock_db.calculate_neighborhood_stats.return_value = []
                mock_db.get_investment_opportunities.return_value = []
                mock_db.aggregate_market_metrics.return_value = {}
                
                response = client.get('/api/v1/market-analysis?city=São Paulo')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                trends = data['data']['price_trends']
                
                assert 'growth_rate' in trends
                assert 'trend_direction' in trends
                assert trends['trend_direction'] == 'up'
                assert trends['growth_rate'] == 6.0  # (530000-500000)/500000 * 100
            
    def test_market_velocity_calculation(self, client):
        with patch('src.api.endpoints.market_analysis.MongoDBHandler') as mock_db_class:
            with patch('src.api.endpoints.market_analysis.CacheManager') as mock_cache_class:
                mock_db = mock_db_class.return_value
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                mock_db.get_market_analysis.return_value = {'city': 'São Paulo'}
                mock_db.get_price_history.return_value = []
                mock_db.calculate_neighborhood_stats.return_value = []
                mock_db.get_investment_opportunities.return_value = []
                
                mock_db.aggregate_market_metrics.return_value = {
                    'avg_days_on_market': 45,
                    'properties_sold_30d': 1200,
                    'new_listings_30d': 1500
                }
                
                response = client.get('/api/v1/market-analysis?city=São Paulo')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                velocity = data['data']['market_velocity']
                
                assert velocity['avg_days_on_market'] == 45
                assert velocity['absorption_rate'] == 0.8  # 1200/1500
                assert 'market_heat' in velocity
                
    def test_neighborhood_ranking(self, client):
        with patch('src.api.endpoints.market_analysis.MongoDBHandler') as mock_db_class:
            with patch('src.api.endpoints.market_analysis.CacheManager') as mock_cache_class:
                mock_db = mock_db_class.return_value
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                mock_db.get_market_analysis.return_value = {'city': 'São Paulo'}
                mock_db.get_price_history.return_value = []
                mock_db.get_investment_opportunities.return_value = []
                mock_db.aggregate_market_metrics.return_value = {}
                
                mock_db.calculate_neighborhood_stats.return_value = [
                    {
                        'neighborhood': 'Vila Mariana',
                        'avg_price': 650000,
                        'total_properties': 500
                    },
                    {
                        'neighborhood': 'Pinheiros',
                        'avg_price': 750000,
                        'total_properties': 450
                    },
                    {
                        'neighborhood': 'Moema',
                        'avg_price': 850000,
                        'total_properties': 400
                    }
                ]
                
                response = client.get('/api/v1/market-analysis?city=São Paulo')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                rankings = data['data']['neighborhood_rankings']
                
                assert len(rankings) == 3
                assert all('rank' in r for r in rankings)
                assert all('investment_score' in r for r in rankings)
                assert rankings[0]['rank'] == 1
                
    def test_investment_opportunities(self, client):
        with patch('src.api.endpoints.market_analysis.MongoDBHandler') as mock_db_class:
            with patch('src.api.endpoints.market_analysis.CacheManager') as mock_cache_class:
                mock_db = mock_db_class.return_value
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                mock_db.get_market_analysis.return_value = {'city': 'São Paulo'}
                mock_db.get_price_history.return_value = []
                mock_db.calculate_neighborhood_stats.return_value = []
                mock_db.aggregate_market_metrics.return_value = {}
                
                mock_db.get_investment_opportunities.return_value = [
                    {
                        'neighborhood': 'Campo Belo',
                        'opportunity_score': 9.2,
                        'avg_price': 480000,
                        'expected_growth': 15.5
                    },
                    {
                        'neighborhood': 'Saúde',
                        'opportunity_score': 8.8,
                        'avg_price': 420000,
                        'expected_growth': 12.3
                    }
                ]
                
                response = client.get('/api/v1/market-analysis?city=São Paulo')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                opportunities = data['data']['investment_opportunities']
                
                assert len(opportunities) >= 2
                assert opportunities[0]['opportunity_score'] == 9.2
                assert 'roi_projection' in opportunities[0]
                assert 'annual_roi' in opportunities[0]['roi_projection']
                
    def test_market_insights_generation(self, client):
        with patch('src.api.endpoints.market_analysis.MongoDBHandler') as mock_db_class:
            with patch('src.api.endpoints.market_analysis.CacheManager') as mock_cache_class:
                mock_db = mock_db_class.return_value
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                mock_db.get_market_analysis.return_value = {
                    'city': 'São Paulo',
                    'avg_price': 520000,
                    'total_properties': 15000
                }
                
                mock_db.get_price_history.return_value = [
                    {'date': '2024-01-01', 'avg_price': 500000},
                    {'date': '2024-03-01', 'avg_price': 550000}  # 10% growth
                ]
                
                mock_db.calculate_neighborhood_stats.return_value = []
                mock_db.get_investment_opportunities.return_value = []
                
                mock_db.aggregate_market_metrics.return_value = {
                    'properties_sold_30d': 1200,
                    'new_listings_30d': 1500
                }
                
                response = client.get('/api/v1/market-analysis?city=São Paulo')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                insights = data['data']['insights']
                
                assert isinstance(insights, list)
                assert len(insights) > 0
                assert all('type' in insight for insight in insights)
                assert all('message' in insight for insight in insights)
                assert all('importance' in insight for insight in insights)
                
    def test_analysis_cache_strategy(self, client):
        with patch('src.api.endpoints.market_analysis.CacheManager') as mock_cache_class:
            # Test cache hit
            mock_cache = mock_cache_class.return_value
            cached_analysis = {
                'city': 'São Paulo',
                'cached': True,
                'analysis_date': '2024-03-01'
            }
            mock_cache.get.return_value = cached_analysis
            
            response = client.get('/api/v1/market-analysis?city=São Paulo')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['meta']['cache_hit'] is True
            
            # Test cache miss with complex calculation
            mock_cache.get.return_value = None
            
            with patch('src.api.endpoints.market_analysis.MongoDBHandler') as mock_db_class:
                mock_db = mock_db_class.return_value
                mock_db.get_market_analysis.return_value = {'city': 'Rio de Janeiro', 'avg_price': 450000}
                mock_db.get_price_history.return_value = []
                mock_db.calculate_neighborhood_stats.return_value = []
                mock_db.get_investment_opportunities.return_value = []
                mock_db.aggregate_market_metrics.return_value = {}
                
                response = client.get('/api/v1/market-analysis?city=Rio de Janeiro')
                assert response.status_code == 200
                
                # Verify cache was set with appropriate TTL
                mock_cache.set.assert_called()
                call_args = mock_cache.set.call_args
                assert call_args[1]['ttl'] >= 3600  # At least 1 hour cache