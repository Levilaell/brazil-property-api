"""
ZAP Scraper implementation for scraping property data from ZAP Imóveis.
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


class ZapScraper(BaseScraper):
    """
    ZAP Scraper for extracting property data from ZAP Imóveis website.
    """
    
    def __init__(self, config):
        """Initialize ZAP scraper."""
        super().__init__(config)
        self.name = "ZapScraper"
        self.base_url = "https://www.zapimoveis.com.br"
        
        # ZAP-specific configuration
        self.delay_range = (2, 4)  # Longer delays for ZAP
        self.max_retries = 3
        
        logger.info("Initialized ZAP scraper")
    
    def build_search_url(self, search_params: Dict[str, Any]) -> str:
        """
        Build ZAP search URL from parameters.
        
        Args:
            search_params: Search parameters dictionary
            
        Returns:
            Complete ZAP search URL
        """
        try:
            # Required parameters
            city = search_params.get('city', '').strip()
            state = search_params.get('state', '').strip()
            transaction_type = search_params.get('transaction_type', 'venda').lower()
            
            if not city or not state:
                raise ScraperDataError("City and state are required for ZAP search")
            
            # Normalize city name for URL
            normalized_city = self.normalize_city_name(city)
            normalized_state = state.lower()
            
            # Build base URL path
            url_path = f"/{transaction_type}/{normalized_state}+{normalized_city}/"
            
            # Add property type if specified
            property_type = search_params.get('property_type', '').lower()
            if property_type:
                if property_type in ['apartamento', 'casa', 'cobertura', 'loft']:
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
                params.append(f"area-minima={search_params['area_min']}")
            if search_params.get('area_max'):
                params.append(f"area-maxima={search_params['area_max']}")
            
            # Pagination
            page = search_params.get('page', 1)
            if page > 1:
                params.append(f"pagina={page}")
            
            # Add parameters to URL
            if params:
                url += "?" + "&".join(params)
            
            logger.debug(f"Built ZAP search URL: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Error building ZAP search URL: {e}")
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
            
            # Look for pagination elements
            pagination = soup.find('div', class_=['pagination', 'paginator', 'pages'])
            if not pagination:
                # Try alternative selectors
                pagination = soup.find('nav', {'aria-label': 'pagination'})
                if not pagination:
                    pagination = soup.find('ul', class_='pagination')
            
            if pagination:
                # Extract page numbers from pagination links
                page_links = pagination.find_all('a', href=True)
                page_numbers = []
                
                for link in page_links:
                    # Extract page number from href or text
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # Try to extract from href first
                    page_match = re.search(r'pagina=(\d+)', href)
                    if page_match:
                        page_numbers.append(int(page_match.group(1)))
                    # Try to extract from text
                    elif text.isdigit():
                        page_numbers.append(int(text))
                
                # Also check for current page indicator
                current_page = pagination.find('span', class_=['current', 'active'])
                if current_page and current_page.get_text(strip=True).isdigit():
                    page_numbers.append(int(current_page.get_text(strip=True)))
                
                if page_numbers:
                    total_pages = max(page_numbers)
                    logger.info(f"Found {total_pages} total pages for search")
                    return total_pages
            
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
            property_data = {'source': 'ZAP'}
            
            # Extract title
            title_elem = soup.find(['h2', 'h3'], class_=['property-title', 'card-title', 'listing-title'])
            if not title_elem:
                # Try alternative selectors
                title_elem = soup.find(['h2', 'h3', 'h4'], string=re.compile(r'.+'))
            
            if title_elem:
                property_data['title'] = self.clean_text(title_elem.get_text())
            else:
                raise ScraperParsingError("Could not find property title")
            
            # Extract price
            price_elem = soup.find(['div', 'span'], class_=['property-price', 'card-price', 'listing-price'])
            if not price_elem:
                # Try alternative selectors
                price_elem = soup.find(['div', 'span'], string=re.compile(r'R\$'))
            
            if price_elem:
                price_text = self.clean_text(price_elem.get_text())
                property_data['price'] = self.parse_price(price_text)
                
                if property_data['price'] is None:
                    raise ScraperParsingError(f"Could not parse price: {price_text}")
            else:
                raise ScraperParsingError("Could not find property price")
            
            # Extract address
            address_elem = soup.find(['div', 'span'], class_=['property-address', 'card-address', 'listing-address'])
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
                    # Default city - this should ideally come from search params
                    property_data['city'] = 'Unknown'
            else:
                property_data['address'] = ""
                property_data['neighborhood'] = ""
                property_data['city'] = 'Unknown'
            
            # Extract property details
            details_container = soup.find(['div', 'ul'], class_=['property-details', 'card-details', 'listing-details'])
            if details_container:
                # Extract bedrooms
                bedrooms_elem = details_container.find(['span', 'li'], string=re.compile(r'\d+\s*quarto'))
                if bedrooms_elem:
                    bedrooms_match = re.search(r'(\d+)', bedrooms_elem.get_text())
                    if bedrooms_match:
                        property_data['bedrooms'] = int(bedrooms_match.group(1))
                
                # Extract bathrooms
                bathrooms_elem = details_container.find(['span', 'li'], string=re.compile(r'\d+\s*banheiro'))
                if bathrooms_elem:
                    bathrooms_match = re.search(r'(\d+)', bathrooms_elem.get_text())
                    if bathrooms_match:
                        property_data['bathrooms'] = int(bathrooms_match.group(1))
                
                # Extract area
                area_elem = details_container.find(['span', 'li'], string=re.compile(r'\d+\s*m²'))
                if area_elem:
                    area_match = re.search(r'(\d+)', area_elem.get_text())
                    if area_match:
                        property_data['size'] = int(area_match.group(1))
            
            # Extract property URL/ID
            link_elem = soup.find('a', class_=['property-link', 'card-link', 'listing-link'])
            if not link_elem:
                link_elem = soup.find('a', href=True)
            
            if link_elem:
                property_url = link_elem.get('href', '')
                property_data['url'] = self.get_property_details_url(property_url)
                property_data['id'] = self.extract_property_id(property_url)
            else:
                # Generate a temporary ID if no link found
                property_data['id'] = f"zap_{hash(property_data.get('title', '') + str(property_data.get('price', 0)))}"
                property_data['url'] = ""
            
            # Set default values for missing fields
            property_data.setdefault('bedrooms', 0)
            property_data.setdefault('bathrooms', 0)
            property_data.setdefault('size', 0)
            property_data.setdefault('neighborhood', "")
            
            # Add scraping metadata
            property_data['scraped_at'] = self.get_stats()['current_time']
            
            logger.debug(f"Extracted property data: {property_data['id']}")
            return property_data
            
        except Exception as e:
            logger.error(f"Error extracting property data: {e}")
            raise ScraperParsingError(f"Failed to extract property data: {e}")
    
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
        
        # Check for "sob consulta" or similar
        if any(phrase in price_text.lower() for phrase in ['sob consulta', 'consulte', 'negociar']):
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
            Property ID with ZAP prefix
        """
        if not url:
            return f"zap_{hash(url)}"
        
        # Try to extract numeric ID from URL
        id_match = re.search(r'/imovel/[^/]*?(\d+)', url)
        if id_match:
            return f"zap_{id_match.group(1)}"
        
        # Try to extract from listing path
        listing_match = re.search(r'/listing/(\d+)', url)
        if listing_match:
            return f"zap_{listing_match.group(1)}"
        
        # Fallback to hash of URL
        return f"zap_{hash(url)}"
    
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
            r'-\s*([^,]+),',  # " - Neighborhood, City"
            r',\s*([^,\d]+),',  # ", Neighborhood, City" (excluding numbers)
            r'-\s*([^-,\d]+)(?:,|$)',  # " - Neighborhood" (excluding numbers)
            r',\s*([^,\d]+)(?:,|$)',  # ", Neighborhood" (excluding numbers)
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
                    
                    # Find property cards
                    property_cards = soup.find_all(['div', 'article'], class_=['property-card', 'card', 'listing'])
                    if not property_cards:
                        # Try alternative selectors
                        property_cards = soup.find_all('div', attrs={'data-testid': 'property-card'})
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
            
            logger.info(f"Successfully scraped {len(properties)} properties from ZAP")
            return properties
            
        except Exception as e:
            logger.error(f"Error during ZAP scraping: {e}")
            self.update_stats('errors_count')
            return properties