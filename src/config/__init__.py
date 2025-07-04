"""
Configuration module for the Brazil Property API.
"""
import os
from .base import Config, DevelopmentConfig, ProductionConfig, TestingConfig


def create_config(env: str = None) -> Config:
    """
    Create configuration instance based on environment.
    
    Args:
        env: Environment name ('development', 'production', 'testing')
        
    Returns:
        Configuration instance
        
    Raises:
        ValueError: If environment is unknown
    """
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    
    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }
    
    if env not in config_map:
        raise ValueError(f"Unknown environment: {env}")
    
    return config_map[env]()


# Export main classes
__all__ = [
    'Config',
    'DevelopmentConfig', 
    'ProductionConfig',
    'TestingConfig',
    'create_config'
]