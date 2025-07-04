"""
Input validation and security checks for the Brazil Property API.
"""
import re
import logging
from typing import Dict, Any, Optional
import html
import urllib.parse

from src.security.exceptions import SecurityViolation, InvalidInput


logger = logging.getLogger(__name__)


class InputValidator:
    """Input validation and sanitization."""
    
    def __init__(self):
        # SQL injection patterns (simplified to avoid regex issues)
        self.sql_patterns = [
            r"'.*--",          # SQL comment after quote
            r"'.*OR.*'.*'",    # OR with quotes
            r"admin'--",       # admin with comment
            r"\bUNION\b.*\bSELECT\b",
            r"\bDROP\s+TABLE\b",
            r"\bDELETE\s+FROM\b",
            r"\bINSERT\s+INTO\b", 
            r"\bUPDATE\s+\w+\s+SET\b",
            r";\s*DROP\b",
            r";\s*DELETE\b",
            r"1\s*=\s*1",
            r"OR\s+1\s*=\s*1",
            r"'1'='1",         # Common injection pattern
            r";\s*\w+.*--"     # Semicolon with command and comment
        ]
        
        # XSS patterns
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"vbscript:",
            r"onload\s*=",
            r"onerror\s*=",
            r"onclick\s*=",
            r"onmouseover\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
            r"<link[^>]*>",
            r"<meta[^>]*>"
        ]
        
        # Allowed file extensions
        self.allowed_extensions = {'csv', 'json', 'xlsx', 'txt'}
        
        # Maximum sizes
        self.max_string_length = 1000
        self.max_array_length = 100
        
        logger.info("InputValidator initialized")
    
    def validate_search_query(self, query: str) -> str:
        """Validate and sanitize search query."""
        if not query or not isinstance(query, str):
            raise InvalidInput("Search query must be a non-empty string")
        
        # Check for SQL injection
        self._check_sql_injection(query)
        
        # Check for XSS
        self._check_xss(query)
        
        # Sanitize the query
        sanitized = self.sanitize_input(query)
        
        return sanitized
    
    def validate_search_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate search parameters."""
        validated = {}
        
        # Required fields
        if 'city' not in params or not params['city']:
            raise InvalidInput("City is required")
        
        # Validate city
        city = str(params['city']).strip()
        if not city:
            raise InvalidInput("City cannot be empty")
        
        validated['city'] = self.sanitize_input(city)
        
        # Validate optional parameters
        if 'min_price' in params:
            try:
                min_price = int(params['min_price'])
                if min_price < 0:
                    raise InvalidInput("Minimum price cannot be negative")
                validated['min_price'] = min_price
            except (ValueError, TypeError):
                raise InvalidInput("Minimum price must be a valid number")
        
        if 'max_price' in params:
            try:
                max_price = int(params['max_price'])
                if max_price < 0:
                    raise InvalidInput("Maximum price cannot be negative")
                validated['max_price'] = max_price
            except (ValueError, TypeError):
                raise InvalidInput("Maximum price must be a valid number")
        
        # Check price range logic
        if 'min_price' in validated and 'max_price' in validated:
            if validated['min_price'] > validated['max_price']:
                raise InvalidInput("Minimum price cannot be greater than maximum price")
        
        # Validate bedrooms
        if 'bedrooms' in params:
            try:
                bedrooms = int(params['bedrooms'])
                if bedrooms < 0 or bedrooms > 20:  # Reasonable limits
                    raise InvalidInput("Bedrooms must be between 0 and 20")
                validated['bedrooms'] = bedrooms
            except (ValueError, TypeError):
                raise InvalidInput("Bedrooms must be a valid number")
        
        # Validate property type
        if 'property_type' in params:
            property_type = str(params['property_type']).strip().lower()
            allowed_types = ['apartment', 'house', 'commercial', 'land', 'any']
            if property_type not in allowed_types:
                raise InvalidInput(f"Property type must be one of: {', '.join(allowed_types)}")
            validated['property_type'] = property_type
        
        return validated
    
    def validate_json_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate JSON payload."""
        if not isinstance(data, dict):
            raise InvalidInput("Payload must be a JSON object")
        
        # Check for required fields based on context
        if 'city' in data:
            if not data['city'] or not isinstance(data['city'], str):
                raise InvalidInput("City must be a non-empty string")
        
        # Recursively sanitize all string values
        return self._sanitize_dict(data)
    
    def sanitize_input(self, input_str: str) -> str:
        """Sanitize input string."""
        if not isinstance(input_str, str):
            return str(input_str)
        
        # Remove dangerous protocols
        sanitized = input_str
        dangerous_protocols = ['javascript:', 'data:', 'vbscript:']
        for protocol in dangerous_protocols:
            sanitized = sanitized.replace(protocol, '')
        
        # HTML escape
        sanitized = html.escape(sanitized)
        
        # URL decode (to catch encoded attacks)
        sanitized = urllib.parse.unquote(sanitized)
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Limit length
        if len(sanitized) > self.max_string_length:
            sanitized = sanitized[:self.max_string_length]
        
        return sanitized.strip()
    
    def is_allowed_file_extension(self, filename: str) -> bool:
        """Check if file extension is allowed."""
        if not filename or '.' not in filename:
            return False
        
        extension = filename.rsplit('.', 1)[1].lower()
        return extension in self.allowed_extensions
    
    def _check_sql_injection(self, input_str: str):
        """Check for SQL injection patterns."""
        input_lower = input_str.lower()
        
        for pattern in self.sql_patterns:
            if re.search(pattern, input_lower, re.IGNORECASE):
                logger.warning(f"SQL injection attempt detected: {input_str[:100]}")
                raise SecurityViolation("Potential SQL injection detected")
    
    def _check_xss(self, input_str: str):
        """Check for XSS patterns."""
        input_lower = input_str.lower()
        
        for pattern in self.xss_patterns:
            if re.search(pattern, input_lower, re.IGNORECASE):
                logger.warning(f"XSS attempt detected: {input_str[:100]}")
                raise SecurityViolation("Potential XSS attack detected")
    
    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary values."""
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = self.sanitize_input(value)
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = self._sanitize_list(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_list(self, data: list) -> list:
        """Recursively sanitize list values."""
        if len(data) > self.max_array_length:
            raise InvalidInput(f"Array too large (max {self.max_array_length} items)")
        
        sanitized = []
        
        for item in data:
            if isinstance(item, str):
                sanitized.append(self.sanitize_input(item))
            elif isinstance(item, dict):
                sanitized.append(self._sanitize_dict(item))
            elif isinstance(item, list):
                sanitized.append(self._sanitize_list(item))
            else:
                sanitized.append(item)
        
        return sanitized


class SecurityValidator:
    """Additional security validation and checks."""
    
    def __init__(self):
        # Suspicious user agents
        self.suspicious_agents = [
            'sqlmap', 'nikto', 'nmap', 'dirb', 'zmeu', 'masscan',
            'nessus', 'openvas', 'acunetix', 'netsparker', 'burpsuite'
        ]
        
        # Blocked IPs (could be loaded from database)
        self.blocked_ips = set()
        
        logger.info("SecurityValidator initialized")
    
    def is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is suspicious."""
        if not user_agent:
            return True  # Empty user agent is suspicious
        
        user_agent_lower = user_agent.lower()
        
        for suspicious in self.suspicious_agents:
            if suspicious in user_agent_lower:
                return True
        
        return False
    
    def is_blocked_ip(self, ip_address: str) -> bool:
        """Check if IP address is blocked."""
        return ip_address in self.blocked_ips
    
    def add_blocked_ip(self, ip_address: str):
        """Add IP address to blocked list."""
        self.blocked_ips.add(ip_address)
        logger.warning(f"IP {ip_address} has been blocked")
    
    def remove_blocked_ip(self, ip_address: str):
        """Remove IP address from blocked list."""
        self.blocked_ips.discard(ip_address)
        logger.info(f"IP {ip_address} has been unblocked")
    
    def validate_request_size(self, content_length: int, max_size: int = 10 * 1024 * 1024) -> bool:
        """Validate request content length."""
        return content_length <= max_size
    
    def detect_suspicious_pattern(self, ip_address: str, requests_per_minute: int = 60) -> bool:
        """Detect suspicious request patterns."""
        # This is a simplified implementation
        # In practice, you'd track request patterns over time
        return requests_per_minute > 60