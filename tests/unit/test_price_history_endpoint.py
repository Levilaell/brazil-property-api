import pytest
from flask import Flask
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime, timedelta

from src.api.endpoints.price_history import get_price_history


class TestPriceHistoryEndpoint:
    @pytest.fixture
    def app(self):
        from src.api.base import create_app
        app = create_app(testing=True)
        return app
        
    @pytest.fixture
    def client(self, app):
        return app.test_client()
        
    def test_price_history_by_city(self, client):
        with patch('src.api.endpoints.price_history.MongoDBHandler') as mock_db_class:
            with patch('src.api.endpoints.price_history.CacheManager') as mock_cache_class:
                # Setup mocks
                mock_db = mock_db_class.return_value
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None  # Cache miss
                
                # Mock historical data
                history_data = [
                    {
                        'date': '2024-01-01',
                        'city': 'São Paulo',
                        'avg_price': 450000,
                        'min_price': 200000,
                        'max_price': 1200000,
                        'total_properties': 1500,
                        'avg_price_per_sqm': 7500
                    },
                    {
                        'date': '2024-02-01',
                        'city': 'São Paulo',
                        'avg_price': 460000,
                        'min_price': 210000,
                        'max_price': 1250000,
                        'total_properties': 1600,
                        'avg_price_per_sqm': 7650
                    },
                    {
                        'date': '2024-03-01',
                        'city': 'São Paulo',
                        'avg_price': 470000,
                        'min_price': 220000,
                        'max_price': 1300000,
                        'total_properties': 1700,
                        'avg_price_per_sqm': 7800
                    }
                ]
                mock_db.get_price_history.return_value = history_data
                
                response = client.get('/api/v1/price-history?city=São Paulo&period=all')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                assert data['status'] == 'success'
                assert len(data['data']['history']) == 3
                assert data['data']['city'] == 'São Paulo'
                assert 'trend' in data['data']
                assert 'growth_percentage' in data['data']
            
    def test_price_history_by_neighborhood(self, client):
        with patch('src.api.endpoints.price_history.MongoDBHandler') as mock_db_class:
            with patch('src.api.endpoints.price_history.CacheManager') as mock_cache_class:
                mock_db = mock_db_class.return_value
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                history_data = [
                    {
                        'date': '2024-01-01',
                        'city': 'São Paulo',
                        'neighborhood': 'Vila Mariana',
                        'avg_price': 550000,
                        'total_properties': 200
                    },
                    {
                        'date': '2024-02-01',
                        'city': 'São Paulo',
                        'neighborhood': 'Vila Mariana',
                        'avg_price': 560000,
                        'total_properties': 210
                    }
                ]
                mock_db.get_price_history_by_neighborhood.return_value = history_data
                
                response = client.get('/api/v1/price-history?city=São Paulo&neighborhood=Vila Mariana&period=all')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                assert data['data']['neighborhood'] == 'Vila Mariana'
                assert len(data['data']['history']) == 2
            
    def test_price_history_with_period(self, client):
        with patch('src.api.endpoints.price_history.MongoDBHandler') as mock_db_class:
            with patch('src.api.endpoints.price_history.CacheManager') as mock_cache_class:
                mock_db = mock_db_class.return_value
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                mock_db.get_price_history.return_value = []
                
                # Test different period options
                periods = ['1m', '3m', '6m', '1y', 'all']
                
                for period in periods:
                    response = client.get(f'/api/v1/price-history?city=São Paulo&period={period}')
                    assert response.status_code == 200
                    
                    data = json.loads(response.data)
                    assert data['data']['period'] == period
                    
    def test_price_history_invalid_city(self, client):
        response = client.get('/api/v1/price-history?city=')
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert data['error'] == 'Validation Error'
        assert 'city' in data['message'].lower()
        
    def test_price_history_no_data(self, client):
        with patch('src.api.endpoints.price_history.MongoDBHandler') as mock_db_class:
            with patch('src.api.endpoints.price_history.CacheManager') as mock_cache_class:
                mock_db = mock_db_class.return_value
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                mock_db.get_price_history.return_value = []
                
                response = client.get('/api/v1/price-history?city=Cidade Pequena')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                assert data['status'] == 'success'
                assert len(data['data']['history']) == 0
                assert data['data']['trend'] == 'insufficient_data'
                assert data['data']['growth_percentage'] == 0
            
    def test_price_history_cache_behavior(self, client):
        with patch('src.api.endpoints.price_history.CacheManager') as mock_cache_class:
            # Test cache hit
            mock_cache = mock_cache_class.return_value
            cached_data = {
                'history': [{'date': '2024-01-01', 'avg_price': 450000}],
                'trend': 'up',
                'growth_percentage': 5.2
            }
            mock_cache.get.return_value = cached_data
            
            response = client.get('/api/v1/price-history?city=São Paulo')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['meta']['cache_hit'] is True
            
            # Test cache miss
            mock_cache.get.return_value = None
            
            with patch('src.api.endpoints.price_history.MongoDBHandler') as mock_db_class:
                mock_db = mock_db_class.return_value
                mock_db.get_price_history.return_value = []
                
                response = client.get('/api/v1/price-history?city=Rio de Janeiro')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                assert data['meta']['cache_hit'] is False
                
                # Verify cache was set
                mock_cache.set.assert_called()
                
    def test_price_history_data_processing(self, client):
        with patch('src.api.endpoints.price_history.MongoDBHandler') as mock_db_class:
            with patch('src.api.endpoints.price_history.CacheManager') as mock_cache_class:
                mock_db = mock_db_class.return_value
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                # Mock data with clear trend
                history_data = [
                    {
                        'date': '2024-01-01',
                        'city': 'São Paulo',
                        'avg_price': 400000,
                        'min_price': 200000,
                        'max_price': 800000,
                        'total_properties': 1000,
                        'avg_price_per_sqm': 6000
                    },
                    {
                        'date': '2024-02-01',
                        'city': 'São Paulo',
                        'avg_price': 420000,
                        'min_price': 210000,
                        'max_price': 840000,
                        'total_properties': 1100,
                        'avg_price_per_sqm': 6300
                    },
                    {
                        'date': '2024-03-01',
                        'city': 'São Paulo',
                        'avg_price': 440000,
                        'min_price': 220000,
                        'max_price': 880000,
                        'total_properties': 1200,
                        'avg_price_per_sqm': 6600
                    }
                ]
                mock_db.get_price_history.return_value = history_data
                
                response = client.get('/api/v1/price-history?city=São Paulo&period=all')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                
                # Check trend analysis
                assert data['data']['trend'] == 'up'
                assert data['data']['growth_percentage'] == 10.0  # (440000-400000)/400000 * 100
                
                # Check chart data formatting
                assert 'chart_data' in data['data']
                chart = data['data']['chart_data']
                assert 'labels' in chart
                assert 'datasets' in chart
                assert len(chart['labels']) == 3
                assert chart['datasets'][0]['label'] == 'Average Price'
                
                # Check statistics
                assert 'statistics' in data['data']
                stats = data['data']['statistics']
                assert 'current_avg_price' in stats
                assert 'previous_avg_price' in stats
                assert 'price_volatility' in stats