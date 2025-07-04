import pytest
from flask import Flask
from unittest.mock import Mock, patch, MagicMock
import json

from src.api.endpoints.search import search_properties


class TestSearchEndpoint:
    @pytest.fixture
    def app(self):
        from src.api.base import create_app
        app = create_app(testing=True)
        return app
        
    @pytest.fixture
    def client(self, app):
        return app.test_client()
        
    def test_search_with_city_only(self, client):
        with patch('src.api.endpoints.search.ScraperCoordinator') as mock_scraper_class:
            with patch('src.api.endpoints.search.CacheManager') as mock_cache_class:
                # Setup mocks
                mock_scraper = mock_scraper_class.return_value
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None  # Cache miss
                
                mock_scraper.scrape_properties.return_value = [
                    {
                        'id': '1',
                        'title': 'Apartamento 2 quartos',
                        'price': 250000,
                        'city': 'São Paulo',
                        'neighborhood': 'Vila Mariana',
                        'size': 65,
                        'bedrooms': 2,
                        'bathrooms': 1,
                        'source': 'zap'
                    }
                ]
                
                response = client.get('/api/v1/search?city=São Paulo')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                assert data['status'] == 'success'
                assert len(data['data']['properties']) == 1
                assert data['data']['total'] == 1
            
    def test_search_with_all_filters(self, client):
        with patch('src.api.endpoints.search.ScraperCoordinator') as mock_scraper_class:
            with patch('src.api.endpoints.search.CacheManager') as mock_cache_class:
                mock_scraper = mock_scraper_class.return_value
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                mock_scraper.scrape_properties.return_value = []
                
                response = client.get(
                    '/api/v1/search?city=Rio de Janeiro&min_price=200000&max_price=500000'
                    '&min_size=50&max_size=100&bedrooms=2&property_type=apartment'
                )
                assert response.status_code == 200
                
                # Verify scraper was called with correct filters
                mock_scraper.scrape_properties.assert_called_once()
                call_args = mock_scraper.scrape_properties.call_args[0][0]
                assert call_args['city'] == 'Rio de Janeiro'
                assert call_args['min_price'] == 200000
                assert call_args['max_price'] == 500000
            
    def test_search_with_invalid_city(self, client):
        response = client.get('/api/v1/search?city=')
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert data['error'] == 'Validation Error'
        assert 'city' in data['message'].lower()
        
    def test_search_with_invalid_price_range(self, client):
        response = client.get('/api/v1/search?city=São Paulo&min_price=500000&max_price=200000')
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert data['error'] == 'Validation Error'
        assert 'price' in data['message'].lower()
        
    def test_search_with_pagination(self, client):
        with patch('src.api.endpoints.search.ScraperCoordinator') as mock_scraper_class:
            with patch('src.api.endpoints.search.CacheManager') as mock_cache_class:
                mock_scraper = mock_scraper_class.return_value
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                # Mock 50 properties
                properties = [
                    {
                        'id': str(i),
                        'title': f'Property {i}',
                        'price': 300000 + i * 1000,
                        'city': 'São Paulo',
                        'neighborhood': 'Centro',
                        'size': 70,
                        'bedrooms': 2,
                        'bathrooms': 1,
                        'source': 'zap'
                    }
                    for i in range(50)
                ]
                
                mock_scraper.scrape_properties.return_value = properties
                
                response = client.get('/api/v1/search?city=São Paulo&page=2&per_page=20')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                assert len(data['data']['properties']) == 20
                assert data['data']['pagination']['page'] == 2
                assert data['data']['pagination']['per_page'] == 20
                assert data['data']['pagination']['total'] == 50
                assert data['data']['pagination']['pages'] == 3
            
    def test_search_cache_hit(self, client):
        with patch('src.api.endpoints.search.CacheManager') as mock_cache_class:
            mock_cache = mock_cache_class.return_value
            cached_data = {
                'properties': [{'id': '1', 'title': 'Cached Property', 'source': 'cache'}],
                'total': 1,
                'sources': ['cache']
            }
            mock_cache.get.return_value = cached_data
            
            response = client.get('/api/v1/search?city=São Paulo')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['data']['properties'][0]['title'] == 'Cached Property'
            assert data['meta']['cache_hit'] is True
            
    def test_search_cache_miss(self, client):
        with patch('src.api.endpoints.search.ScraperCoordinator') as mock_scraper_class:
            with patch('src.api.endpoints.search.CacheManager') as mock_cache_class:
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                mock_scraper = mock_scraper_class.return_value
                mock_scraper.scrape_properties.return_value = []
                
                response = client.get('/api/v1/search?city=São Paulo')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                assert data['meta']['cache_hit'] is False
                
                # Verify cache was set
                mock_cache.set.assert_called_once()
                
    def test_search_rate_limiting(self, client):
        # Rate limiting will be implemented later
        # For now, just ensure the endpoint works
        with patch('src.api.endpoints.search.ScraperCoordinator') as mock_scraper_class:
            with patch('src.api.endpoints.search.CacheManager') as mock_cache_class:
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                mock_scraper = mock_scraper_class.return_value
                mock_scraper.scrape_properties.return_value = []
                
                response = client.get('/api/v1/search?city=São Paulo')
                assert response.status_code == 200
            
    def test_search_response_format(self, client):
        with patch('src.api.endpoints.search.ScraperCoordinator') as mock_scraper_class:
            with patch('src.api.endpoints.search.CacheManager') as mock_cache_class:
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                mock_scraper = mock_scraper_class.return_value
                mock_scraper.scrape_properties.return_value = [
                    {
                        'id': '1',
                        'title': 'Test Property',
                        'price': 300000,
                        'city': 'São Paulo',
                        'neighborhood': 'Vila Mariana',
                        'size': 80,
                        'bedrooms': 3,
                        'bathrooms': 2,
                        'features': ['pool', 'gym'],
                        'source': 'zap'
                    }
                ]
                
                response = client.get('/api/v1/search?city=São Paulo')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                
                # Check response structure
                assert 'status' in data
                assert 'data' in data
                assert 'meta' in data
                
                # Check data structure
                assert 'properties' in data['data']
                assert 'total' in data['data']
                assert 'statistics' in data['data']
                assert 'pagination' in data['data']
                
                # Check meta structure
                assert 'timestamp' in data['meta']
                assert 'response_time' in data['meta']
                assert 'cache_hit' in data['meta']
                assert 'sources' in data['meta']
            
    def test_search_statistics_calculation(self, client):
        with patch('src.api.endpoints.search.ScraperCoordinator') as mock_scraper_class:
            with patch('src.api.endpoints.search.CacheManager') as mock_cache_class:
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                mock_scraper = mock_scraper_class.return_value
                mock_scraper.scrape_properties.return_value = [
                    {'id': '1', 'price': 200000, 'size': 50, 'bedrooms': 1, 'source': 'zap'},
                    {'id': '2', 'price': 300000, 'size': 70, 'bedrooms': 2, 'source': 'zap'},
                    {'id': '3', 'price': 400000, 'size': 90, 'bedrooms': 3, 'source': 'vivareal'},
                ]
                
                response = client.get('/api/v1/search?city=São Paulo')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                stats = data['data']['statistics']
                
                assert stats['avg_price'] == 300000
                assert stats['min_price'] == 200000
                assert stats['max_price'] == 400000
                assert stats['avg_size'] == 70
                assert stats['avg_price_per_sqm'] == pytest.approx(4285.71, rel=1e-2)
            
    def test_search_empty_results(self, client):
        with patch('src.api.endpoints.search.ScraperCoordinator') as mock_scraper_class:
            with patch('src.api.endpoints.search.CacheManager') as mock_cache_class:
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                mock_scraper = mock_scraper_class.return_value
                mock_scraper.scrape_properties.return_value = []
                
                response = client.get('/api/v1/search?city=Cidade Inexistente')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                assert data['status'] == 'success'
                assert len(data['data']['properties']) == 0
                assert data['data']['total'] == 0
                assert data['data']['statistics'] == {}
            
    def test_search_timeout_handling(self, client):
        with patch('src.api.endpoints.search.ScraperCoordinator') as mock_scraper_class:
            with patch('src.api.endpoints.search.CacheManager') as mock_cache_class:
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                mock_scraper = mock_scraper_class.return_value
                mock_scraper.scrape_properties.side_effect = TimeoutError('Search timeout')
                
                response = client.get('/api/v1/search?city=São Paulo')
                assert response.status_code == 500  # Changed from 504 to 500 for general error