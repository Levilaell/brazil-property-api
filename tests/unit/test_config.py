"""
Tests for configuration management.
Following TDD approach - write tests first, then implement.
"""
import pytest
import os
from unittest.mock import patch
from src.config import Config, DevelopmentConfig, ProductionConfig, TestingConfig, create_config


@pytest.mark.unit
class TestConfig:
    """Test base configuration class."""
    
    def test_development_config_loads(self):
        """Test that development config loads with correct settings."""
        config = DevelopmentConfig()
        assert config.DEBUG is True
        assert config.TESTING is False
        assert config.ENV == 'development'
        assert config.SECRET_KEY is not None
        assert config.MONGODB_URL is not None
        assert config.REDIS_URL is not None
    
    def test_production_config_loads(self):
        """Test that production config loads with correct settings."""
        with patch.dict(os.environ, {'SECRET_KEY': 'production-secret-key'}):
            config = ProductionConfig()
            assert config.DEBUG is False
            assert config.TESTING is False
            assert config.ENV == 'production'
            assert config.SECRET_KEY is not None
            assert config.MONGODB_URL is not None
            assert config.REDIS_URL is not None
    
    def test_testing_config_loads(self):
        """Test that testing config loads with correct settings."""
        config = TestingConfig()
        assert config.DEBUG is False
        assert config.TESTING is True
        assert config.ENV == 'testing'
        assert config.SECRET_KEY is not None
        assert config.MONGODB_URL is not None
        assert config.REDIS_URL is not None
    
    def test_required_environment_variables(self):
        """Test that required environment variables are validated."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="SECRET_KEY environment variable is required"):
                Config()
    
    def test_database_url_parsing(self):
        """Test that database URLs are parsed correctly."""
        config = DevelopmentConfig()
        
        # Test valid MongoDB URL
        assert config.MONGODB_URL.startswith('mongodb://')
        assert config.get_database_host() is not None
        assert config.get_database_port() is not None
        assert config.get_database_name() is not None
    
    def test_redis_url_parsing(self):
        """Test that Redis URLs are parsed correctly."""
        config = DevelopmentConfig()
        
        # Test valid Redis URL
        assert config.REDIS_URL.startswith('redis://')
        assert config.get_redis_host() is not None
        assert config.get_redis_port() is not None
        assert config.get_redis_db() is not None
    
    def test_invalid_config_raises_error(self):
        """Test that invalid configuration raises appropriate errors."""
        with patch.dict(os.environ, {'SECRET_KEY': 'test-secret-key', 'MONGODB_URL': 'invalid-url'}):
            with pytest.raises(ValueError, match="Invalid MONGODB_URL"):
                DevelopmentConfig()
    
    def test_config_inheritance(self):
        """Test that config classes inherit from base Config properly."""
        dev_config = DevelopmentConfig()
        with patch.dict(os.environ, {'SECRET_KEY': 'production-secret-key'}):
            prod_config = ProductionConfig()
        test_config = TestingConfig()
        
        assert isinstance(dev_config, Config)
        assert isinstance(prod_config, Config)
        assert isinstance(test_config, Config)
    
    def test_secret_key_not_default_in_prod(self):
        """Test that production config doesn't use default secret key."""
        with patch.dict(os.environ, {'SECRET_KEY': 'production-secret-key'}):
            config = ProductionConfig()
            assert config.SECRET_KEY != 'default-secret-key'
            assert config.SECRET_KEY == 'production-secret-key'
    
    def test_debug_disabled_in_production(self):
        """Test that debug is disabled in production."""
        with patch.dict(os.environ, {'SECRET_KEY': 'production-secret-key'}):
            config = ProductionConfig()
            assert config.DEBUG is False
            
            # Also test that sensitive info is not exposed
            assert not hasattr(config, 'expose_config')
    
    def test_cache_configuration(self):
        """Test cache-related configuration."""
        config = DevelopmentConfig()
        
        assert hasattr(config, 'CACHE_TTL')
        assert isinstance(config.CACHE_TTL, int)
        assert config.CACHE_TTL > 0
        
        assert hasattr(config, 'CACHE_TYPE')
        assert config.CACHE_TYPE in ['redis', 'memory']
    
    def test_rate_limit_configuration(self):
        """Test rate limiting configuration."""
        config = DevelopmentConfig()
        
        assert hasattr(config, 'RATE_LIMIT_PER_MINUTE')
        assert isinstance(config.RATE_LIMIT_PER_MINUTE, int)
        assert config.RATE_LIMIT_PER_MINUTE > 0
        
        assert hasattr(config, 'RATE_LIMIT_STORAGE')
        assert config.RATE_LIMIT_STORAGE in ['redis', 'memory']
    
    def test_scraper_configuration(self):
        """Test scraper-related configuration."""
        config = DevelopmentConfig()
        
        assert hasattr(config, 'SCRAPER_DELAY')
        assert isinstance(config.SCRAPER_DELAY, (int, float))
        assert config.SCRAPER_DELAY >= 0
        
        assert hasattr(config, 'SCRAPER_TIMEOUT')
        assert isinstance(config.SCRAPER_TIMEOUT, int)
        assert config.SCRAPER_TIMEOUT > 0
        
        assert hasattr(config, 'SCRAPER_RETRIES')
        assert isinstance(config.SCRAPER_RETRIES, int)
        assert config.SCRAPER_RETRIES >= 0


