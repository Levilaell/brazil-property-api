"""
Tests for ZAP Scraper - Phase 4 of TDD Development.
Following TDD approach - write tests first, then implement.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from src.scrapers import ZapScraper
from src.scrapers.exceptions import ScraperParsingError, ScraperDataError
from src.config import DevelopmentConfig


@pytest.mark.unit
class TestZapScraper:
    """Test ZAP scraper functionality."""
    
    def test_zap_scraper_initialization(self):
        """Test ZAP scraper initialization."""
        config = DevelopmentConfig()
        scraper = ZapScraper(config)
        
        assert scraper.config == config
        assert scraper.name == "ZapScraper"
        assert scraper.base_url == "https://www.zapimoveis.com.br"
        assert scraper.session is not None
    
    def test_build_search_url_basic(self):
        """Test building basic search URL."""
        config = DevelopmentConfig()
        scraper = ZapScraper(config)
        
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
        scraper = ZapScraper(config)
        
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
        scraper = ZapScraper(config)
        
        search_params = {
            'city': 'Rio de Janeiro',
            'state': 'RJ',
            'transaction_type': 'venda',
            'page': 2
        }
        
        url = scraper.build_search_url(search_params)
        
        assert 'pagina=2' in url or 'page=2' in url
    
    @patch('src.scrapers.zap_scraper.ZapScraper.make_request')
    def test_get_total_pages_success(self, mock_request):
        """Test getting total pages successfully."""
        config = DevelopmentConfig()
        scraper = ZapScraper(config)
        
        # Mock HTML response with pagination
        mock_html = """
        <html>
            <body>
                <div class="pagination">
                    <a href="?page=1">1</a>
                    <a href="?page=2">2</a>
                    <a href="?page=3">3</a>
                    <span>4</span>
                    <a href="?page=5">5</a>
                </div>
            </body>
        </html>
        """
        
        mock_response = Mock()
        mock_response.text = mock_html
        mock_request.return_value = mock_response
        
        search_params = {'city': 'Rio de Janeiro', 'state': 'RJ'}
        pages = scraper.get_total_pages(search_params)
        
        assert pages == 5
    
    @patch('src.scrapers.zap_scraper.ZapScraper.make_request')
    def test_get_total_pages_no_pagination(self, mock_request):
        """Test getting total pages when no pagination exists."""
        config = DevelopmentConfig()
        scraper = ZapScraper(config)
        
        # Mock HTML response without pagination
        mock_html = """
        <html>
            <body>
                <div class="results">
                    <div class="property">Property 1</div>
                    <div class="property">Property 2</div>
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
        scraper = ZapScraper(config)
        
        # Mock property HTML
        property_html = """
        <div class="property-card">
            <h2 class="property-title">Apartamento de 3 quartos em Copacabana</h2>
            <div class="property-price">R$ 750.000</div>
            <div class="property-address">Rua Barata Ribeiro, 123 - Copacabana</div>
            <div class="property-details">
                <span class="bedrooms">3 quartos</span>
                <span class="bathrooms">2 banheiros</span>
                <span class="area">120 m²</span>
            </div>
            <a href="/imovel/123456" class="property-link">Ver detalhes</a>
        </div>
        """
        
        soup = BeautifulSoup(property_html, 'html.parser')
        property_data = scraper.extract_property_data(soup)
        
        assert property_data['title'] == "Apartamento de 3 quartos em Copacabana"
        assert property_data['price'] == 750000
        assert 'Copacabana' in property_data['address']
        assert property_data['bedrooms'] == 3
        assert property_data['bathrooms'] == 2
        assert property_data['size'] == 120
        assert property_data['source'] == 'ZAP'
    
    def test_extract_property_data_missing_elements(self):
        """Test extracting property data with missing elements."""
        config = DevelopmentConfig()
        scraper = ZapScraper(config)
        
        # Mock incomplete property HTML
        property_html = """
        <div class="property-card">
            <h2 class="property-title">Casa sem preço</h2>
            <div class="property-address">Endereço qualquer</div>
        </div>
        """
        
        soup = BeautifulSoup(property_html, 'html.parser')
        
        with pytest.raises(ScraperParsingError):
            scraper.extract_property_data(soup)
    
    @patch('src.scrapers.zap_scraper.ZapScraper.make_request')
    def test_scrape_properties_success(self, mock_request):
        """Test scraping properties successfully."""
        config = DevelopmentConfig()
        scraper = ZapScraper(config)
        
        # Mock search results HTML
        mock_html = """
        <html>
            <body>
                <div class="results">
                    <div class="property-card">
                        <h2 class="property-title">Apartamento 1</h2>
                        <div class="property-price">R$ 500.000</div>
                        <div class="property-address">Endereço 1 - Bairro 1</div>
                        <div class="property-details">
                            <span class="bedrooms">2 quartos</span>
                            <span class="bathrooms">1 banheiro</span>
                            <span class="area">80 m²</span>
                        </div>
                        <a href="/imovel/111" class="property-link">Ver detalhes</a>
                    </div>
                    <div class="property-card">
                        <h2 class="property-title">Apartamento 2</h2>
                        <div class="property-price">R$ 750.000</div>
                        <div class="property-address">Endereço 2 - Bairro 2</div>
                        <div class="property-details">
                            <span class="bedrooms">3 quartos</span>
                            <span class="bathrooms">2 banheiros</span>
                            <span class="area">120 m²</span>
                        </div>
                        <a href="/imovel/222" class="property-link">Ver detalhes</a>
                    </div>
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
        assert properties[0]['price'] == 500000
        assert properties[1]['title'] == "Apartamento 2"
        assert properties[1]['price'] == 750000
    
    @patch('src.scrapers.zap_scraper.ZapScraper.get_total_pages')
    @patch('src.scrapers.zap_scraper.ZapScraper.make_request')
    def test_scrape_properties_with_pagination(self, mock_request, mock_get_total_pages):
        """Test scraping properties with pagination."""
        config = DevelopmentConfig()
        scraper = ZapScraper(config)
        
        # Mock total pages
        mock_get_total_pages.return_value = 5
        
        # Mock different responses for different pages
        def mock_request_side_effect(url, **kwargs):
            mock_response = Mock()
            if 'pagina=2' in url or 'page=2' in url:
                mock_response.text = """
                <div class="results">
                    <div class="property-card">
                        <h2 class="property-title">Propriedade Página 2</h2>
                        <div class="property-price">R$ 400.000</div>
                        <div class="property-address">Endereço Página 2</div>
                        <div class="property-details">
                            <span class="bedrooms">3 quartos</span>
                            <span class="bathrooms">2 banheiros</span>
                            <span class="area">90 m²</span>
                        </div>
                        <a href="/imovel/page2" class="property-link">Ver detalhes</a>
                    </div>
                </div>
                """
            else:
                # Default to page 1 (no pagination parameter in URL)
                mock_response.text = """
                <div class="results">
                    <div class="property-card">
                        <h2 class="property-title">Propriedade Página 1</h2>
                        <div class="property-price">R$ 300.000</div>
                        <div class="property-address">Endereço Página 1</div>
                        <div class="property-details">
                            <span class="bedrooms">2 quartos</span>
                            <span class="bathrooms">1 banheiro</span>
                            <span class="area">70 m²</span>
                        </div>
                        <a href="/imovel/page1" class="property-link">Ver detalhes</a>
                    </div>
                </div>
                """
            return mock_response
        
        mock_request.side_effect = mock_request_side_effect
        
        search_params = {
            'city': 'Rio de Janeiro', 
            'state': 'RJ',
            'max_pages': 2
        }
        properties = scraper.scrape_properties(search_params)
        
        assert len(properties) == 2
        assert properties[0]['title'] == "Propriedade Página 1"
        assert properties[1]['title'] == "Propriedade Página 2"
    
    def test_normalize_city_name(self):
        """Test city name normalization."""
        config = DevelopmentConfig()
        scraper = ZapScraper(config)
        
        # Test various city names
        assert scraper.normalize_city_name("São Paulo") == "sao-paulo"
        assert scraper.normalize_city_name("Rio de Janeiro") == "rio-de-janeiro"
        assert scraper.normalize_city_name("Belo Horizonte") == "belo-horizonte"
        assert scraper.normalize_city_name("Brasília") == "brasilia"
    
    def test_parse_price_variations(self):
        """Test parsing different price formats."""
        config = DevelopmentConfig()
        scraper = ZapScraper(config)
        
        # Test various price formats
        assert scraper.parse_price("R$ 750.000") == 750000
        assert scraper.parse_price("R$ 1.250.000") == 1250000
        assert scraper.parse_price("750.000") == 750000
        assert scraper.parse_price("R$ 750 mil") == 750000
        assert scraper.parse_price("Preço sob consulta") is None
    
    def test_extract_property_id(self):
        """Test extracting property ID from URL."""
        config = DevelopmentConfig()
        scraper = ZapScraper(config)
        
        # Test various URL formats
        assert scraper.extract_property_id("/imovel/123456/") == "zap_123456"
        assert scraper.extract_property_id("/imovel/apartamento-copacabana-789/") == "zap_789"
        assert scraper.extract_property_id("/listing/456789") == "zap_456789"
    
    def test_extract_neighborhood_from_address(self):
        """Test extracting neighborhood from address."""
        config = DevelopmentConfig()
        scraper = ZapScraper(config)
        
        # Test various address formats
        address1 = "Rua das Flores, 123 - Copacabana, Rio de Janeiro"
        assert scraper.extract_neighborhood(address1) == "Copacabana"
        
        address2 = "Avenida Paulista, 1000, Bela Vista, São Paulo"
        assert scraper.extract_neighborhood(address2) == "Bela Vista"
    
    @patch('src.scrapers.zap_scraper.ZapScraper.make_request')
    def test_scrape_properties_error_handling(self, mock_request):
        """Test error handling during scraping."""
        config = DevelopmentConfig()
        scraper = ZapScraper(config)
        
        # Mock request that raises an exception
        mock_request.side_effect = requests.ConnectionError("Connection failed")
        
        search_params = {'city': 'Rio de Janeiro', 'state': 'RJ'}
        
        # Should handle the error gracefully and return empty list
        properties = scraper.scrape_properties(search_params)
        assert properties == []
    
    def test_validate_search_params(self):
        """Test search parameters validation."""
        config = DevelopmentConfig()
        scraper = ZapScraper(config)
        
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
        scraper = ZapScraper(config)
        
        relative_url = "/imovel/apartamento-copacabana-123456/"
        full_url = scraper.get_property_details_url(relative_url)
        
        assert full_url == "https://www.zapimoveis.com.br/imovel/apartamento-copacabana-123456/"
    
    def test_scraper_stats_tracking(self):
        """Test that scraper tracks statistics correctly."""
        config = DevelopmentConfig()
        scraper = ZapScraper(config)
        
        # Initial stats
        stats = scraper.get_stats()
        assert stats['requests_made'] == 0
        assert stats['properties_found'] == 0
        
        # Update stats manually (would normally happen during scraping)
        scraper.update_stats('requests_made', 5)
        scraper.update_stats('properties_found', 25)
        
        stats = scraper.get_stats()
        assert stats['requests_made'] == 5
        assert stats['properties_found'] == 25