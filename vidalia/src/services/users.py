"""
Security Onion User Management Service

This module handles user-related operations including:
- User lookup and caching
- User list retrieval
"""
import logging
from datetime import datetime
from typing import Dict, List, Any
from .base import BaseSecurityOnionClient

logger = logging.getLogger(__name__)

class UserService:
    """Service class for Security Onion user operations"""
    
    def __init__(self, api_client: BaseSecurityOnionClient):
        """
        Initialize the user service
        
        Args:
            api_client: An initialized Security Onion API client to use for requests
        """
        self.api_client = api_client
        # Initialize user cache
        self._user_cache = {}
        self._user_cache_time = None
        # Get cache TTL from config, default to 300 seconds
        self._user_cache_ttl = getattr(api_client, 'config', {}).get('USER_CACHE_TTL', 300)

    def get_user_name(self, user_id: str) -> str:
        """
        Get a user's email address from their ID.
        Caches user details to minimize API calls.
        
        Args:
            user_id: The user ID to look up
            
        Returns:
            The user's email address or original ID if user not found
        """
        logger.debug(f"Looking up name for user ID: {user_id}")
        
        # Refresh cache if needed
        if not self._user_cache or not self._user_cache_time or \
           (datetime.now() - self._user_cache_time).total_seconds() > self._user_cache_ttl:
            logger.debug("User cache expired or not initialized, refreshing...")
            try:
                users = self.get_users()
                logger.debug(f"Got {len(users)} users from API")
                
                self._user_cache = {
                    user['id']: user.get('name', user.get('email', user['id']))
                    for user in users
                }
                self._user_cache_time = datetime.now()
                
                logger.debug("User cache refreshed successfully")
                logger.debug(f"Cache contains {len(self._user_cache)} users")
                logger.debug(f"Available user IDs: {list(self._user_cache.keys())}")
            except Exception as e:
                logger.error(f"Failed to refresh user cache: {str(e)}")
                # Return user ID on error but keep old cache if it exists
                if user_id in self._user_cache:
                    return self._user_cache[user_id]
                return user_id
        else:
            logger.debug("Using existing user cache")
            
        name = self._user_cache.get(user_id, 'Unknown User')
        logger.debug(f"Resolved user ID {user_id} to name: {name}")
        return name

    def get_users(self) -> List[Dict[str, Any]]:
        """
        Get list of all users
        
        Returns:
            List of user objects containing user details
        """
        self.api_client._ensure_authenticated()
        
        try:
            response = self.api_client.session.get(
                f"{self.api_client.base_url}/connect/users",
                headers=self.api_client._get_bearer_header(),
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting users: {str(e)}")
            return []  # Return empty list on error