@pytest.mark.unit
class TestConfigFactory:
    """Test configuration factory function."""
    
    def test_create_config_development(self):
        """Test creating development config."""
        config = create_config('development')
        assert isinstance(config, DevelopmentConfig)
        assert config.DEBUG is True
    
    def test_create_config_production(self):
        """Test creating production config."""
        with patch.dict(os.environ, {'SECRET_KEY': 'production-secret-key'}):
            config = create_config('production')
            assert isinstance(config, ProductionConfig)
            assert config.DEBUG is False
    
    def test_create_config_testing(self):
        """Test creating testing config."""
        config = create_config('testing')
        assert isinstance(config, TestingConfig)
        assert config.TESTING is True
    
    def test_create_config_invalid_env(self):
        """Test creating config with invalid environment."""
        with pytest.raises(ValueError, match="Unknown environment"):
            create_config('invalid')
    
    def test_create_config_from_env_var(self):
        """Test creating config from environment variable."""
        with patch.dict(os.environ, {'FLASK_ENV': 'development'}):
            config = create_config()
            assert isinstance(config, DevelopmentConfig)
    
    def test_create_config_default_env(self):
        """Test creating config with default environment."""
        with patch.dict(os.environ, {}, clear=True):
            # Should default to development
            config = create_config()
            assert isinstance(config, DevelopmentConfig)


@pytest.mark.unit
class TestConfigValidation:
    """Test configuration validation."""
    
    def test_validate_mongodb_url_valid(self):
        """Test validation of valid MongoDB URLs."""
        valid_urls = [
            'mongodb://localhost:27017/testdb',
            'mongodb://user:pass@localhost:27017/testdb',
            'mongodb+srv://user:pass@cluster.mongodb.net/testdb'
        ]
        
        with patch.dict(os.environ, {'SECRET_KEY': 'test-secret-key'}):
            config = DevelopmentConfig()
            for url in valid_urls:
                assert config.validate_mongodb_url(url) is True
    
    def test_validate_mongodb_url_invalid(self):
        """Test validation of invalid MongoDB URLs."""
        invalid_urls = [
            'invalid-url',
            'http://localhost:27017/testdb',
            'mongodb://localhost/testdb',  # Missing port
            ''
        ]
        
        with patch.dict(os.environ, {'SECRET_KEY': 'test-secret-key'}):
            config = DevelopmentConfig()
            for url in invalid_urls:
                assert config.validate_mongodb_url(url) is False
    
    def test_validate_redis_url_valid(self):
        """Test validation of valid Redis URLs."""
        valid_urls = [
            'redis://localhost:6379/0',
            'redis://user:pass@localhost:6379/0',
            'redis://localhost:6379'
        ]
        
        with patch.dict(os.environ, {'SECRET_KEY': 'test-secret-key'}):
            config = DevelopmentConfig()
            for url in valid_urls:
                assert config.validate_redis_url(url) is True
    
    def test_validate_redis_url_invalid(self):
        """Test validation of invalid Redis URLs."""
        invalid_urls = [
            'invalid-url',
            'http://localhost:6379/0',
            ''
        ]
        
        with patch.dict(os.environ, {'SECRET_KEY': 'test-secret-key'}):
            config = DevelopmentConfig()
            for url in invalid_urls:
                assert config.validate_redis_url(url) is False
    
    def test_validate_secret_key(self):
        """Test secret key validation."""
        with patch.dict(os.environ, {'SECRET_KEY': 'test-secret-key'}):
            config = DevelopmentConfig()
            
            # Valid secret keys
            assert config.validate_secret_key('long-enough-secret-key') is True
            assert config.validate_secret_key('a' * 32) is True
            
            # Invalid secret keys
            assert config.validate_secret_key('short') is False
            assert config.validate_secret_key('') is False
            assert config.validate_secret_key(None) is False