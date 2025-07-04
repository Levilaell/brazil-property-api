"""
Test configuration and fixtures for the Brazil Property API.
"""
import pytest
import mongomock
import fakeredis
from unittest.mock import Mock, patch
from flask import Flask
from typing import Dict, Any, List
import json
import os


# Test data fixtures
@pytest.fixture
def sample_property_data():
    """Sample property data for testing."""
    return {
        "id": "prop_12345",
        "title": "Apartamento 3 quartos em Copacabana",
        "price": 800000,
        "size": 120,
        "bedrooms": 3,
        "bathrooms": 2,
        "city": "Rio de Janeiro",
        "neighborhood": "Copacabana",
        "address": "Rua Barata Ribeiro, 123",
        "features": ["varanda", "portaria", "piscina"],
        "description": "Apartamento com vista para o mar",
        "images": ["image1.jpg", "image2.jpg"],
        "source": "zap",
        "url": "https://www.zapimoveis.com.br/imovel/123456",
        "created_at": "2024-01-01T10:00:00Z",
        "updated_at": "2024-01-01T10:00:00Z"
    }


@pytest.fixture
def sample_properties_list():
    """List of sample properties for testing."""
    return [
        {
            "id": "prop_001",
            "title": "Casa 4 quartos Ipanema",
            "price": 1200000,
            "size": 200,
            "bedrooms": 4,
            "bathrooms": 3,
            "city": "Rio de Janeiro",
            "neighborhood": "Ipanema",
            "source": "zap"
        },
        {
            "id": "prop_002", 
            "title": "Apartamento 2 quartos Leblon",
            "price": 900000,
            "size": 90,
            "bedrooms": 2,
            "bathrooms": 2,
            "city": "Rio de Janeiro",
            "neighborhood": "Leblon",
            "source": "vivareal"
        },
        {
            "id": "prop_003",
            "title": "Cobertura 3 quartos Barra",
            "price": 1500000,
            "size": 150,
            "bedrooms": 3,
            "bathrooms": 3,
            "city": "Rio de Janeiro",
            "neighborhood": "Barra da Tijuca",
            "source": "zap"
        }
    ]


@pytest.fixture
def sample_search_filters():
    """Sample search filters for testing."""
    return {
        "city": "Rio de Janeiro",
        "min_price": 500000,
        "max_price": 1000000,
        "min_size": 80,
        "max_size": 150,
        "bedrooms": 2,
        "neighborhoods": ["Copacabana", "Ipanema"]
    }


@pytest.fixture
def sample_price_history():
    """Sample price history data for testing."""
    return [
        {
            "date": "2024-01-01",
            "avg_price": 750000,
            "min_price": 500000,
            "max_price": 1200000,
            "total_properties": 150,
            "neighborhood": "Copacabana"
        },
        {
            "date": "2024-02-01",
            "avg_price": 780000,
            "min_price": 520000,
            "max_price": 1250000,
            "total_properties": 142,
            "neighborhood": "Copacabana"
        }
    ]


# Database fixtures
@pytest.fixture
def mock_mongodb():
    """Mock MongoDB client for testing."""
    with patch('pymongo.MongoClient') as mock_client:
        mock_db = mongomock.MongoClient().test_db
        mock_client.return_value = mock_db
        yield mock_db


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    return fakeredis.FakeRedis()


# HTTP fixtures
@pytest.fixture
def mock_requests():
    """Mock requests for HTTP testing."""
    with patch('requests.Session') as mock_session:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Sample HTML</body></html>"
        mock_response.json.return_value = {"status": "success"}
        mock_session.return_value.get.return_value = mock_response
        mock_session.return_value.post.return_value = mock_response
        yield mock_session


# Flask app fixtures
@pytest.fixture
def app():
    """Create a Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


# Configuration fixtures
@pytest.fixture
def test_config():
    """Test configuration settings."""
    return {
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "MONGODB_URL": "mongodb://localhost:27017/test_db",
        "REDIS_URL": "redis://localhost:6379/0",
        "CACHE_TTL": 300,
        "RATE_LIMIT_PER_MINUTE": 60,
        "DEBUG": False
    }


@pytest.fixture
def environment_variables():
    """Set test environment variables."""
    env_vars = {
        "FLASK_ENV": "testing",
        "MONGODB_URL": "mongodb://localhost:27017/test_db",
        "REDIS_URL": "redis://localhost:6379/0",
        "SECRET_KEY": "test-secret-key"
    }
    
    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = value
    
    yield env_vars
    
    # Clean up environment variables
    for key in env_vars.keys():
        if key in os.environ:
            del os.environ[key]


# HTML fixtures for scraper testing
@pytest.fixture
def zap_html_sample():
    """Sample ZAP HTML for scraper testing."""
    return '''
    <html>
        <body>
            <div class="listing-item">
                <h2 class="listing-title">Apartamento 3 quartos</h2>
                <span class="listing-price">R$ 800.000</span>
                <span class="listing-size">120m²</span>
                <span class="listing-bedrooms">3 quartos</span>
                <span class="listing-bathrooms">2 banheiros</span>
                <span class="listing-address">Copacabana, Rio de Janeiro</span>
            </div>
        </body>
    </html>
    '''


@pytest.fixture
def vivareal_html_sample():
    """Sample VivaReal HTML for scraper testing."""
    return '''
    <html>
        <body>
            <div class="property-card">
                <h3 class="property-title">Casa 4 quartos Ipanema</h3>
                <div class="property-price">R$ 1.200.000</div>
                <div class="property-details">
                    <span class="area">200m²</span>
                    <span class="rooms">4 quartos</span>
                    <span class="bathrooms">3 banheiros</span>
                </div>
                <div class="property-location">Ipanema, Rio de Janeiro</div>
            </div>
        </body>
    </html>
    '''


# Parametrized fixtures for comprehensive testing
@pytest.fixture(params=[
    {"city": "Rio de Janeiro", "neighborhood": "Copacabana"},
    {"city": "São Paulo", "neighborhood": "Vila Madalena"},
    {"city": "Belo Horizonte", "neighborhood": "Savassi"}
])
def city_neighborhood_combinations(request):
    """Different city/neighborhood combinations for testing."""
    return request.param


@pytest.fixture(params=[
    {"min_price": 300000, "max_price": 600000},
    {"min_price": 600000, "max_price": 1000000},
    {"min_price": 1000000, "max_price": 2000000}
])
def price_range_combinations(request):
    """Different price range combinations for testing."""
    return request.param


# Markers for different test types
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests"
    )
    config.addinivalue_line(
        "markers", "slow: Slow running tests"
    )