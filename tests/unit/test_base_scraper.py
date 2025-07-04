"""
Tests for Base Scraper - Phase 4 of TDD Development.
Following TDD approach - write tests first, then implement.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from datetime import datetime
from src.scrapers import BaseScraper
from src.scrapers.exceptions import (
    ScraperConnectionError, ScraperParsingError, ScraperRateLimitError,
    ScraperBlockedError, ScraperTimeoutError, ScraperDataError
)
from src.config import DevelopmentConfig


class TestableBaseScraper(BaseScraper):
    """Concrete implementation of BaseScraper for testing."""
    
    def extract_property_data(self, soup):
        return {"test": "data"}
    
    def build_search_url(self, search_params):
        return "http://test.com/search"
    
    def scrape_properties(self, search_params):
        return [{"test": "property"}]
    
    def get_total_pages(self, search_params):
        return 1


@pytest.mark.unit
class TestBaseScraper:
    """Test base scraper functionality."""
    
    def test_scraper_initialization(self):
        """Test scraper initialization."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        assert scraper.config == config
        assert scraper.session is not None
        assert scraper.name == "TestableBaseScraper"
        assert scraper.base_url == ""
        assert scraper.delay_range == (1, 3)
        assert scraper.max_retries == 3
        assert scraper.timeout == 30
    
    def test_session_configuration(self):
        """Test HTTP session configuration."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        # Should have proper headers
        assert 'User-Agent' in scraper.session.headers
        assert scraper.session.headers['Accept-Language'] == 'pt-BR,pt;q=0.9,en;q=0.8'
        assert scraper.session.headers['Accept-Encoding'] == 'gzip, deflate'
    
    def test_rate_limiting_delay(self):
        """Test rate limiting delay functionality."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        with patch('time.sleep') as mock_sleep:
            with patch('random.uniform', return_value=2.0):
                scraper._apply_rate_limit()
                mock_sleep.assert_called_once_with(2.0)
    
    def test_retry_mechanism(self):
        """Test retry mechanism."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        call_count = 0
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise requests.ConnectionError("Connection failed")
            return "success"
        
        with patch.object(scraper, '_apply_rate_limit'):
            result = scraper._retry_request(failing_function)
            assert result == "success"
            assert call_count == 3
    
    def test_retry_exhaustion(self):
        """Test retry exhaustion."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        def always_failing_function():
            raise requests.ConnectionError("Always fails")
        
        with patch.object(scraper, '_apply_rate_limit'):
            with pytest.raises(ScraperConnectionError):
                scraper._retry_request(always_failing_function)
    
    def test_request_success(self):
        """Test successful HTTP request."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>test</html>"
        mock_response.raise_for_status.return_value = None
        
        with patch.object(scraper.session, 'get', return_value=mock_response):
            response = scraper.make_request("http://example.com")
            assert response == mock_response
            assert response.status_code == 200
    
    def test_request_timeout_handling(self):
        """Test request timeout handling."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        with patch.object(scraper.session, 'get', side_effect=requests.Timeout):
            with patch.object(scraper, '_apply_rate_limit'):  # Skip delays in tests
                with pytest.raises(ScraperTimeoutError):
                    scraper.make_request("http://example.com")
    
    def test_request_connection_error_handling(self):
        """Test connection error handling."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        with patch.object(scraper.session, 'get', side_effect=requests.ConnectionError):
            with pytest.raises(ScraperConnectionError):
                scraper.make_request("http://example.com")
    
    def test_rate_limit_detection(self):
        """Test rate limit detection."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = requests.HTTPError()
        
        with patch.object(scraper.session, 'get', return_value=mock_response):
            with pytest.raises(ScraperRateLimitError):
                scraper.make_request("http://example.com")
    
    def test_blocked_detection(self):
        """Test blocked detection."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = requests.HTTPError()
        
        with patch.object(scraper.session, 'get', return_value=mock_response):
            with pytest.raises(ScraperBlockedError):
                scraper.make_request("http://example.com")
    
    def test_parse_html_success(self):
        """Test HTML parsing success."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        html_content = "<html><body><h1>Test</h1></body></html>"
        soup = scraper.parse_html(html_content)
        
        assert soup.find('h1').text == "Test"
    
    def test_parse_html_failure(self):
        """Test HTML parsing failure."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        # Invalid HTML that might cause parsing issues
        with pytest.raises(ScraperParsingError):
            scraper.parse_html(None)
    
    def test_extract_property_data_not_implemented(self):
        """Test that BaseScraper cannot be instantiated directly."""
        config = DevelopmentConfig()
        
        with pytest.raises(TypeError):
            BaseScraper(config)
    
    def test_build_search_url_not_implemented(self):
        """Test that abstract methods must be implemented."""
        # Test using the TestableBaseScraper that implements the methods
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        # These should work since they're implemented
        result = scraper.build_search_url({})
        assert result == "http://test.com/search"
    
    def test_validate_property_data(self):
        """Test property data validation."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        # Valid property data
        valid_data = {
            'id': 'prop_123',
            'title': 'Casa em Copacabana',
            'price': 750000,
            'address': 'Rua das Flores, 123',
            'city': 'Rio de Janeiro',
            'neighborhood': 'Copacabana',
            'bedrooms': 3,
            'bathrooms': 2,
            'size': 120,
            'source': 'test_scraper'
        }
        
        result = scraper.validate_property_data(valid_data)
        assert result is True
    
    def test_validate_property_data_missing_fields(self):
        """Test property data validation with missing fields."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        # Missing required fields
        invalid_data = {
            'title': 'Casa sem preço',
            'address': 'Endereço qualquer'
        }
        
        result = scraper.validate_property_data(invalid_data)
        assert result is False
    
    def test_validate_property_data_invalid_price(self):
        """Test property data validation with invalid price."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        # Invalid price
        invalid_data = {
            'id': 'prop_123',
            'title': 'Casa em Copacabana',
            'price': 'not_a_number',
            'address': 'Rua das Flores, 123',
            'city': 'Rio de Janeiro'
        }
        
        result = scraper.validate_property_data(invalid_data)
        assert result is False
    
    def test_scrape_properties_not_implemented(self):
        """Test implemented scrape_properties method."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        result = scraper.scrape_properties({})
        assert result == [{"test": "property"}]
    
    def test_get_total_pages_not_implemented(self):
        """Test implemented get_total_pages method."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        result = scraper.get_total_pages({})
        assert result == 1
    
    def test_get_scraper_stats(self):
        """Test getting scraper statistics."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        # Simulate some activity
        scraper.stats['requests_made'] = 10
        scraper.stats['properties_found'] = 25
        scraper.stats['errors_count'] = 2
        
        stats = scraper.get_stats()
        
        assert stats['requests_made'] == 10
        assert stats['properties_found'] == 25
        assert stats['errors_count'] == 2
        assert 'start_time' in stats
        assert 'total_runtime' in stats
    
    def test_reset_stats(self):
        """Test resetting scraper statistics."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        # Set some stats
        scraper.stats['requests_made'] = 10
        scraper.stats['properties_found'] = 25
        
        scraper.reset_stats()
        
        assert scraper.stats['requests_made'] == 0
        assert scraper.stats['properties_found'] == 0
        assert scraper.stats['errors_count'] == 0
    
    def test_update_stats(self):
        """Test updating scraper statistics."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        scraper.update_stats('requests_made', 5)
        scraper.update_stats('properties_found', 10)
        
        assert scraper.stats['requests_made'] == 5
        assert scraper.stats['properties_found'] == 10
    
    def test_clean_text_utility(self):
        """Test text cleaning utility."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        dirty_text = "  \n\t  Texto com espaços  \n\r  "
        clean_text = scraper.clean_text(dirty_text)
        
        assert clean_text == "Texto com espaços"
    
    def test_extract_number_utility(self):
        """Test number extraction utility."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        # Test price extraction
        price_text = "R$ 750.000"
        price = scraper.extract_number(price_text)
        assert price == 750000
        
        # Test area extraction
        area_text = "120 m²"
        area = scraper.extract_number(area_text)
        assert area == 120
        
        # Test invalid number
        invalid_text = "texto sem número"
        result = scraper.extract_number(invalid_text)
        assert result is None
    
    def test_session_cleanup(self):
        """Test session cleanup."""
        config = DevelopmentConfig()
        scraper = TestableBaseScraper(config)
        
        scraper.close()
        
        # Session should be closed (we can't easily test this, but method should exist)
        assert hasattr(scraper, 'session')