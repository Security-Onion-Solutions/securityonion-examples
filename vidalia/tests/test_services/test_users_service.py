import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import json
import requests
import responses
from src.services.users import UserService

def test_get_users_success(app, mock_responses):
    """Test successful user retrieval."""
    with app.app_context():
        # Create mock client
        client = MagicMock()
        client.base_url = "https://mock-so-api"
        client.session = requests.Session()
        client._get_bearer_header.return_value = {"Authorization": "Bearer test-token"}
        client._ensure_authenticated = MagicMock()  # Mock the authenticate method
        
        # Mock users endpoint
        mock_responses.get(
            "https://mock-so-api/connect/users",
            json=[
                {"id": "user1", "name": "User One", "email": "user1@example.com"},
                {"id": "user2", "name": "User Two", "email": "user2@example.com"}
            ],
            status=200
        )
        
        service = UserService(client)
        
        # Get users
        users = service.get_users()
        
        # Verify response
        assert len(users) == 2
        assert users[0]["id"] == "user1"
        assert users[0]["name"] == "User One"
        assert users[1]["id"] == "user2"
        assert users[1]["name"] == "User Two"

def test_get_users_api_error(app, mock_responses):
    """Test error handling when users API request fails."""
    with app.app_context():
        # Create mock client
        client = MagicMock()
        client.base_url = "https://mock-so-api"
        client.session = requests.Session()
        client._get_bearer_header.return_value = {"Authorization": "Bearer test-token"}
        client._ensure_authenticated = MagicMock()  # Mock the authenticate method
        
        # Mock users endpoint with error
        mock_responses.get(
            "https://mock-so-api/connect/users",
            json={"error": "API Error"},
            status=500
        )
        
        service = UserService(client)
        
        # Get users
        users = service.get_users()
        
        # Verify error handling returns empty list
        assert users == []

def test_get_users_exception(app):
    """Test error handling for unexpected exceptions in get_users."""
    with app.app_context():
        # Create mock client
        client = MagicMock()
        client.base_url = "https://mock-so-api"
        client.session = MagicMock()
        client._get_bearer_header.return_value = {"Authorization": "Bearer test-token"}
        client._ensure_authenticated = MagicMock()  # Mock the authenticate method
        
        # Make session.get throw an exception
        client.session.get.side_effect = Exception("Connection error")
        
        service = UserService(client)
        
        # Get users
        users = service.get_users()
        
        # Verify error handling returns empty list
        assert users == []

def test_get_user_name_from_cache(app, mock_responses):
    """Test retrieving a user name from cache."""
    with app.app_context():
        # Create mock client with config
        client = MagicMock()
        client.base_url = "https://mock-so-api"
        client.session = requests.Session()
        client._get_bearer_header.return_value = {"Authorization": "Bearer test-token"}
        client._ensure_authenticated = MagicMock()  # Mock the authenticate method
        client.config = {"USER_CACHE_TTL": 300}
        
        # Mock users endpoint
        mock_responses.get(
            "https://mock-so-api/connect/users",
            json=[
                {"id": "user1", "name": "User One", "email": "user1@example.com"},
                {"id": "user2", "name": "User Two", "email": "user2@example.com"}
            ],
            status=200
        )
        
        service = UserService(client)
        
        # Make sure _user_cache_time is set to a datetime
        service._user_cache_time = datetime.now()
        
        # Populate cache first
        first_name = service.get_user_name("user1")
        assert first_name == "User One"
        
        # Mock to ensure get_users isn't called again
        with patch.object(service, 'get_users') as mock_get_users:
            # Get user name from cache
            name = service.get_user_name("user1")
            
            # Verify response
            assert name == "User One"
            # Verify cache was used
            mock_get_users.assert_not_called()

