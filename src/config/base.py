"""
Base configuration classes for the Brazil Property API.
"""
import os
from urllib.parse import urlparse
from typing import Optional


class Config:
    """Base configuration class."""
    
    def __init__(self):
        """Initialize configuration with validation."""
        self.validate_required_vars()
        self.validate_urls()
        self.validate_secret_key(self.SECRET_KEY)
    
    # Core Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-secret-key')
    DEBUG = False
    TESTING = False
    ENV = 'production'
    
    # Database settings
    MONGODB_URL = os.environ.get('MONGODB_URL', 'mongodb://localhost:27017/brazil_property_api')
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Cache settings
    CACHE_TTL = int(os.environ.get('CACHE_TTL', 300))  # 5 minutes
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'redis')
    
    # Rate limiting settings
    RATE_LIMIT_PER_MINUTE = int(os.environ.get('RATE_LIMIT_PER_MINUTE', 60))
    RATE_LIMIT_STORAGE = os.environ.get('RATE_LIMIT_STORAGE', 'redis')
    
    # Scraper settings
    SCRAPER_DELAY = float(os.environ.get('SCRAPER_DELAY', 1.0))
    SCRAPER_TIMEOUT = int(os.environ.get('SCRAPER_TIMEOUT', 30))
    SCRAPER_RETRIES = int(os.environ.get('SCRAPER_RETRIES', 3))
    
    def validate_required_vars(self):
        """Validate required environment variables."""
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("SECRET_KEY environment variable is required")
    
    def validate_urls(self):
        """Validate database and cache URLs."""
        if not self.validate_mongodb_url(self.MONGODB_URL):
            raise ValueError("Invalid MONGODB_URL")
        
        if not self.validate_redis_url(self.REDIS_URL):
            raise ValueError("Invalid REDIS_URL")
    
    def validate_mongodb_url(self, url: str) -> bool:
        """Validate MongoDB URL format."""
        if not url:
            return False
        
        try:
            parsed = urlparse(url)
            return (
                parsed.scheme in ['mongodb', 'mongodb+srv'] and
                parsed.hostname is not None and
                (parsed.port is not None or parsed.scheme == 'mongodb+srv')
            )
        except Exception:
            return False
    
    def validate_redis_url(self, url: str) -> bool:
        """Validate Redis URL format."""
        if not url:
            return False
        
        try:
            parsed = urlparse(url)
            return (
                parsed.scheme == 'redis' and
                parsed.hostname is not None
            )
        except Exception:
            return False
    
    def validate_secret_key(self, key: Optional[str]) -> bool:
        """Validate secret key strength."""
        if not key:
            return False
        
        if len(key) < 16:
            return False
        
        return True
    
    def get_database_host(self) -> Optional[str]:
        """Extract database host from MongoDB URL."""
        try:
            parsed = urlparse(self.MONGODB_URL)
            return parsed.hostname
        except Exception:
            return None
    
    def get_database_port(self) -> Optional[int]:
        """Extract database port from MongoDB URL."""
        try:
            parsed = urlparse(self.MONGODB_URL)
            return parsed.port or 27017
        except Exception:
            return None
    
    def get_database_name(self) -> Optional[str]:
        """Extract database name from MongoDB URL."""
        try:
            parsed = urlparse(self.MONGODB_URL)
            return parsed.path.lstrip('/') or 'brazil_property_api'
        except Exception:
            return None
    
    def get_redis_host(self) -> Optional[str]:
        """Extract Redis host from Redis URL."""
        try:
            parsed = urlparse(self.REDIS_URL)
            return parsed.hostname
        except Exception:
            return None
    
    def get_redis_port(self) -> Optional[int]:
        """Extract Redis port from Redis URL."""
        try:
            parsed = urlparse(self.REDIS_URL)
            return parsed.port or 6379
        except Exception:
            return None
    
    def get_redis_db(self) -> Optional[int]:
        """Extract Redis database from Redis URL."""
        try:
            parsed = urlparse(self.REDIS_URL)
            return int(parsed.path.lstrip('/')) if parsed.path else 0
        except Exception:
            return None


class DevelopmentConfig(Config):
    """Development configuration."""
    
    DEBUG = True
    TESTING = False
    ENV = 'development'
    
    # Override with development-specific settings
    MONGODB_URL = os.environ.get('MONGODB_URL', 'mongodb://localhost:27017/brazil_property_api_dev')
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/1')
    
    def validate_required_vars(self):
        """Development config is more lenient with required vars."""
        # Allow default secret key in development, but still validate URLs
        if os.environ.get('MONGODB_URL') and not self.validate_mongodb_url(os.environ.get('MONGODB_URL')):
            raise ValueError("Invalid MONGODB_URL")


class ProductionConfig(Config):
    """Production configuration."""
    
    DEBUG = False
    TESTING = False
    ENV = 'production'
    
    def __init__(self):
        """Initialize production configuration."""
        # Set SECRET_KEY from environment first
        self.SECRET_KEY = os.environ.get('SECRET_KEY')
        super().__init__()
    
    def validate_required_vars(self):
        """Production config requires all environment variables."""
        # For production, SECRET_KEY must be provided via environment
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("SECRET_KEY environment variable is required")
        
        # Additional production validations
        if os.environ.get('SECRET_KEY') == 'default-secret-key':
            raise ValueError("Production requires a custom SECRET_KEY")


class TestingConfig(Config):
    """Testing configuration."""
    
    DEBUG = False
    TESTING = True
    ENV = 'testing'
    
    # Override with testing-specific settings
    MONGODB_URL = os.environ.get('MONGODB_URL', 'mongodb://localhost:27017/brazil_property_api_test')
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/2')
    
    def validate_required_vars(self):
        """Testing config is lenient with required vars."""
        # Allow default secret key in testing
        pass