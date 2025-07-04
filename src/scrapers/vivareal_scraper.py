"""
VivaReal Scraper implementation for scraping property data from VivaReal.
"""
import re
import logging
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, quote
import unicodedata

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from .exceptions import ScraperParsingError, ScraperDataError


logger = logging.getLogger(__name__)


class VivaRealScraper(BaseScraper):
    """
    VivaReal Scraper for extracting property data from VivaReal website.
    """
    
    def __init__(self, config):
        """Initialize VivaReal scraper."""
        super().__init__(config)
        self.name = "VivaRealScraper"
        self.base_url = "https://www.vivareal.com.br"
        
        # VivaReal-specific configuration
        self.delay_range = (1.5, 3.5)  # Moderate delays for VivaReal
        self.max_retries = 3
        
        logger.info("Initialized VivaReal scraper")
    
    def build_search_url(self, search_params: Dict[str, Any]) -> str:
        """
        Build VivaReal search URL from parameters.
        
        Args:
            search_params: Search parameters dictionary
            
        Returns:
            Complete VivaReal search URL
        """
        try:
            # Required parameters
            city = search_params.get('city', '').strip()
            state = search_params.get('state', '').strip()
            transaction_type = search_params.get('transaction_type', 'venda').lower()
            
            if not city or not state:
                raise ScraperDataError("City and state are required for VivaReal search")
            
            # Normalize city name for URL
            normalized_city = self.normalize_city_name(city)
            normalized_state = state.lower()
            
            # Build base URL path - VivaReal uses different structure
            url_path = f"/{transaction_type}/{normalized_state}/{normalized_city}/"
            
            # Add property type if specified
            property_type = search_params.get('property_type', '').lower()
            if property_type:
                if property_type in ['apartamento', 'casa', 'cobertura', 'loft', 'studio']:
                    url_path += f"{property_type}/"
            
            # Build full URL
            url = urljoin(self.base_url, url_path)
            
            # Add query parameters
            params = []
            
            # Price filters
            if search_params.get('price_min'):
                params.append(f"preco-minimo={search_params['price_min']}")
            if search_params.get('price_max'):
                params.append(f"preco-maximo={search_params['price_max']}")
            
            # Bedrooms filter
            if search_params.get('bedrooms'):
                params.append(f"quartos={search_params['bedrooms']}")
            
            # Bathrooms filter
            if search_params.get('bathrooms'):
                params.append(f"banheiros={search_params['bathrooms']}")
            
            # Area filters
            if search_params.get('area_min'):
                params.append(f"area-util-minima={search_params['area_min']}")
            if search_params.get('area_max'):
                params.append(f"area-util-maxima={search_params['area_max']}")
            
            # Parking spaces
            if search_params.get('parking_spaces'):
                params.append(f"vagas={search_params['parking_spaces']}")
            
            # Add parameters to URL
            if params:
                url += "?" + "&".join(params)
            
            # Add pagination as hash fragment (VivaReal uses SPA)
            page = search_params.get('page', 1)
            if page > 1:
                url += f"#pagina={page}"
            
            logger.debug(f"Built VivaReal search URL: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Error building VivaReal search URL: {e}")
            raise ScraperDataError(f"Failed to build search URL: {e}")
    
    def normalize_city_name(self, city: str) -> str:
        """
        Normalize city name for URL usage.
        
        Args:
            city: City name
            
        Returns:
            Normalized city name
        """
        if not city:
            return ""
        
        # Remove accents
        normalized = unicodedata.normalize('NFD', city)
        normalized = ''.join(char for char in normalized if unicodedata.category(char) != 'Mn')
        
        # Convert to lowercase and replace spaces with hyphens
        normalized = normalized.lower().replace(' ', '-')
        
        # Remove special characters except hyphens
        normalized = re.sub(r'[^a-z0-9\-]', '', normalized)
        
        return normalized
    
    def get_total_pages(self, search_params: Dict[str, Any]) -> int:
        """
        Get total number of pages for search results.
        
        Args:
            search_params: Search parameters dictionary
            
        Returns:
            Total number of pages
        """
        try:
            # Build URL for first page
            search_url = self.build_search_url(search_params)
            
            # Make request
            response = self.make_request(search_url)
            soup = self.parse_html(response.text)
            
            # Look for pagination summary (e.g., "Página 1 de 8 páginas")
            summary = soup.find(['span', 'div'], string=re.compile(r'Página \d+ de \d+ páginas?'))
            if summary:
                match = re.search(r'Página \d+ de (\d+) páginas?', summary.get_text())
                if match:
                    total_pages = int(match.group(1))
                    logger.info(f"Found {total_pages} total pages from summary")
                    return total_pages
            
            # Look for pagination navigation
            pagination = soup.find(['nav', 'div'], class_=['pagination', 'paginator', 'pages-nav'])
            if pagination:
                # Extract page numbers from pagination buttons
                page_buttons = pagination.find_all(['button', 'a'], string=re.compile(r'^\d+$'))
                if page_buttons:
                    page_numbers = []
                    for button in page_buttons:
                        text = button.get_text(strip=True)
                        if text.isdigit():
                            page_numbers.append(int(text))
                    
                    if page_numbers:
                        total_pages = max(page_numbers)
                        logger.info(f"Found {total_pages} total pages from pagination")
                        return total_pages
            
            # Look for results count to estimate pages
            results_count = soup.find(['span', 'div'], string=re.compile(r'\d+\s*resultados?'))
            if results_count:
                match = re.search(r'(\d+)\s*resultados?', results_count.get_text())
                if match:
                    total_results = int(match.group(1))
                    # Assume ~20 results per page
                    estimated_pages = max(1, (total_results + 19) // 20)
                    logger.info(f"Estimated {estimated_pages} pages from {total_results} results")
                    return estimated_pages
            
            # If no pagination found, assume single page
            logger.info("No pagination found, assuming single page")
            return 1
            
        except Exception as e:
            logger.error(f"Error getting total pages: {e}")
            return 1
    
    def extract_property_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract property data from property card HTML.
        
        Args:
            soup: BeautifulSoup object with property card HTML
            
        Returns:
            Dictionary with property data
            
        Raises:
            ScraperParsingError: If required data cannot be extracted
        """
        try:
            property_data = {'source': 'VivaReal'}
            
            # Extract title
            title_elem = soup.find(['h3', 'h2'], class_=['property-card__title', 'listing-title'])
            if not title_elem:
                # Try alternative selectors
                title_elem = soup.find(['h3', 'h2', 'h4'], attrs={'data-cy': 'listing-title'})
                if not title_elem:
                    title_elem = soup.find(['h3', 'h2'], string=re.compile(r'.+'))
            
            if title_elem:
                property_data['title'] = self.clean_text(title_elem.get_text())
            else:
                raise ScraperParsingError("Could not find property title")
            
            # Extract price
            price_elem = soup.find(['div', 'span'], class_=['property-card__price', 'listing-price'])
            if not price_elem:
                # Try alternative selectors
                price_elem = soup.find(['div', 'span'], attrs={'data-cy': 'listing-price'})
                if not price_elem:
                    price_elem = soup.find(['div', 'span'], string=re.compile(r'R\$'))
            
            if price_elem:
                price_text = self.clean_text(price_elem.get_text())
                property_data['price'] = self.parse_price(price_text)
                
                if property_data['price'] is None:
                    raise ScraperParsingError(f"Could not parse price: {price_text}")
            else:
                raise ScraperParsingError("Could not find property price")
            
            # Extract address
            address_elem = soup.find(['span', 'div'], class_=['property-card__address', 'listing-address'])
            if not address_elem:
                address_elem = soup.find(['span', 'div'], attrs={'data-cy': 'listing-address'})
            
            if address_elem:
                address_text = self.clean_text(address_elem.get_text())
                property_data['address'] = address_text
                property_data['neighborhood'] = self.extract_neighborhood(address_text)
                
                # Extract city from address if possible
                if 'Rio de Janeiro' in address_text:
                    property_data['city'] = 'Rio de Janeiro'
                elif 'São Paulo' in address_text:
                    property_data['city'] = 'São Paulo'
                else:
                    property_data['city'] = 'Unknown'
            else:
                property_data['address'] = ""
                property_data['neighborhood'] = ""
                property_data['city'] = 'Unknown'
            
            # Extract property features (VivaReal specific structure)
            features = self.extract_property_features(soup)
            property_data.update(features)
            
            # Extract property URL/ID
            link_elem = soup.find('a', class_=['property-card__link', 'listing-link'])
            if not link_elem:
                link_elem = soup.find('a', href=True)
            
            if link_elem:
                property_url = link_elem.get('href', '')
                property_data['url'] = self.get_property_details_url(property_url)
                property_data['id'] = self.extract_property_id(property_url)
            else:
                # Generate a temporary ID if no link found
                property_data['id'] = f"vivareal_{hash(property_data.get('title', '') + str(property_data.get('price', 0)))}"
                property_data['url'] = ""
            
            # Set default values for missing fields
            property_data.setdefault('bedrooms', 0)
            property_data.setdefault('bathrooms', 0)
            property_data.setdefault('size', 0)
            property_data.setdefault('parking_spaces', 0)
            property_data.setdefault('amenities', [])
            property_data.setdefault('neighborhood', "")
            
            # Add scraping metadata
            property_data['scraped_at'] = self.get_stats()['current_time']
            
            logger.debug(f"Extracted property data: {property_data['id']}")
            return property_data
            
        except Exception as e:
            logger.error(f"Error extracting property data: {e}")
            raise ScraperParsingError(f"Failed to extract property data: {e}")
    
    def extract_property_features(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract property features from VivaReal specific structure.
        
        Args:
            soup: BeautifulSoup object with property HTML
            
        Returns:
            Dictionary with extracted features
        """
        features = {
            'bedrooms': 0,
            'bathrooms': 0,
            'size': 0,
            'parking_spaces': 0,
            'amenities': []
        }
        
        try:
            # Find details container
            details_container = soup.find(['ul', 'div'], class_=['property-card__details', 'listing-details'])
            if not details_container:
                return features
            
            # Find all detail items
            detail_items = details_container.find_all(['li', 'span'], class_=re.compile(r'property-card__detail|listing-detail'))
            
            for item in detail_items:
                text = self.clean_text(item.get_text()).lower()
                
                # Extract bedrooms
                if 'quarto' in text:
                    bedrooms_match = re.search(r'(\d+)', text)
                    if bedrooms_match:
                        features['bedrooms'] = int(bedrooms_match.group(1))
                
                # Extract bathrooms
                elif 'banheiro' in text:
                    bathrooms_match = re.search(r'(\d+)', text)
                    if bathrooms_match:
                        features['bathrooms'] = int(bathrooms_match.group(1))
                
                # Extract area
                elif 'm²' in text or 'm2' in text:
                    area_match = re.search(r'(\d+)', text)
                    if area_match:
                        features['size'] = int(area_match.group(1))
                
                # Extract parking spaces
                elif 'vaga' in text:
                    parking_match = re.search(r'(\d+)', text)
                    if parking_match:
                        features['parking_spaces'] = int(parking_match.group(1))
                
                # Extract amenities (general features)
                elif any(amenity in text for amenity in ['piscina', 'academia', 'churrasqueira', 'playground', 'salão', 'quadra']):
                    amenity_text = self.clean_text(item.get_text())
                    if amenity_text not in features['amenities']:
                        features['amenities'].append(amenity_text)
            
        except Exception as e:
            logger.debug(f"Error extracting features: {e}")
        
        return features
    
    def parse_price(self, price_text: str) -> Optional[int]:
        """
        Parse price from text string.
        
        Args:
            price_text: Text containing price
            
        Returns:
            Price as integer or None if not found
        """
        if not price_text:
            return None
        
        # Check for "consulte" or similar
        if any(phrase in price_text.lower() for phrase in ['consulte', 'negociar', 'valor']):
            return None
        
        # Remove currency symbols and clean text
        cleaned = re.sub(r'[R$\s]', '', price_text)
        
        # Handle "mil" suffix
        if 'mil' in price_text.lower():
            number_match = re.search(r'(\d+(?:\.\d+)?)', cleaned)
            if number_match:
                number = float(number_match.group(1).replace('.', ''))
                return int(number * 1000)
        
        # Handle regular numbers with dots as thousands separators
        number_match = re.search(r'(\d+(?:\.\d+)*)', cleaned)
        if number_match:
            number_str = number_match.group(1)
            # Remove dots (thousands separators) and convert to int
            number = int(number_str.replace('.', ''))
            return number
        
        return None
    
    def extract_property_id(self, url: str) -> str:
        """
        Extract property ID from URL.
        
        Args:
            url: Property URL
            
        Returns:
            Property ID with VivaReal prefix
        """
        if not url:
            return f"vivareal_{hash(url)}"
        
        # Try to extract numeric ID from URL
        id_match = re.search(r'/imovel/[^/]*?(\d+)', url)
        if id_match:
            return f"vivareal_{id_match.group(1)}"
        
        # Try to extract from property path
        property_match = re.search(r'/property/(\d+)', url)
        if property_match:
            return f"vivareal_{property_match.group(1)}"
        
        # Extract last part of URL as ID
        path_parts = url.strip('/').split('/')
        if path_parts:
            last_part = path_parts[-1]
            # Try to extract numbers from last part
            numbers = re.findall(r'\d+', last_part)
            if numbers:
                return f"vivareal_{numbers[-1]}"
        
        # Fallback to hash of URL
        return f"vivareal_{hash(url)}"
    
    def extract_neighborhood(self, address: str) -> str:
        """
        Extract neighborhood from address string.
        
        Args:
            address: Full address string
            
        Returns:
            Neighborhood name
        """
        if not address:
            return ""
        
        # Common patterns for neighborhood extraction
        patterns = [
            r'-\s*([^,\d]+)\s*,',  # " - Neighborhood, City"
            r',\s*([^,\d]+)\s*,',  # ", Neighborhood, City"
            r'-\s*([^-,\d]+)\s*-',  # " - Neighborhood - "
            r'-\s*([^-,\d]+)$',    # " - Neighborhood" (end of string)
            r',\s*([^,\d]+)$',     # ", Neighborhood" (end of string)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, address)
            if match:
                neighborhood = self.clean_text(match.group(1))
                # Filter out common non-neighborhood terms and numbers
                if (not any(term in neighborhood.lower() for term in ['são paulo', 'rio de janeiro', 'brasil', 'brazil']) 
                    and not neighborhood.isdigit() 
                    and len(neighborhood) > 2):
                    return neighborhood
        
        # If no pattern matches, return empty string
        return ""
    
    def get_property_details_url(self, relative_url: str) -> str:
        """
        Build full property details URL.
        
        Args:
            relative_url: Relative URL from property link
            
        Returns:
            Full property details URL
        """
        if not relative_url:
            return ""
        
        if relative_url.startswith('http'):
            return relative_url
        
        return urljoin(self.base_url, relative_url)
    
    def validate_search_params(self, search_params: Dict[str, Any]) -> bool:
        """
        Validate search parameters.
        
        Args:
            search_params: Search parameters dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_params = ['city', 'state']
        
        for param in required_params:
            if param not in search_params or not search_params[param].strip():
                logger.warning(f"Missing required search parameter: {param}")
                return False
        
        return True
    
    def scrape_properties(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape properties based on search parameters.
        
        Args:
            search_params: Search parameters dictionary
            
        Returns:
            List of property data dictionaries
        """
        properties = []
        
        try:
            # Validate search parameters
            if not self.validate_search_params(search_params):
                logger.error("Invalid search parameters")
                return properties
            
            # Determine how many pages to scrape
            max_pages = search_params.get('max_pages', 1)
            start_page = search_params.get('page', 1)
            
            if max_pages > 1:
                # Get total pages if scraping multiple pages
                if start_page == 1:
                    total_pages = self.get_total_pages(search_params)
                    pages_to_scrape = min(max_pages, total_pages)
                else:
                    # If starting from a specific page, just scrape the requested number
                    pages_to_scrape = max_pages
            else:
                # Single page
                pages_to_scrape = 1
            
            logger.info(f"Scraping {pages_to_scrape} pages starting from page {start_page}")
            
            # Scrape each page
            for page in range(start_page, start_page + pages_to_scrape):
                try:
                    page_params = search_params.copy()
                    page_params['page'] = page
                    
                    # Build URL for this page
                    search_url = self.build_search_url(page_params)
                    logger.info(f"Scraping page {page}: {search_url}")
                    
                    # Make request
                    response = self.make_request(search_url)
                    soup = self.parse_html(response.text)
                    
                    # Find property cards (VivaReal uses article tags)
                    property_cards = soup.find_all(['article', 'div'], class_=['property-card', 'listing-item'])
                    if not property_cards:
                        # Try alternative selectors
                        property_cards = soup.find_all('article', attrs={'data-cy': 'listing-item'})
                        if not property_cards:
                            property_cards = soup.find_all('div', class_=re.compile(r'result|item|property'))
                    
                    logger.info(f"Found {len(property_cards)} property cards on page {page}")
                    
                    # Extract data from each property card
                    for card in property_cards:
                        try:
                            property_data = self.extract_property_data(card)
                            
                            # Add search context if missing
                            if property_data.get('city') == 'Unknown':
                                property_data['city'] = search_params.get('city', 'Unknown')
                            
                            # Validate property data
                            if self.validate_property_data(property_data):
                                properties.append(property_data)
                                self.update_stats('properties_found')
                            else:
                                logger.warning(f"Invalid property data: {property_data.get('id', 'unknown')}")
                                
                        except ScraperParsingError as e:
                            logger.warning(f"Failed to extract property data: {e}")
                            self.update_stats('errors_count')
                            continue
                    
                    # Add delay between pages
                    if page < start_page + pages_to_scrape - 1:
                        self._apply_rate_limit()
                        
                except Exception as e:
                    logger.error(f"Error scraping page {page}: {e}")
                    self.update_stats('errors_count')
                    continue
            
            logger.info(f"Successfully scraped {len(properties)} properties from VivaReal")
            return properties
            
        except Exception as e:
            logger.error(f"Error during VivaReal scraping: {e}")
            self.update_stats('errors_count')
            return properties