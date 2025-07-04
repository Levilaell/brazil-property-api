"""
Test utilities and helper functions.
"""
import json
import random
import string
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch


def generate_random_string(length: int = 10) -> str:
    """Generate a random string of specified length."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_random_property_id() -> str:
    """Generate a random property ID."""
    return f"prop_{generate_random_string(8)}"


def generate_mock_property(
    city: str = "Rio de Janeiro",
    neighborhood: str = "Copacabana",
    price: int = None,
    size: int = None,
    bedrooms: int = None
) -> Dict[str, Any]:
    """Generate a mock property with optional parameters."""
    return {
        "id": generate_random_property_id(),
        "title": f"Apartamento {bedrooms or random.randint(1, 4)} quartos em {neighborhood}",
        "price": price or random.randint(300000, 2000000),
        "size": size or random.randint(50, 300),
        "bedrooms": bedrooms or random.randint(1, 4),
        "bathrooms": random.randint(1, 3),
        "city": city,
        "neighborhood": neighborhood,
        "address": f"Rua {generate_random_string(10)}, {random.randint(1, 999)}",
        "features": random.sample(["varanda", "portaria", "piscina", "academia", "churrasqueira"], 
                                 random.randint(1, 3)),
        "description": f"Imóvel em {neighborhood} com excelente localização",
        "images": [f"image_{i}.jpg" for i in range(random.randint(1, 5))],
        "source": random.choice(["zap", "vivareal"]),
        "url": f"https://example.com/property/{generate_random_string(8)}",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }


def generate_mock_properties(count: int = 10, **kwargs) -> List[Dict[str, Any]]:
    """Generate a list of mock properties."""
    return [generate_mock_property(**kwargs) for _ in range(count)]


def generate_mock_price_history(
    days: int = 30,
    neighborhood: str = "Copacabana"
) -> List[Dict[str, Any]]:
    """Generate mock price history data."""
    history = []
    base_price = 750000
    
    for i in range(days):
        date = datetime.now() - timedelta(days=days - i)
        # Add some randomness to the prices
        variation = random.uniform(-0.1, 0.1)
        avg_price = int(base_price * (1 + variation))
        
        history.append({
            "date": date.strftime("%Y-%m-%d"),
            "avg_price": avg_price,
            "min_price": int(avg_price * 0.7),
            "max_price": int(avg_price * 1.5),
            "total_properties": random.randint(100, 200),
            "neighborhood": neighborhood
        })
    
    return history


def mock_http_response(
    status_code: int = 200,
    text: str = None,
    json_data: Dict[str, Any] = None
) -> Mock:
    """Create a mock HTTP response."""
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.text = text or "<html><body>Mock HTML</body></html>"
    mock_response.json.return_value = json_data or {"status": "success"}
    return mock_response


def mock_database_collection(initial_data: List[Dict[str, Any]] = None) -> Mock:
    """Create a mock database collection."""
    mock_collection = Mock()
    data = initial_data or []
    
    def find_side_effect(query=None):
        if query:
            # Simple query matching for testing
            if 'city' in query:
                return [item for item in data if item.get('city') == query['city']]
        return data
    
    mock_collection.find.side_effect = find_side_effect
    mock_collection.insert_one.side_effect = lambda doc: data.append(doc)
    mock_collection.insert_many.side_effect = lambda docs: data.extend(docs)
    mock_collection.count_documents.return_value = len(data)
    
    return mock_collection


def mock_cache_client(initial_data: Dict[str, Any] = None) -> Mock:
    """Create a mock cache client."""
    mock_cache = Mock()
    cache_data = initial_data or {}
    
    def get_side_effect(key):
        return cache_data.get(key)
    
    def set_side_effect(key, value, ex=None):
        cache_data[key] = value
        return True
    
    mock_cache.get.side_effect = get_side_effect
    mock_cache.set.side_effect = set_side_effect
    mock_cache.delete.side_effect = lambda key: cache_data.pop(key, None)
    mock_cache.exists.side_effect = lambda key: key in cache_data
    
    return mock_cache


def assert_property_structure(property_data: Dict[str, Any]):
    """Assert that a property has the expected structure."""
    required_fields = [
        'id', 'title', 'price', 'size', 'bedrooms', 'bathrooms',
        'city', 'neighborhood', 'address', 'source'
    ]
    
    for field in required_fields:
        assert field in property_data, f"Property missing required field: {field}"
    
    # Assert data types
    assert isinstance(property_data['price'], (int, float)), "Price must be numeric"
    assert isinstance(property_data['size'], (int, float)), "Size must be numeric"
    assert isinstance(property_data['bedrooms'], int), "Bedrooms must be integer"
    assert isinstance(property_data['bathrooms'], int), "Bathrooms must be integer"
    assert isinstance(property_data['features'], list), "Features must be a list"


def assert_api_response_structure(response_data: Dict[str, Any]):
    """Assert that an API response has the expected structure."""
    assert 'status' in response_data, "Response missing status field"
    assert 'data' in response_data, "Response missing data field"
    assert response_data['status'] in ['success', 'error'], "Invalid status value"


def load_test_data(filename: str) -> Dict[str, Any]:
    """Load test data from JSON file."""
    try:
        with open(f'tests/fixtures/{filename}', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_test_data(filename: str, data: Dict[str, Any]):
    """Save test data to JSON file."""
    with open(f'tests/fixtures/{filename}', 'w') as f:
        json.dump(data, f, indent=2)


class MockScraperResponse:
    """Mock scraper response for testing."""
    
    def __init__(self, properties: List[Dict[str, Any]], total_pages: int = 1):
        self.properties = properties
        self.total_pages = total_pages
        self.current_page = 1
        self.has_next_page = total_pages > 1
        self.success = True
        self.error_message = None
    
    def __len__(self):
        return len(self.properties)
    
    def __iter__(self):
        return iter(self.properties)


class MockDatabaseConnection:
    """Mock database connection for testing."""
    
    def __init__(self):
        self.connected = True
        self.collections = {}
    
    def get_collection(self, name: str):
        if name not in self.collections:
            self.collections[name] = []
        return self.collections[name]
    
    def close(self):
        self.connected = False


class MockCacheConnection:
    """Mock cache connection for testing."""
    
    def __init__(self):
        self.connected = True
        self.data = {}
    
    def get(self, key: str):
        return self.data.get(key)
    
    def set(self, key: str, value: Any, ttl: int = None):
        self.data[key] = value
        return True
    
    def delete(self, key: str):
        return self.data.pop(key, None) is not None
    
    def flush(self):
        self.data.clear()
    
    def close(self):
        self.connected = False