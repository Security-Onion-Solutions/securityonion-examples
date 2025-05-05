import pytest
import json
import base64
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import requests
import responses
from src.services.base import BaseSecurityOnionClient

def test_init_with_http_url():
    """Test initialization with HTTP URL is converted to HTTPS."""
    client = BaseSecurityOnionClient(
        base_url="http://securityonion.local",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    assert client.base_url == "https://securityonion.local"
    assert client.client_id == "test_id"
    assert client.client_secret == "test_secret"
    assert client.token is None
    assert client.token_expires is None

def test_init_with_trailing_slash():
    """Test initialization with trailing slash is handled correctly."""
    client = BaseSecurityOnionClient(
        base_url="https://securityonion.local/",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    assert client.base_url == "https://securityonion.local"

def test_init_with_connect_endpoint():
    """Test initialization with /connect in the URL is handled correctly."""
    client = BaseSecurityOnionClient(
        base_url="https://securityonion.local/connect",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    assert client.base_url == "https://securityonion.local"

def test_get_auth_header():
    """Test basic auth header generation."""
    client = BaseSecurityOnionClient(
        base_url="https://securityonion.local",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    auth_header = client._get_auth_header()
    
    # Verify format is correct
    assert "Authorization" in auth_header
    assert auth_header["Authorization"].startswith("Basic ")
    
    # Decode and verify the encoded credentials
    encoded_part = auth_header["Authorization"].split(" ")[1]
    decoded = base64.b64decode(encoded_part).decode()
    assert decoded == "test_id:test_secret"

def test_get_bearer_header_with_token():
    """Test bearer header generation with existing token."""
    client = BaseSecurityOnionClient(
        base_url="https://securityonion.local",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    # Set a token directly
    client.token = "test_token"
    
    bearer_header = client._get_bearer_header()
    
    assert "Authorization" in bearer_header
    assert bearer_header["Authorization"] == "Bearer test_token"

def test_get_bearer_header_no_token(mock_responses):
    """Test bearer header generation with no token triggers authentication."""
    client = BaseSecurityOnionClient(
        base_url="https://securityonion.local",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    # Mock the authentication endpoint
    mock_responses.post(
        "https://securityonion.local/oauth2/token",
        json={
            "access_token": "new_token",
            "token_type": "Bearer",
            "expires_in": 3600
        },
        status=200
    )
    
    # This should trigger authentication
    bearer_header = client._get_bearer_header()
    
    assert "Authorization" in bearer_header
    assert bearer_header["Authorization"] == "Bearer new_token"
    assert client.token == "new_token"
    # Check that token_expires was set
    assert client.token_expires is not None

def test_authenticate_success(mock_responses):
    """Test successful authentication."""
    client = BaseSecurityOnionClient(
        base_url="https://securityonion.local",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    # Mock the authentication endpoint
    mock_responses.post(
        "https://securityonion.local/oauth2/token",
        json={
            "access_token": "test_token",
            "token_type": "Bearer",
            "expires_in": 3600
        },
        status=200
    )
    
    # Authenticate
    client.authenticate()
    
    # Verify token was set
    assert client.token == "test_token"
    # Verify expiration was set (should be about 3600-60 seconds in the future)
    assert client.token_expires is not None
    assert datetime.now() < client.token_expires
    
    # Check the time difference is roughly correct (allowing for test execution time)
    time_diff = (client.token_expires - datetime.now()).total_seconds()
    assert 3530 <= time_diff <= 3540  # 3600-60 seconds with some margin

def test_authenticate_error(mock_responses):
    """Test authentication error handling."""
    client = BaseSecurityOnionClient(
        base_url="https://securityonion.local",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    # Mock authentication endpoint with error
    mock_responses.post(
        "https://securityonion.local/oauth2/token",
        json={"error": "invalid_client"},
        status=401
    )
    
    # Authentication should raise an exception
    with pytest.raises(requests.exceptions.HTTPError):
        client.authenticate()

def test_authenticate_connection_error():
    """Test handling of connection errors during authentication."""
    client = BaseSecurityOnionClient(
        base_url="https://securityonion.local",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    # Patch the session to simulate a connection error
    with patch.object(client.session, 'post') as mock_post:
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        # Authentication should raise the connection error
        with pytest.raises(requests.exceptions.ConnectionError):
            client.authenticate()

def test_authenticate_ssl_error():
    """Test handling of SSL errors during authentication."""
    client = BaseSecurityOnionClient(
        base_url="https://securityonion.local",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    # Patch the session to simulate an SSL error
    with patch.object(client.session, 'post') as mock_post:
        mock_post.side_effect = requests.exceptions.SSLError("SSL verification failed")
        
        # Authentication should raise the SSL error
        with pytest.raises(requests.exceptions.SSLError):
            client.authenticate()

def test_authenticate_json_decode_error(mock_responses):
    """Test handling of JSON decode errors in the response."""
    client = BaseSecurityOnionClient(
        base_url="https://securityonion.local",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    # Mock authentication endpoint with invalid JSON response
    mock_responses.post(
        "https://securityonion.local/oauth2/token",
        body="Invalid JSON",
        status=200
    )
    
    # Authentication should raise a JSON decode error
    with pytest.raises(json.JSONDecodeError):
        client.authenticate()

def test_authenticate_empty_response(mock_responses):
    """Test handling of empty responses."""
    client = BaseSecurityOnionClient(
        base_url="https://securityonion.local",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    # Mock authentication endpoint with empty response
    mock_responses.post(
        "https://securityonion.local/oauth2/token",
        body="",
        status=200
    )
    
    # Authentication should raise an exception for empty response
    with pytest.raises(Exception, match="Empty response from OAuth token endpoint"):
        client.authenticate()

def test_ensure_authenticated_no_token(mock_responses):
    """Test _ensure_authenticated with no token."""
    client = BaseSecurityOnionClient(
        base_url="https://securityonion.local",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    # Mock the authentication endpoint
    mock_responses.post(
        "https://securityonion.local/oauth2/token",
        json={
            "access_token": "test_token",
            "token_type": "Bearer",
            "expires_in": 3600
        },
        status=200
    )
    
    # This should trigger authentication
    client._ensure_authenticated()
    
    assert client.token == "test_token"
    assert client.token_expires is not None

def test_ensure_authenticated_token_expired(mock_responses):
    """Test _ensure_authenticated with expired token."""
    client = BaseSecurityOnionClient(
        base_url="https://securityonion.local",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    # Set an expired token
    client.token = "expired_token"
    client.token_expires = datetime.now() - timedelta(seconds=60)
    
    # Mock the authentication endpoint
    mock_responses.post(
        "https://securityonion.local/oauth2/token",
        json={
            "access_token": "new_token",
            "token_type": "Bearer",
            "expires_in": 3600
        },
        status=200
    )
    
    # This should trigger re-authentication
    client._ensure_authenticated()
    
    assert client.token == "new_token"
    assert client.token_expires is not None

def test_ensure_authenticated_valid_token(mock_responses):
    """Test _ensure_authenticated with valid token."""
    client = BaseSecurityOnionClient(
        base_url="https://securityonion.local",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    # Set a valid token
    client.token = "valid_token"
    client.token_expires = datetime.now() + timedelta(hours=1)
    
    # Mock to ensure authenticate is not called
    with patch.object(client, 'authenticate') as mock_authenticate:
        client._ensure_authenticated()
        
        # Authenticate should not be called
        mock_authenticate.assert_not_called()
    
    # Token should remain unchanged
    assert client.token == "valid_token"