def test_get_user_name_cache_expired(app, mock_responses):
    """Test user name retrieval with expired cache."""
    with app.app_context():
        # Create mock client with short cache TTL
        client = MagicMock()
        client.base_url = "https://mock-so-api"
        client.session = requests.Session()
        client._get_bearer_header.return_value = {"Authorization": "Bearer test-token"}
        client._ensure_authenticated = MagicMock()  # Mock the authenticate method
        client.config = {"USER_CACHE_TTL": 0}  # Ensure cache always expires
        
        # Mock users endpoint for first and second calls
        mock_responses.get(
            "https://mock-so-api/connect/users",
            json=[
                {"id": "user1", "name": "User One", "email": "user1@example.com"}
            ],
            status=200
        )
        
        mock_responses.get(
            "https://mock-so-api/connect/users",
            json=[
                {"id": "user1", "name": "User One Updated", "email": "user1@example.com"}
            ],
            status=200
        )
        
        service = UserService(client)
        
        # Populate cache
        name1 = service.get_user_name("user1")
        assert name1 == "User One"
        
        # Set cache time to past
        service._user_cache_time = datetime.now() - timedelta(seconds=2)
        
        # Get user name again after cache expired
        with patch.object(service, 'get_users', wraps=service.get_users) as mock_get_users:
            name2 = service.get_user_name("user1")
            
            # Verify response has updated and get_users was called
            assert name2 == "User One Updated"
            mock_get_users.assert_called_once()

def test_get_user_name_not_found(app, mock_responses):
    """Test retrieving a user name that doesn't exist."""
    with app.app_context():
        # Create mock client
        client = MagicMock()
        client.base_url = "https://mock-so-api"
        client.session = requests.Session()
        client._get_bearer_header.return_value = {"Authorization": "Bearer test-token"}
        client._ensure_authenticated = MagicMock()  # Mock the authenticate method
        client.config = {"USER_CACHE_TTL": 300}
        
        # Mock users endpoint
        mock_responses.get(
            "https://mock-so-api/connect/users",
            json=[
                {"id": "user1", "name": "User One", "email": "user1@example.com"}
            ],
            status=200
        )
        
        service = UserService(client)
        service._user_cache_time = datetime.now()  # Set cache time to now
        
        # Get name for non-existent user
        name = service.get_user_name("user2")
        
        # Verify response
        assert name == "Unknown User"

def test_get_user_name_cache_refresh_error(app, mock_responses):
    """Test error handling during cache refresh."""
    with app.app_context():
        # Create mock client
        client = MagicMock()
        client.base_url = "https://mock-so-api"
        client.session = requests.Session()
        client._get_bearer_header.return_value = {"Authorization": "Bearer test-token"}
        client._ensure_authenticated = MagicMock()  # Mock the authenticate method
        client.config = {"USER_CACHE_TTL": 300}
        
        # First populate cache successfully
        mock_responses.get(
            "https://mock-so-api/connect/users",
            json=[
                {"id": "user1", "name": "User One", "email": "user1@example.com"}
            ],
            status=200
        )
        
        service = UserService(client)
        name1 = service.get_user_name("user1")
        assert name1 == "User One"
        
        # Force cache to expire
        service._user_cache_time = datetime.now() - timedelta(hours=1)
        
        # Mock API error for refresh
        with patch.object(service, 'get_users') as mock_get_users:
            mock_get_users.side_effect = Exception("API Error")
            
            # Get user name when refresh fails
            name2 = service.get_user_name("user1")
            
            # Should still return from old cache
            assert name2 == "User One"
            
            # Try with non-cached user
            name3 = service.get_user_name("user2")
            
            # Should return user ID when not in cache and refresh fails
            assert name3 == "user2"

def test_get_user_name_name_precedence(app, mock_responses):
    """Test name precedence in user lookup."""
    with app.app_context():
        # Create mock client
        client = MagicMock()
        client.base_url = "https://mock-so-api"
        client.session = requests.Session()
        client._get_bearer_header.return_value = {"Authorization": "Bearer test-token"}
        client._ensure_authenticated = MagicMock()  # Mock the authenticate method
        client.config = {"USER_CACHE_TTL": 300}
        
        # Mock users endpoint with different combinations of fields
        mock_responses.get(
            "https://mock-so-api/connect/users",
            json=[
                {"id": "user1", "name": "User One", "email": "user1@example.com"},  # Has name and email
                {"id": "user2", "email": "user2@example.com"},  # Has email only
                {"id": "user3"}  # Has ID only
            ],
            status=200
        )
        
        service = UserService(client)
        service._user_cache_time = datetime.now()  # Set cache time to prevent expiration
        
        # Test priority: name > email > id
        assert service.get_user_name("user1") == "User One"  # Should use name
        assert service.get_user_name("user2") == "user2@example.com"  # Should use email
        assert service.get_user_name("user3") == "user3"  # Should use ID