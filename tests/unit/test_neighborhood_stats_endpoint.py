import pytest
from flask import Flask
from unittest.mock import Mock, patch, MagicMock
import json

from src.api.endpoints.neighborhood_stats import get_neighborhood_stats


class TestNeighborhoodStatsEndpoint:
    @pytest.fixture
    def app(self):
        from src.api.base import create_app
        app = create_app(testing=True)
        return app
        
    @pytest.fixture
    def client(self, app):
        return app.test_client()
        
    def test_neighborhood_basic_stats(self, client):
        with patch('src.api.endpoints.neighborhood_stats.MongoDBHandler') as mock_db_class:
            with patch('src.api.endpoints.neighborhood_stats.CacheManager') as mock_cache_class:
                mock_db = mock_db_class.return_value
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                mock_db.calculate_neighborhood_stats.return_value = [
                    {
                        '_id': 'Vila Mariana',
                        'total_properties': 500,
                        'avg_price': 650000,
                        'min_price': 350000,
                        'max_price': 1200000,
                        'avg_size': 85
                    }
                ]
                
                response = client.get('/api/v1/neighborhood-stats?city=São Paulo&neighborhood=Vila Mariana')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                assert data['status'] == 'success'
                assert data['data']['neighborhood'] == 'Vila Mariana'
                assert data['data']['total_properties'] == 500
                assert data['data']['avg_price'] == 650000
                assert 'property_types' in data['data']
                assert 'bedroom_distribution' in data['data']
            
    def test_neighborhood_enriched_data(self, client):
        with patch('src.api.endpoints.neighborhood_stats.MongoDBHandler') as mock_db_class:
            with patch('src.api.endpoints.neighborhood_stats.CacheManager') as mock_cache_class:
                mock_db = mock_db_class.return_value
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                # Mock basic stats
                mock_db.calculate_neighborhood_stats.return_value = [
                    {
                        '_id': 'Pinheiros',
                        'avg_price': 750000,
                        'total_properties': 450,
                        'avg_size': 90
                    }
                ]
                
                response = client.get('/api/v1/neighborhood-stats?city=São Paulo&neighborhood=Pinheiros&enriched=true')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                assert 'walkability_score' in data['data']
                assert 'amenities' in data['data']
                assert 'demographics' in data['data']
                assert data['data']['walkability_score'] == 8.5
                
    def test_neighborhood_comparison(self, client):
        neighborhoods = ['Vila Mariana', 'Pinheiros', 'Moema']
        
        with patch('src.api.endpoints.neighborhood_stats.MongoDBHandler') as mock_db_class:
            with patch('src.api.endpoints.neighborhood_stats.CacheManager') as mock_cache_class:
                mock_db = mock_db_class.return_value
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                # Mock data for multiple neighborhoods
                mock_db.calculate_neighborhood_stats.return_value = [
                    {
                        '_id': 'Vila Mariana',
                        'avg_price': 650000,
                        'total_properties': 500,
                        'avg_size': 85
                    },
                    {
                        '_id': 'Pinheiros',
                        'avg_price': 750000,
                        'total_properties': 450,
                        'avg_size': 90
                    },
                    {
                        '_id': 'Moema',
                        'avg_price': 850000,
                        'total_properties': 400,
                        'avg_size': 95
                    }
                ]
                
                response = client.get(f'/api/v1/neighborhood-stats?city=São Paulo&neighborhood={",".join(neighborhoods)}&compare=true')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                assert 'comparison' in data['data']
                assert len(data['data']['comparison']) == 3
                
                # Check comparison includes rankings
                comparison = data['data']['comparison']
                assert all('price_rank' in n for n in comparison)
                assert all('value_score' in n for n in comparison)
            
    def test_walkability_score(self, client):
        with patch('src.api.endpoints.neighborhood_stats.MongoDBHandler') as mock_db_class:
            with patch('src.api.endpoints.neighborhood_stats.CacheManager') as mock_cache_class:
                mock_db = mock_db_class.return_value
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                mock_db.calculate_neighborhood_stats.return_value = [
                    {
                        '_id': 'Vila Mariana',
                        'avg_price': 650000,
                        'total_properties': 500,
                        'avg_size': 85
                    }
                ]
                
                response = client.get('/api/v1/neighborhood-stats?city=São Paulo&neighborhood=Vila Mariana&metrics=walkability')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                assert 'walkability' in data['data']
                assert data['data']['walkability']['score'] == 8.5
                assert data['data']['walkability']['category'] == 'Very Walkable'
                
    def test_safety_index(self, client):
        with patch('src.api.endpoints.neighborhood_stats.MongoDBHandler') as mock_db_class:
            with patch('src.api.endpoints.neighborhood_stats.CacheManager') as mock_cache_class:
                mock_db = mock_db_class.return_value
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                mock_db.calculate_neighborhood_stats.return_value = [
                    {
                        '_id': 'Moema',
                        'avg_price': 850000,
                        'total_properties': 400,
                        'avg_size': 95
                    }
                ]
                
                response = client.get('/api/v1/neighborhood-stats?city=São Paulo&neighborhood=Moema&metrics=safety')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                assert 'safety' in data['data']
                assert data['data']['safety']['index'] == 7.8
                assert data['data']['safety']['trend'] == 'improving'
                
    def test_infrastructure_rating(self, client):
        with patch('src.api.endpoints.neighborhood_stats.MongoDBHandler') as mock_db_class:
            with patch('src.api.endpoints.neighborhood_stats.CacheManager') as mock_cache_class:
                mock_db = mock_db_class.return_value
                mock_cache = mock_cache_class.return_value
                mock_cache.get.return_value = None
                
                mock_db.calculate_neighborhood_stats.return_value = [
                    {
                        '_id': 'Pinheiros',
                        'avg_price': 750000,
                        'total_properties': 450,
                        'avg_size': 90
                    }
                ]
                
                response = client.get('/api/v1/neighborhood-stats?city=São Paulo&neighborhood=Pinheiros&metrics=infrastructure')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                assert 'infrastructure' in data['data']
                assert data['data']['infrastructure']['overall_rating'] == 8.3
                assert 'categories' in data['data']['infrastructure']
                assert 'recent_improvements' in data['data']['infrastructure']