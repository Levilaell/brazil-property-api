"""
Tests for VivaReal Scraper - Phase 4 of TDD Development.
Following TDD approach - write tests first, then implement.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from src.scrapers import VivaRealScraper
from src.scrapers.exceptions import ScraperParsingError, ScraperDataError
from src.config import DevelopmentConfig


@pytest.mark.unit
class TestVivaRealScraper:
    """Test VivaReal scraper functionality."""
    
    def test_vivareal_scraper_initialization(self):
        """Test VivaReal scraper initialization."""
        config = DevelopmentConfig()
        scraper = VivaRealScraper(config)
        
        assert scraper.config == config
        assert scraper.name == "VivaRealScraper"
        assert scraper.base_url == "https://www.vivareal.com.br"
        assert scraper.session is not None
    
    def test_build_search_url_basic(self):
        """Test building basic search URL."""
        config = DevelopmentConfig()
        scraper = VivaRealScraper(config)
        
        search_params = {
            'city': 'Rio de Janeiro',
            'state': 'RJ',
            'transaction_type': 'venda'
        }
        
        url = scraper.build_search_url(search_params)
        
        assert scraper.base_url in url
        assert 'rio-de-janeiro' in url.lower()
        assert 'venda' in url.lower()
    
    def test_build_search_url_with_filters(self):
        """Test building search URL with filters."""
        config = DevelopmentConfig()
        scraper = VivaRealScraper(config)
        
        search_params = {
            'city': 'São Paulo',
            'state': 'SP',
            'transaction_type': 'venda',
            'price_min': 500000,
            'price_max': 1000000,
            'bedrooms': 3,
            'property_type': 'apartamento'
        }
        
        url = scraper.build_search_url(search_params)
        
        assert scraper.base_url in url
        assert 'sao-paulo' in url.lower()
        assert 'apartamento' in url.lower()
    
    def test_build_search_url_with_pagination(self):
        """Test building search URL with pagination."""
        config = DevelopmentConfig()
        scraper = VivaRealScraper(config)
        
        search_params = {
            'city': 'Rio de Janeiro',
            'state': 'RJ',
            'transaction_type': 'venda',
            'page': 3
        }
        
        url = scraper.build_search_url(search_params)
        
        assert '#pagina=3' in url or 'page=3' in url
    
    @patch('src.scrapers.vivareal_scraper.VivaRealScraper.make_request')
    def test_get_total_pages_success(self, mock_request):
        """Test getting total pages successfully."""
        config = DevelopmentConfig()
        scraper = VivaRealScraper(config)
        
        # Mock HTML response with pagination
        mock_html = """
        <html>
            <body>
                <div class="results-summary">
                    <span>Página 1 de 8 páginas</span>
                </div>
                <nav class="pagination">
                    <button>1</button>
                    <button>2</button>
                    <button>3</button>
                    <span>...</span>
                    <button>8</button>
                </nav>
            </body>
        </html>
        """
        
        mock_response = Mock()
        mock_response.text = mock_html
        mock_request.return_value = mock_response
        
        search_params = {'city': 'Rio de Janeiro', 'state': 'RJ'}
        pages = scraper.get_total_pages(search_params)
        
        assert pages == 8
    
    @patch('src.scrapers.vivareal_scraper.VivaRealScraper.make_request')
    def test_get_total_pages_no_pagination(self, mock_request):
        """Test getting total pages when no pagination exists."""
        config = DevelopmentConfig()
        scraper = VivaRealScraper(config)
        
        # Mock HTML response without pagination
        mock_html = """
        <html>
            <body>
                <div class="listing-wrapper">
                    <article class="property-card">Property 1</article>
                    <article class="property-card">Property 2</article>
                </div>
            </body>
        </html>
        """
        
        mock_response = Mock()
        mock_response.text = mock_html
        mock_request.return_value = mock_response
        
        search_params = {'city': 'Rio de Janeiro', 'state': 'RJ'}
        pages = scraper.get_total_pages(search_params)
        
        assert pages == 1
    
    def test_extract_property_data_success(self):
        """Test extracting property data successfully."""
        config = DevelopmentConfig()
        scraper = VivaRealScraper(config)
        
        # Mock property HTML with VivaReal structure
        property_html = """
        <article class="property-card">
            <h3 class="property-card__title">Apartamento com 3 quartos à venda em Ipanema</h3>
            <div class="property-card__price">R$ 850.000</div>
            <span class="property-card__address">Rua Visconde de Pirajá, 500 - Ipanema, Rio de Janeiro</span>
            <ul class="property-card__details">
                <li class="property-card__detail-room">3 quartos</li>
                <li class="property-card__detail-bathroom">2 banheiros</li>
                <li class="property-card__detail-area">100 m²</li>
                <li class="property-card__detail-parking">1 vaga</li>
            </ul>
            <a href="/imovel/apartamento-ipanema-654321" class="property-card__link">Ver imóvel</a>
        </article>
        """
        
        soup = BeautifulSoup(property_html, 'html.parser')
        property_data = scraper.extract_property_data(soup)
        
        assert property_data['title'] == "Apartamento com 3 quartos à venda em Ipanema"
        assert property_data['price'] == 850000
        assert 'Ipanema' in property_data['address']
        assert property_data['bedrooms'] == 3
        assert property_data['bathrooms'] == 2
        assert property_data['size'] == 100
        assert property_data['source'] == 'VivaReal'
    
    def test_extract_property_data_missing_elements(self):
        """Test extracting property data with missing elements."""
        config = DevelopmentConfig()
        scraper = VivaRealScraper(config)
        
        # Mock incomplete property HTML
        property_html = """
        <article class="property-card">
            <h3 class="property-card__title">Casa sem informações completas</h3>
            <span class="property-card__address">Endereço qualquer</span>
        </article>
        """
        
        soup = BeautifulSoup(property_html, 'html.parser')
        
        with pytest.raises(ScraperParsingError):
            scraper.extract_property_data(soup)
    
    @patch('src.scrapers.vivareal_scraper.VivaRealScraper.make_request')
    def test_scrape_properties_success(self, mock_request):
        """Test scraping properties successfully."""
        config = DevelopmentConfig()
        scraper = VivaRealScraper(config)
        
        # Mock search results HTML
        mock_html = """
        <html>
            <body>
                <div class="listing-wrapper">
                    <article class="property-card">
                        <h3 class="property-card__title">Apartamento 1</h3>
                        <div class="property-card__price">R$ 600.000</div>
                        <span class="property-card__address">Endereço 1 - Bairro 1, Rio de Janeiro</span>
                        <ul class="property-card__details">
                            <li class="property-card__detail-room">2 quartos</li>
                            <li class="property-card__detail-bathroom">1 banheiro</li>
                            <li class="property-card__detail-area">85 m²</li>
                        </ul>
                        <a href="/imovel/apartamento-1" class="property-card__link">Ver imóvel</a>
                    </article>
                    <article class="property-card">
                        <h3 class="property-card__title">Apartamento 2</h3>
                        <div class="property-card__price">R$ 780.000</div>
                        <span class="property-card__address">Endereço 2 - Bairro 2, Rio de Janeiro</span>
                        <ul class="property-card__details">
                            <li class="property-card__detail-room">3 quartos</li>
                            <li class="property-card__detail-bathroom">2 banheiros</li>
                            <li class="property-card__detail-area">110 m²</li>
                        </ul>
                        <a href="/imovel/apartamento-2" class="property-card__link">Ver imóvel</a>
                    </article>
                </div>
            </body>
        </html>
        """
        
        mock_response = Mock()
        mock_response.text = mock_html
        mock_request.return_value = mock_response
        
        search_params = {'city': 'Rio de Janeiro', 'state': 'RJ'}
        properties = scraper.scrape_properties(search_params)
        
        assert len(properties) == 2
        assert properties[0]['title'] == "Apartamento 1"
        assert properties[0]['price'] == 600000
        assert properties[1]['title'] == "Apartamento 2"
        assert properties[1]['price'] == 780000
    
    def test_normalize_city_name(self):
        """Test city name normalization for VivaReal URLs."""
        config = DevelopmentConfig()
        scraper = VivaRealScraper(config)
        
        # Test various city names
        assert scraper.normalize_city_name("São Paulo") == "sao-paulo"
        assert scraper.normalize_city_name("Rio de Janeiro") == "rio-de-janeiro"
        assert scraper.normalize_city_name("Belo Horizonte") == "belo-horizonte"
        assert scraper.normalize_city_name("Brasília") == "brasilia"
    
    def test_parse_price_variations(self):
        """Test parsing different price formats."""
        config = DevelopmentConfig()
        scraper = VivaRealScraper(config)
        
        # Test various price formats from VivaReal
        assert scraper.parse_price("R$ 850.000") == 850000
        assert scraper.parse_price("R$ 1.350.000") == 1350000
        assert scraper.parse_price("850.000") == 850000
        assert scraper.parse_price("R$ 850 mil") == 850000
        assert scraper.parse_price("Consulte valor") is None
    
    def test_extract_property_id(self):
        """Test extracting property ID from URL."""
        config = DevelopmentConfig()
        scraper = VivaRealScraper(config)
        
        # Test various URL formats from VivaReal
        assert scraper.extract_property_id("/imovel/apartamento-ipanema-654321") == "vivareal_654321"
        assert scraper.extract_property_id("/imovel/casa-leblon-789012/") == "vivareal_789012"
        assert scraper.extract_property_id("/property/345678") == "vivareal_345678"
    
    def test_extract_neighborhood_from_address(self):
        """Test extracting neighborhood from address."""
        config = DevelopmentConfig()
        scraper = VivaRealScraper(config)
        
        # Test various address formats
        address1 = "Rua Visconde de Pirajá, 500 - Ipanema, Rio de Janeiro"
        assert scraper.extract_neighborhood(address1) == "Ipanema"
        
        address2 = "Avenida Paulista, 1500, Bela Vista, São Paulo"
        assert scraper.extract_neighborhood(address2) == "Bela Vista"
        
        address3 = "Rua das Palmeiras, 200 - Botafogo - Rio de Janeiro"
        assert scraper.extract_neighborhood(address3) == "Botafogo"
    
    @patch('src.scrapers.vivareal_scraper.VivaRealScraper.make_request')
    def test_scrape_properties_error_handling(self, mock_request):
        """Test error handling during scraping."""
        config = DevelopmentConfig()
        scraper = VivaRealScraper(config)
        
        # Mock request that raises an exception
        mock_request.side_effect = requests.ConnectionError("Connection failed")
        
        search_params = {'city': 'Rio de Janeiro', 'state': 'RJ'}
        
        # Should handle the error gracefully and return empty list
        properties = scraper.scrape_properties(search_params)
        assert properties == []
    
    def test_validate_search_params(self):
        """Test search parameters validation."""
        config = DevelopmentConfig()
        scraper = VivaRealScraper(config)
        
        # Valid parameters
        valid_params = {
            'city': 'Rio de Janeiro',
            'state': 'RJ',
            'transaction_type': 'venda'
        }
        assert scraper.validate_search_params(valid_params) is True
        
        # Missing required parameters
        invalid_params = {
            'city': 'Rio de Janeiro'
            # Missing state and transaction_type
        }
        assert scraper.validate_search_params(invalid_params) is False
    
    def test_get_property_details_url(self):
        """Test building property details URL."""
        config = DevelopmentConfig()
        scraper = VivaRealScraper(config)
        
        relative_url = "/imovel/apartamento-ipanema-654321"
        full_url = scraper.get_property_details_url(relative_url)
        
        assert full_url == "https://www.vivareal.com.br/imovel/apartamento-ipanema-654321"
    
    def test_extract_property_features(self):
        """Test extracting additional property features."""
        config = DevelopmentConfig()
        scraper = VivaRealScraper(config)
        
        # Test VivaReal specific feature extraction
        features_html = """
        <ul class="property-card__details">
            <li class="property-card__detail-room">3 quartos</li>
            <li class="property-card__detail-bathroom">2 banheiros</li>
            <li class="property-card__detail-area">100 m²</li>
            <li class="property-card__detail-parking">2 vagas</li>
            <li class="property-card__detail-feature">Piscina</li>
            <li class="property-card__detail-feature">Academia</li>
        </ul>
        """
        
        soup = BeautifulSoup(features_html, 'html.parser')
        features = scraper.extract_property_features(soup)
        
        assert features['bedrooms'] == 3
        assert features['bathrooms'] == 2
        assert features['size'] == 100
        assert features['parking_spaces'] == 2
        assert 'Piscina' in features['amenities']
        assert 'Academia' in features['amenities']
    
    def test_scraper_stats_tracking(self):
        """Test that scraper tracks statistics correctly."""
        config = DevelopmentConfig()
        scraper = VivaRealScraper(config)
        
        # Initial stats
        stats = scraper.get_stats()
        assert stats['requests_made'] == 0
        assert stats['properties_found'] == 0
        
        # Update stats manually (would normally happen during scraping)
        scraper.update_stats('requests_made', 3)
        scraper.update_stats('properties_found', 18)
        
        stats = scraper.get_stats()
        assert stats['requests_made'] == 3
        assert stats['properties_found'] == 18