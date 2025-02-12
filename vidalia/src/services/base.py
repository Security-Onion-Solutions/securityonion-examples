"""
Base Security Onion API Client

This module provides the base client class with common functionality for
authentication and request handling that other service modules build upon.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import requests
from base64 import b64encode
import urllib3

# Suppress SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class BaseSecurityOnionClient:
    """Base client class for Security Onion API services"""
    
    def __init__(self, base_url: str, client_id: str, client_secret: str):
        """
        Initialize the base Security Onion API client
        
        Args:
            base_url: Base URL of the Security Onion API
            client_id: OAuth client ID
            client_secret: OAuth client secret
        """
        # Ensure HTTPS protocol
        if not base_url.startswith('https://'):
            base_url = base_url.replace('http://', 'https://')
        
        # Remove any trailing slashes and /connect if present
        base_url = base_url.rstrip('/').replace('/connect', '')
            
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.token: Optional[str] = None
        self.token_expires: Optional[datetime] = None
        
        # Configure session with SSL verification disabled for self-signed certs
        self.session = requests.Session()
        self.session.verify = False

    def _get_auth_header(self) -> Dict[str, str]:
        """Get the Basic auth header for token requests"""
        credentials = b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        return {"Authorization": f"Basic {credentials}"}

    def _get_bearer_header(self) -> Dict[str, str]:
        """Get the Bearer token header for API requests"""
        if not self.token:
            self.authenticate()
        return {"Authorization": f"Bearer {self.token}"}

    def authenticate(self) -> None:
        """Authenticate with the Security Onion API and get an access token"""
        # The oauth endpoint is at /oauth2/token, not under /connect
        auth_url = f"{self.base_url}/oauth2/token"
        data = {"grant_type": "client_credentials"}
        headers = {
            **self._get_auth_header(),
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        logger.debug(f"Authenticating with SO API at: {auth_url}")
        logger.debug(f"Using headers: {json.dumps(headers, indent=2)}")
        logger.debug(f"Using data: {json.dumps(data, indent=2)}")
        
        response = None
        try:
            logger.debug("Sending authentication request...")
            response = self.session.post(
                auth_url,
                headers=headers,
                data=data,
                timeout=10
            )
            logger.debug("Got response from authentication request")
            logger.debug(f"Auth response status: {response.status_code}")
            
            response.raise_for_status()
            
            logger.debug("Authentication successful")
            logger.debug(f"Response content: {response.content}")
            
            if not response.content:
                logger.error("Empty response from OAuth token endpoint")
                raise Exception("Empty response from OAuth token endpoint")
                
            try:
                token_data = response.json()
                logger.debug(f"Token response: {json.dumps(token_data, indent=2)}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse token response: {str(e)}")
                logger.error(f"Raw response content: {response.content}")
                raise
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {str(e)}")
            if response and response.text:
                logger.error(f"Response text: {response.text}")
            if isinstance(e, requests.exceptions.SSLError):
                logger.error("SSL verification error - check certificate")
            elif isinstance(e, requests.exceptions.ConnectionError):
                logger.error("Connection error - check if Security Onion is reachable")
            raise
        
        token_data = response.json()
        self.token = token_data["access_token"]
        # Set token expiration slightly before actual expiry
        self.token_expires = datetime.now() + timedelta(seconds=token_data["expires_in"] - 60)

    def _ensure_authenticated(self) -> None:
        """Ensure we have a valid token, refreshing if necessary"""
        if not self.token or not self.token_expires or datetime.now() >= self.token_expires:
            self.authenticate()
