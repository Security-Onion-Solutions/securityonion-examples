# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

"""Configuration settings for the Vidalia application"""
import os
import logging
from dotenv import load_dotenv
from src.services.so_api import SecurityOnionAPI

class Config:
    """Application configuration"""
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance
    # Flask configuration values
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    DEBUG = True
    TESTING = True
    
    # Logging configuration
    LOG_LEVEL = logging.DEBUG
    PROPAGATE_EXCEPTIONS = True
    
    # Security Onion API configuration
    SO_API_URL = os.getenv('SO_API_URL', 'http://SOMANAGER:443')
    SO_CLIENT_ID = os.getenv('SO_CLIENT_ID')
    SO_CLIENT_SECRET = os.getenv('SO_CLIENT_SECRET')

    def __init__(self):
        if not self._initialized:
            # Load environment variables from specified .env file or use .env.test for testing
            env_file = os.getenv('ENV_FILE', '.env.test' if os.getenv('FLASK_ENV') == 'testing' else '.env')
            load_dotenv(env_file)
            
            # Flask configuration
            self.SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
            self.DEBUG = True
            self.TESTING = True
            
            # Logging configuration
            self.LOG_LEVEL = logging.DEBUG
            self.PROPAGATE_EXCEPTIONS = True
            
            # Security Onion API configuration
            # Force the API URL to mock-so-api in testing environment
            if os.getenv('FLASK_ENV') == 'testing':
                self.SO_API_URL = 'https://mock-so-api'
                self.SO_CLIENT_ID = os.getenv('SO_CLIENT_ID', 'test_client_id') 
                self.SO_CLIENT_SECRET = os.getenv('SO_CLIENT_SECRET', 'test_client_secret')
            else:
                self.SO_API_URL = os.getenv('SO_API_URL', 'http://SOMANAGER:443')
                self.SO_CLIENT_ID = os.getenv('SO_CLIENT_ID')
                self.SO_CLIENT_SECRET = os.getenv('SO_CLIENT_SECRET')
            
            self._initialized = True
    
    @classmethod
    def validate(cls):
        """Validate required configuration values are set"""
        config = cls()
        required = [
            ('SO_CLIENT_ID', config.SO_CLIENT_ID),
            ('SO_CLIENT_SECRET', config.SO_CLIENT_SECRET)
        ]
        
        missing = [name for name, value in required if not value]
        
        if missing:
            raise ValueError(
                f"Missing required configuration values: {', '.join(missing)}\n"
                "Please set these values in your .env file."
            )

def get_api_client() -> SecurityOnionAPI:
    """
    Get an instance of the Security Onion API client
    
    Returns:
        SecurityOnionAPI: Configured API client instance
    """
    config = Config()
    config.validate()
    return SecurityOnionAPI(
        base_url=config.SO_API_URL,
        client_id=config.SO_CLIENT_ID,
        client_secret=config.SO_CLIENT_SECRET
    )
