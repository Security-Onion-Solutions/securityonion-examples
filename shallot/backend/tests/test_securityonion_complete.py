"""Complete tests for the Security Onion client providing 100% coverage."""
import pytest
import json
import base64
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock, ANY, call
import httpx

from app.core.securityonion import SecurityOnionClient, client as global_client
from app.models.settings import Settings as SettingsModel
from tests.utils import await_mock


@pytest.fixture
def mock_settings_db():
    """Fixture to create a mock database with Security Onion settings."""
    settings_mock = MagicMock(spec=SettingsModel)
    settings_mock.value = json.dumps({
        "apiUrl": "https://securityonion.example.com",
        "clientId": "test_client_id", 
        "clientSecret": "test_client_secret",
        "verifySSL": True
    })
    
    # Mock the database session
    db_mock = AsyncMock()
    return db_mock, settings_mock


@pytest.fixture
def mock_token_response():
    """Fixture to create a mock token response."""
    response_mock = AsyncMock(spec=httpx.Response)
    response_mock.status_code = 200
    response_mock.headers = {"content-type": "application/json"}
    response_mock.text = json.dumps({
        "access_token": "test_access_token",
        "expires_in": 3600,
        "token_type": "Bearer"
    })
    response_mock.json.return_value = {
        "access_token": "test_access_token",
        "expires_in": 3600,
        "token_type": "Bearer"
    }
    return response_mock


@pytest.fixture
def mock_health_response():
    """Fixture to create a mock health response."""
    response_mock = AsyncMock(spec=httpx.Response)
    response_mock.status_code = 200
    response_mock.headers = {"content-type": "application/json"}
    response_mock.text = json.dumps({"status": "ok"})
    response_mock.json.return_value = {"status": "ok"}
    return response_mock


@pytest.fixture
def security_onion_client():
    """Return a fresh instance of the SecurityOnionClient."""
    return SecurityOnionClient()


@pytest.mark.asyncio
async def test_initialization_success(mock_settings_db, mock_token_response, mock_health_response, security_onion_client):
    """Test successful initialization of the Security Onion client."""
    db_mock, settings_mock = mock_settings_db
    
    # Mock the database session
    with patch('app.database.AsyncSessionLocal', return_value=db_mock), \
         patch('app.services.settings.get_setting', return_value=await_mock(settings_mock)), \
         patch('httpx.AsyncClient.post', return_value=await_mock(mock_token_response)), \
         patch('httpx.AsyncClient.get', return_value=await_mock(mock_health_response)), \
         patch('app.core.securityonion.httpx.AsyncClient', return_value=AsyncMock()):
        
        # Initialize the client
        await security_onion_client.initialize()
        
        # Verify the client is connected
        assert security_onion_client._connected is True
        assert security_onion_client._last_error is None
        assert security_onion_client._base_url == "https://securityonion.example.com/"
        assert security_onion_client._client_id == "test_client_id"
        assert security_onion_client._client_secret == "test_client_secret"
        assert security_onion_client._verify_ssl is True


@pytest.mark.asyncio
async def test_initialization_missing_settings(mock_settings_db, security_onion_client):
    """Test initialization with missing settings."""
    db_mock, _ = mock_settings_db
    
    # Mock the database session
    with patch('app.database.AsyncSessionLocal', return_value=db_mock), \
         patch('app.services.settings.get_setting', return_value=await_mock(None)):
        
        # Initialize the client
        await security_onion_client.initialize()
        
        # Verify the client is not connected
        assert security_onion_client._connected is False
        assert security_onion_client._last_error == "Security Onion settings not found"


@pytest.mark.asyncio
async def test_initialization_invalid_settings_json(mock_settings_db, security_onion_client):
    """Test initialization with invalid settings JSON."""
    db_mock, settings_mock = mock_settings_db
    settings_mock.value = "invalid json"
    
    # Mock the database session
    with patch('app.database.AsyncSessionLocal', return_value=db_mock), \
         patch('app.services.settings.get_setting', return_value=await_mock(settings_mock)):
        
        # Initialize the client
        await security_onion_client.initialize()
        
        # Verify the client is not connected
        assert security_onion_client._connected is False
        assert "Invalid settings format" in security_onion_client._last_error


@pytest.mark.asyncio
async def test_initialization_missing_required_fields(mock_settings_db, security_onion_client):
    """Test initialization with missing required fields."""
    db_mock, settings_mock = mock_settings_db
    settings_mock.value = json.dumps({
        "apiUrl": "https://securityonion.example.com",
        # Missing clientId and clientSecret
    })
    
    # Mock the database session
    with patch('app.database.AsyncSessionLocal', return_value=db_mock), \
         patch('app.services.settings.get_setting', return_value=await_mock(settings_mock)):
        
        # Initialize the client
        await security_onion_client.initialize()
        
        # Verify the client is not connected
        assert security_onion_client._connected is False
        assert "Missing required settings" in security_onion_client._last_error


@pytest.mark.asyncio
async def test_initialization_url_formatting(mock_settings_db, mock_token_response, mock_health_response, security_onion_client):
    """Test URL formatting during initialization."""
    db_mock, settings_mock = mock_settings_db
    
    # Test different URL formats
    url_tests = [
        "securityonion.example.com",  # No protocol
        "https://securityonion.example.com",  # No trailing slash
        "https://securityonion.example.com/",  # With trailing slash
        "https://securityonion.example.com//",  # Double slash
    ]
    
    for test_url in url_tests:
        settings_mock.value = json.dumps({
            "apiUrl": test_url,
            "clientId": "test_client_id", 
            "clientSecret": "test_client_secret"
        })
        
        # Mock the database session
        with patch('app.database.AsyncSessionLocal', return_value=db_mock), \
             patch('app.services.settings.get_setting', return_value=await_mock(settings_mock)), \
             patch('httpx.AsyncClient.post', return_value=await_mock(mock_token_response)), \
             patch('httpx.AsyncClient.get', return_value=await_mock(mock_health_response)), \
             patch('app.core.securityonion.httpx.AsyncClient', return_value=AsyncMock()):
            
            # Initialize the client
            await security_onion_client.initialize()
            
            # Verify the URL is properly formatted
            assert security_onion_client._base_url.startswith("https://")
            assert security_onion_client._base_url.endswith("/")
            assert "//" not in security_onion_client._base_url[8:]  # No double slashes after protocol


@pytest.mark.asyncio
async def test_initialization_exception(mock_settings_db, security_onion_client):
    """Test initialization with an exception."""
    db_mock, settings_mock = mock_settings_db
    
    # Mock the database session
    with patch('app.database.AsyncSessionLocal', return_value=db_mock), \
         patch('app.services.settings.get_setting', side_effect=Exception("Test error")):
        
        # Initialize the client
        await security_onion_client.initialize()
        
        # Verify the client is not connected
        assert security_onion_client._connected is False
        assert "Initialization error: Test error" in security_onion_client._last_error


@pytest.mark.asyncio
async def test_initialization_http_protocol(mock_settings_db, mock_token_response, mock_health_response, security_onion_client):
    """Test initialization with HTTP protocol."""
    db_mock, settings_mock = mock_settings_db
    settings_mock.value = json.dumps({
        "apiUrl": "http://securityonion.example.com",
        "clientId": "test_client_id", 
        "clientSecret": "test_client_secret",
        "verifySSL": False
    })
    
    # Mock the database session
    with patch('app.database.AsyncSessionLocal', return_value=db_mock), \
         patch('app.services.settings.get_setting', return_value=await_mock(settings_mock)), \
         patch('httpx.AsyncClient.post', return_value=await_mock(mock_token_response)), \
         patch('httpx.AsyncClient.get', return_value=await_mock(mock_health_response)), \
         patch('app.core.securityonion.httpx.AsyncClient', return_value=AsyncMock()):
        
        # Initialize the client
        await security_onion_client.initialize()
        
        # Verify URL is kept as HTTP
        assert security_onion_client._base_url == "http://securityonion.example.com/"
        assert security_onion_client._verify_ssl is False


@pytest.mark.asyncio
async def test_test_connection_success(mock_token_response, mock_health_response, security_onion_client):
    """Test successful connection test."""
    # Setup client with necessary attributes
    security_onion_client._client = AsyncMock()
    security_onion_client._base_url = "https://securityonion.example.com/"
    security_onion_client._client_id = "test_client_id"
    security_onion_client._client_secret = "test_client_secret"
    
    # Mock token and health responses
    with patch.object(security_onion_client._client, 'post', return_value=await_mock(mock_token_response)), \
         patch.object(security_onion_client._client, 'get', return_value=await_mock(mock_health_response)):
        
        # Test the connection
        result = await security_onion_client.test_connection()
        
        # Verify the result
        assert result is True
        assert security_onion_client._connected is True
        assert security_onion_client._last_error is None


@pytest.mark.asyncio
async def test_test_connection_no_client(security_onion_client):
    """Test connection test with no client initialized."""
    # Ensure client is not initialized
    security_onion_client._client = None
    
    # Test the connection
    result = await security_onion_client.test_connection()
    
    # Verify the result
    assert result is False
    assert "Client not initialized" in security_onion_client._last_error


@pytest.mark.asyncio
async def test_test_connection_token_failure(security_onion_client):
    """Test connection test with token failure."""
    # Setup client with necessary attributes
    security_onion_client._client = AsyncMock()
    security_onion_client._base_url = "https://securityonion.example.com/"
    security_onion_client._client_id = "test_client_id"
    security_onion_client._client_secret = "test_client_secret"
    
    # Mock token failure
    with patch.object(security_onion_client, '_ensure_token', return_value=await_mock(False)):
        
        # Test the connection
        result = await security_onion_client.test_connection()
        
        # Verify the result
        assert result is False
        assert security_onion_client._connected is False


@pytest.mark.asyncio
async def test_test_connection_multiple_health_endpoints(mock_token_response, security_onion_client):
    """Test connection test trying multiple health endpoints."""
    # Setup client with necessary attributes
    security_onion_client._client = AsyncMock()
    security_onion_client._base_url = "https://securityonion.example.com/"
    security_onion_client._client_id = "test_client_id"
    security_onion_client._client_secret = "test_client_secret"
    
    # Create mock responses - first fails, second succeeds
    error_response = AsyncMock(spec=httpx.Response)
    error_response.status_code = 404
    error_response.headers = {"content-type": "application/json"}
    error_response.text = json.dumps({"error": "Not found"})
    error_response.json.return_value = {"error": "Not found"}
    
    success_response = AsyncMock(spec=httpx.Response)
    success_response.status_code = 200
    success_response.headers = {"content-type": "application/json"}
    success_response.text = json.dumps({"status": "ok"})
    success_response.json.return_value = {"status": "ok"}
    
    # Mock token success but first health endpoint fails, second succeeds
    with patch.object(security_onion_client._client, 'post', return_value=await_mock(mock_token_response)), \
         patch.object(security_onion_client._client, 'get', side_effect=[
             await_mock(error_response),  # First path fails
             await_mock(success_response)  # Second path succeeds
         ]):
        
        # Test the connection
        result = await security_onion_client.test_connection()
        
        # Verify the result
        assert result is True
        assert security_onion_client._connected is True


@pytest.mark.asyncio
async def test_test_connection_health_response_non_json(mock_token_response, security_onion_client):
    """Test connection test with non-JSON health response."""
    # Setup client with necessary attributes
    security_onion_client._client = AsyncMock()
    security_onion_client._base_url = "https://securityonion.example.com/"
    security_onion_client._client_id = "test_client_id"
    security_onion_client._client_secret = "test_client_secret"
    
    # Create mock response with non-JSON content
    text_response = AsyncMock(spec=httpx.Response)
    text_response.status_code = 200
    text_response.headers = {"content-type": "text/plain"}
    text_response.text = "OK"
    text_response.json = MagicMock(side_effect=json.JSONDecodeError("Invalid JSON", "OK", 0))
    
    # Mock token success but health returns non-JSON
    with patch.object(security_onion_client._client, 'post', return_value=await_mock(mock_token_response)), \
         patch.object(security_onion_client._client, 'get', return_value=await_mock(text_response)):
        
        # Test the connection
        result = await security_onion_client.test_connection()
        
        # Verify the result - still succeeds with 200 status code
        assert result is True
        assert security_onion_client._connected is True


@pytest.mark.asyncio
async def test_test_connection_health_failure(mock_token_response, security_onion_client):
    """Test connection test with health endpoint failure."""
    # Setup client with necessary attributes
    security_onion_client._client = AsyncMock()
    security_onion_client._base_url = "https://securityonion.example.com/"
    security_onion_client._client_id = "test_client_id"
    security_onion_client._client_secret = "test_client_secret"
    
    # Create mock failure response for both health endpoints
    error_response1 = AsyncMock(spec=httpx.Response)
    error_response1.status_code = 500
    error_response1.headers = {"content-type": "application/json"}
    error_response1.text = json.dumps({"detail": "Internal server error"})
    error_response1.json.return_value = {"detail": "Internal server error"}
    
    error_response2 = AsyncMock(spec=httpx.Response)
    error_response2.status_code = 500
    error_response2.headers = {"content-type": "application/json"}
    error_response2.text = json.dumps({"message": "Server error"})
    error_response2.json.return_value = {"message": "Server error"}
    
    # Mock token success but both health endpoints fail
    with patch.object(security_onion_client._client, 'post', return_value=await_mock(mock_token_response)), \
         patch.object(security_onion_client._client, 'get', side_effect=[
             await_mock(error_response1),
             await_mock(error_response2)
         ]):
        
        # Test the connection
        result = await security_onion_client.test_connection()
        
        # Verify the result
        assert result is False
        assert security_onion_client._connected is False
        assert "Server error" in security_onion_client._last_error


@pytest.mark.asyncio
async def test_test_connection_health_exception(mock_token_response, security_onion_client):
    """Test connection test with health endpoint exception."""
    # Setup client with necessary attributes
    security_onion_client._client = AsyncMock()
    security_onion_client._base_url = "https://securityonion.example.com/"
    security_onion_client._client_id = "test_client_id"
    security_onion_client._client_secret = "test_client_secret"
    
    # Mock token success but health exception for both endpoints
    with patch.object(security_onion_client._client, 'post', return_value=await_mock(mock_token_response)), \
         patch.object(security_onion_client._client, 'get', side_effect=Exception("Connection error")):
        
        # Test the connection
        result = await security_onion_client.test_connection()
        
        # Verify the result
        assert result is False
        assert security_onion_client._connected is False
        assert "Connection error" in security_onion_client._last_error


@pytest.mark.asyncio
async def test_ensure_token_existing_valid_token(security_onion_client):
    """Test _ensure_token with existing valid token."""
    # Setup client with valid token
    security_onion_client._access_token = "valid_token"
    security_onion_client._token_expires = datetime.utcnow() + timedelta(hours=1)
    
    # Test ensure token
    result = await security_onion_client._ensure_token()
    
    # Verify result
    assert result is True


@pytest.mark.asyncio
async def test_ensure_token_expired_token(mock_token_response, security_onion_client):
    """Test _ensure_token with expired token."""
    # Setup client with expired token
    security_onion_client._client = AsyncMock()
    security_onion_client._base_url = "https://securityonion.example.com/"
    security_onion_client._client_id = "test_client_id"
    security_onion_client._client_secret = "test_client_secret"
    security_onion_client._access_token = "expired_token"
    security_onion_client._token_expires = datetime.utcnow() - timedelta(hours=1)
    
    # Mock successful token request
    with patch.object(security_onion_client._client, 'post', return_value=await_mock(mock_token_response)):
        
        # Test ensure token
        result = await security_onion_client._ensure_token()
        
        # Verify result
        assert result is True
        assert security_onion_client._access_token == "test_access_token"


@pytest.mark.asyncio
async def test_ensure_token_no_token(mock_token_response, security_onion_client):
    """Test _ensure_token with no existing token."""
    # Setup client with no token
    security_onion_client._client = AsyncMock()
    security_onion_client._base_url = "https://securityonion.example.com/"
    security_onion_client._client_id = "test_client_id"
    security_onion_client._client_secret = "test_client_secret"
    security_onion_client._access_token = None
    security_onion_client._token_expires = None
    
    # Mock successful token request
    with patch.object(security_onion_client._client, 'post', return_value=await_mock(mock_token_response)):
        
        # Test ensure token
        result = await security_onion_client._ensure_token()
        
        # Verify result
        assert result is True
        assert security_onion_client._access_token == "test_access_token"


@pytest.mark.asyncio
async def test_ensure_token_different_paths(mock_token_response, security_onion_client):
    """Test _ensure_token with different token endpoint paths."""
    # Setup client with no token
    security_onion_client._client = AsyncMock()
    security_onion_client._base_url = "https://securityonion.example.com/"
    security_onion_client._client_id = "test_client_id"
    security_onion_client._client_secret = "test_client_secret"
    security_onion_client._access_token = None
    security_onion_client._token_expires = None
    
    # Create sequence of responses - first fails, second succeeds
    error_response = AsyncMock(spec=httpx.Response)
    error_response.status_code = 404
    error_response.headers = {"content-type": "application/json"}
    error_response.text = json.dumps({"detail": "Not found"})
    error_response.json.return_value = {"detail": "Not found"}
    
    # Mock token requests - first fails, second succeeds
    with patch.object(security_onion_client._client, 'post', side_effect=[
        await_mock(error_response),  # First path fails
        await_mock(mock_token_response)  # Second path succeeds
    ]):
        
        # Test ensure token
        result = await security_onion_client._ensure_token()
        
        # Verify result
        assert result is True
        assert security_onion_client._access_token == "test_access_token"


@pytest.mark.asyncio
async def test_ensure_token_missing_fields(security_onion_client):
    """Test _ensure_token with missing fields in response."""
    # Setup client with no token
    security_onion_client._client = AsyncMock()
    security_onion_client._base_url = "https://securityonion.example.com/"
    security_onion_client._client_id = "test_client_id"
    security_onion_client._client_secret = "test_client_secret"
    security_onion_client._access_token = None
    security_onion_client._token_expires = None
    
    # Create response missing access_token or expires_in
    missing_token_response = AsyncMock(spec=httpx.Response)
    missing_token_response.status_code = 200
    missing_token_response.headers = {"content-type": "application/json"}
    missing_token_response.text = json.dumps({"token_type": "Bearer"})  # Missing access_token
    missing_token_response.json.return_value = {"token_type": "Bearer"}
    
    missing_expires_response = AsyncMock(spec=httpx.Response)
    missing_expires_response.status_code = 200
    missing_expires_response.headers = {"content-type": "application/json"}
    missing_expires_response.text = json.dumps({"access_token": "test_token"})  # Missing expires_in
    missing_expires_response.json.return_value = {"access_token": "test_token"}
    
    # Test with missing access_token
    with patch.object(security_onion_client._client, 'post', return_value=await_mock(missing_token_response)):
        result = await security_onion_client._ensure_token()
        assert result is False
        assert "Response missing access_token" in security_onion_client._last_error
    
    # Test with missing expires_in
    with patch.object(security_onion_client._client, 'post', return_value=await_mock(missing_expires_response)):
        result = await security_onion_client._ensure_token()
        assert result is False
        assert "Response missing expires_in" in security_onion_client._last_error


@pytest.mark.asyncio
async def test_ensure_token_non_json_response(security_onion_client):
    """Test _ensure_token with non-JSON response."""
    # Setup client with no token
    security_onion_client._client = AsyncMock()
    security_onion_client._base_url = "https://securityonion.example.com/"
    security_onion_client._client_id = "test_client_id"
    security_onion_client._client_secret = "test_client_secret"
    security_onion_client._access_token = None
    security_onion_client._token_expires = None
    
    # Create text response
    text_response = AsyncMock(spec=httpx.Response)
    text_response.status_code = 200
    text_response.headers = {"content-type": "text/plain"}
    text_response.text = "OK"
    text_response.json = MagicMock(side_effect=json.JSONDecodeError("Invalid JSON", "OK", 0))
    
    # Mock token request with non-JSON response
    with patch.object(security_onion_client._client, 'post', return_value=await_mock(text_response)):
        result = await security_onion_client._ensure_token()
        assert result is False
        assert "Unexpected response type" in security_onion_client._last_error


@pytest.mark.asyncio
async def test_ensure_token_failure(security_onion_client):
    """Test _ensure_token with all paths failing."""
    # Setup client with no token
    security_onion_client._client = AsyncMock()
    security_onion_client._base_url = "https://securityonion.example.com/"
    security_onion_client._client_id = "test_client_id"
    security_onion_client._client_secret = "test_client_secret"
    security_onion_client._access_token = None
    security_onion_client._token_expires = None
    
    # Create error response for all token endpoints
    error_response = AsyncMock(spec=httpx.Response)
    error_response.status_code = 401
    error_response.headers = {"content-type": "application/json"}
    error_response.text = json.dumps({"detail": "Unauthorized"})
    error_response.json.return_value = {"detail": "Unauthorized"}
    
    # Mock token requests - all fail
    with patch.object(security_onion_client._client, 'post', return_value=await_mock(error_response)):
        
        # Test ensure token
        result = await security_onion_client._ensure_token()
        
        # Verify result
        assert result is False
        assert "Unauthorized" in security_onion_client._last_error


@pytest.mark.asyncio
async def test_ensure_token_exception(security_onion_client):
    """Test _ensure_token with exception."""
    # Setup client with no token
    security_onion_client._client = AsyncMock()
    security_onion_client._base_url = "https://securityonion.example.com/"
    security_onion_client._client_id = "test_client_id"
    security_onion_client._client_secret = "test_client_secret"
    security_onion_client._access_token = None
    security_onion_client._token_expires = None
    
    # Mock token request exception
    with patch.object(security_onion_client._client, 'post', side_effect=Exception("Connection error")):
        
        # Test ensure token
        result = await security_onion_client._ensure_token()
        
        # Verify result
        assert result is False
        assert "Connection error" in security_onion_client._last_error


@pytest.mark.asyncio
async def test_ensure_token_auth_encoding(security_onion_client, mock_token_response):
    """Test _ensure_token auth string encoding."""
    # Setup client with no token
    security_onion_client._client = AsyncMock()
    security_onion_client._base_url = "https://securityonion.example.com/"
    security_onion_client._client_id = "test_client_id"
    security_onion_client._client_secret = "test_client_secret"
    security_onion_client._access_token = None
    security_onion_client._token_expires = None
    
    # Mock token request with success and capture headers
    with patch.object(security_onion_client._client, 'post', return_value=await_mock(mock_token_response)) as mock_post:
        # Test ensure token
        result = await security_onion_client._ensure_token()
        
        # Verify auth header
        _, kwargs = mock_post.call_args
        headers = kwargs.get('headers', {})
        auth_header = headers.get('Authorization', '')
        
        # Check Auth header format
        assert auth_header.startswith('Basic ')
        
        # Decode and verify auth string
        auth_parts = base64.b64decode(auth_header[6:]).decode('ascii').split(':')
        assert auth_parts[0] == "test_client_id"
        assert auth_parts[1] == "test_client_secret"


def test_get_headers(security_onion_client):
    """Test _get_headers method."""
    # Setup client with token
    security_onion_client._access_token = "test_token"
    
    # Get headers
    headers = security_onion_client._get_headers()
    
    # Verify headers
    assert headers["Authorization"] == "Bearer test_token"
    assert headers["Content-Type"] == "application/json"


def test_get_status(security_onion_client):
    """Test get_status method."""
    # Test connected status
    security_onion_client._connected = True
    security_onion_client._last_error = None
    status = security_onion_client.get_status()
    assert status["connected"] is True
    assert status["error"] is None
    
    # Test disconnected status with error
    security_onion_client._connected = False
    security_onion_client._last_error = "Connection error"
    status = security_onion_client.get_status()
    assert status["connected"] is False
    assert status["error"] == "Connection error"


def test_get_status_exception(security_onion_client):
    """Test get_status with exception."""
    # Setup to trigger exception
    security_onion_client._connected = "not a boolean"  # Will cause bool() to be called
    security_onion_client._last_error = 123  # Will cause str() to be called
    
    # Get status with exception handling
    status = security_onion_client.get_status()
    assert status["connected"] is False
    assert "Status error:" in status["error"]


@pytest.mark.asyncio
async def test_get_event(mock_token_response, security_onion_client):
    """Test get_event method."""
    # Setup client
    security_onion_client._client = AsyncMock()
    security_onion_client._base_url = "https://securityonion.example.com/"
    security_onion_client._client_id = "test_client_id"
    security_onion_client._client_secret = "test_client_secret"
    security_onion_client._access_token = "test_token"
    security_onion_client._token_expires = datetime.utcnow() + timedelta(hours=1)
    
    # Create mock event response
    event_response = AsyncMock(spec=httpx.Response)
    event_response.status_code = 200
    event_response.json.return_value = {
        "events": [
            {
                "id": "event123",
                "type": "alert",
                "timestamp": "2023-01-01T12:00:00Z"
            }
        ]
    }
    
    # Mock client responses
    with patch.object(security_onion_client, '_ensure_token', return_value=await_mock(True)), \
         patch.object(security_onion_client._client, 'get', return_value=await_mock(event_response)):
        
        # Get event
        event = await security_onion_client.get_event("event123")
        
        # Verify result
        assert event is not None
        assert event["id"] == "event123"
        assert event["type"] == "alert"


@pytest.mark.asyncio
async def test_get_event_not_found(security_onion_client):
    """Test get_event with event not found."""
    # Setup client
    security_onion_client._client = AsyncMock()
    security_onion_client._access_token = "test_token"
    security_onion_client._token_expires = datetime.utcnow() + timedelta(hours=1)
    
    # Create mock empty response
    empty_response = AsyncMock(spec=httpx.Response)
    empty_response.status_code = 200
    empty_response.json.return_value = {"events": []}
    
    # Mock client responses
    with patch.object(security_onion_client, '_ensure_token', return_value=await_mock(True)), \
         patch.object(security_onion_client._client, 'get', return_value=await_mock(empty_response)):
        
        # Get event
        event = await security_onion_client.get_event("nonexistent")
        
        # Verify result
        assert event is None


@pytest.mark.asyncio
async def test_get_event_token_failure(security_onion_client):
    """Test get_event with token failure."""
    # Setup client
    security_onion_client._client = AsyncMock()
    
    # Mock token failure
    with patch.object(security_onion_client, '_ensure_token', return_value=await_mock(False)):
        
        # Get event
        event = await security_onion_client.get_event("event123")
        
        # Verify result
        assert event is None


@pytest.mark.asyncio
async def test_get_event_exception(security_onion_client):
    """Test get_event with exception."""
    # Setup client
    security_onion_client._client = AsyncMock()
    security_onion_client._access_token = "test_token"
    security_onion_client._token_expires = datetime.utcnow() + timedelta(hours=1)
    
    # Mock client responses
    with patch.object(security_onion_client, '_ensure_token', return_value=await_mock(True)), \
         patch.object(security_onion_client._client, 'get', side_effect=Exception("API error")):
        
        # Get event
        event = await security_onion_client.get_event("event123")
        
        # Verify result
        assert event is None
        assert "Failed to get event: API error" in security_onion_client._last_error


@pytest.mark.asyncio
async def test_create_case(security_onion_client):
    """Test create_case method."""
    # Setup client
    security_onion_client._client = AsyncMock()
    security_onion_client._access_token = "test_token"
    security_onion_client._token_expires = datetime.utcnow() + timedelta(hours=1)
    
    # Create mock case response
    case_response = AsyncMock(spec=httpx.Response)
    case_response.status_code = 200
    case_response.json.return_value = {
        "id": "case123",
        "title": "Test Case",
        "status": "New"
    }
    
    # Case data
    case_data = {
        "title": "Test Case",
        "description": "Test case description",
        "priority": "High"
    }
    
    # Mock client responses
    with patch.object(security_onion_client, '_ensure_token', return_value=await_mock(True)), \
         patch.object(security_onion_client._client, 'post', return_value=await_mock(case_response)):
        
        # Create case
        case = await security_onion_client.create_case(case_data)
        
        # Verify result
        assert case is not None
        assert case["id"] == "case123"
        assert case["title"] == "Test Case"
        
        # Verify request
        security_onion_client._client.post.assert_called_once_with(
            "connect/case/",
            headers=ANY,
            json=case_data
        )


@pytest.mark.asyncio
async def test_create_case_token_failure(security_onion_client):
    """Test create_case with token failure."""
    # Setup client
    security_onion_client._client = AsyncMock()
    
    # Case data
    case_data = {
        "title": "Test Case",
        "description": "Test case description"
    }
    
    # Mock token failure
    with patch.object(security_onion_client, '_ensure_token', return_value=await_mock(False)):
        
        # Create case
        case = await security_onion_client.create_case(case_data)
        
        # Verify result
        assert case is None


@pytest.mark.asyncio
async def test_create_case_failure(security_onion_client):
    """Test create_case with API failure."""
    # Setup client
    security_onion_client._client = AsyncMock()
    security_onion_client._access_token = "test_token"
    security_onion_client._token_expires = datetime.utcnow() + timedelta(hours=1)
    
    # Create mock error response
    error_response = AsyncMock(spec=httpx.Response)
    error_response.status_code = 400
    error_response.json.return_value = {"error": "Bad request"}
    
    # Case data
    case_data = {
        "title": "Test Case",
        "description": "Test case description"
    }
    
    # Mock client responses
    with patch.object(security_onion_client, '_ensure_token', return_value=await_mock(True)), \
         patch.object(security_onion_client._client, 'post', return_value=await_mock(error_response)):
        
        # Create case
        case = await security_onion_client.create_case(case_data)
        
        # Verify result
        assert case is None


@pytest.mark.asyncio
async def test_create_case_exception(security_onion_client):
    """Test create_case with exception."""
    # Setup client
    security_onion_client._client = AsyncMock()
    security_onion_client._access_token = "test_token"
    security_onion_client._token_expires = datetime.utcnow() + timedelta(hours=1)
    
    # Case data
    case_data = {
        "title": "Test Case",
        "description": "Test case description"
    }
    
    # Mock client responses
    with patch.object(security_onion_client, '_ensure_token', return_value=await_mock(True)), \
         patch.object(security_onion_client._client, 'post', side_effect=Exception("API error")):
        
        # Create case
        case = await security_onion_client.create_case(case_data)
        
        # Verify result
        assert case is None
        assert "Failed to create case: API error" in security_onion_client._last_error


@pytest.mark.asyncio
async def test_search_events(security_onion_client):
    """Test search_events method."""
    # Setup client
    security_onion_client._client = AsyncMock()
    security_onion_client._access_token = "test_token"
    security_onion_client._token_expires = datetime.utcnow() + timedelta(hours=1)
    
    # Create mock search response
    search_response = AsyncMock(spec=httpx.Response)
    search_response.status_code = 200
    search_response.json.return_value = {
        "events": [
            {
                "id": "event1",
                "type": "alert",
                "timestamp": "2023-01-01T12:00:00Z"
            },
            {
                "id": "event2",
                "type": "alert",
                "timestamp": "2023-01-01T12:30:00Z"
            }
        ],
        "totalEvents": 2
    }
    
    # Mock client responses
    with patch.object(security_onion_client, '_ensure_token', return_value=await_mock(True)), \
         patch.object(security_onion_client._client, 'get', return_value=await_mock(search_response)):
        
        # Search events
        events = await security_onion_client.search_events("tags:alert")
        
        # Verify result
        assert len(events) == 2
        assert events[0]["id"] == "event1"
        assert events[1]["id"] == "event2"
        
        # Verify request params
        call_args = security_onion_client._client.get.call_args[1]
        assert call_args["params"]["query"] == "tags:alert"
        assert "range" in call_args["params"]
        assert call_args["params"]["eventLimit"] == 100  # Default


@pytest.mark.asyncio
async def test_search_events_custom_params(security_onion_client):
    """Test search_events with custom parameters."""
    # Setup client
    security_onion_client._client = AsyncMock()
    security_onion_client._access_token = "test_token"
    security_onion_client._token_expires = datetime.utcnow() + timedelta(hours=1)
    
    # Create mock search response
    search_response = AsyncMock(spec=httpx.Response)
    search_response.status_code = 200
    search_response.json.return_value = {"events": []}
    
    # Mock client responses
    with patch.object(security_onion_client, '_ensure_token', return_value=await_mock(True)), \
         patch.object(security_onion_client._client, 'get', return_value=await_mock(search_response)):
        
        # Search events with custom params
        await security_onion_client.search_events("source.ip:192.168.1.1", time_range="48h", limit=10)
        
        # Verify request params
        call_args = security_onion_client._client.get.call_args[1]
        assert call_args["params"]["query"] == "source.ip:192.168.1.1"
        assert call_args["params"]["eventLimit"] == 10


@pytest.mark.asyncio
async def test_search_events_token_failure(security_onion_client):
    """Test search_events with token failure."""
    # Setup client
    security_onion_client._client = AsyncMock()
    
    # Mock token failure
    with patch.object(security_onion_client, '_ensure_token', return_value=await_mock(False)):
        
        # Search events
        events = await security_onion_client.search_events("tags:alert")
        
        # Verify result
        assert events == []


@pytest.mark.asyncio
async def test_search_events_api_failure(security_onion_client):
    """Test search_events with API failure."""
    # Setup client
    security_onion_client._client = AsyncMock()
    security_onion_client._access_token = "test_token"
    security_onion_client._token_expires = datetime.utcnow() + timedelta(hours=1)
    
    # Create mock error response
    error_response = AsyncMock(spec=httpx.Response)
    error_response.status_code = 500
    error_response.json.return_value = {"error": "Server error"}
    
    # Mock client responses
    with patch.object(security_onion_client, '_ensure_token', return_value=await_mock(True)), \
         patch.object(security_onion_client._client, 'get', return_value=await_mock(error_response)):
        
        # Search events
        events = await security_onion_client.search_events("tags:alert")
        
        # Verify result
        assert events == []


@pytest.mark.asyncio
async def test_search_events_exception(security_onion_client):
    """Test search_events with exception."""
    # Setup client
    security_onion_client._client = AsyncMock()
    security_onion_client._access_token = "test_token"
    security_onion_client._token_expires = datetime.utcnow() + timedelta(hours=1)
    
    # Mock client responses
    with patch.object(security_onion_client, '_ensure_token', return_value=await_mock(True)), \
         patch.object(security_onion_client._client, 'get', side_effect=Exception("API error")):
        
        # Search events
        events = await security_onion_client.search_events("tags:alert")
        
        # Verify result
        assert events == []
        assert "Failed to search events: API error" in security_onion_client._last_error


@pytest.mark.asyncio
async def test_search_events_date_format(security_onion_client):
    """Test search_events date formatting."""
    # Setup client
    security_onion_client._client = AsyncMock()
    security_onion_client._access_token = "test_token"
    security_onion_client._token_expires = datetime.utcnow() + timedelta(hours=1)
    
    # Create mock search response
    search_response = AsyncMock(spec=httpx.Response)
    search_response.status_code = 200
    search_response.json.return_value = {"events": []}
    
    # Test date format for time range
    with patch.object(security_onion_client, '_ensure_token', return_value=await_mock(True)), \
         patch.object(security_onion_client._client, 'get', return_value=await_mock(search_response)) as mock_get:
        
        await security_onion_client.search_events("tags:alert")
        
        # Check the date format in the range parameter
        call_args = mock_get.call_args[1]
        date_range = call_args["params"]["range"]
        assert " - " in date_range
        assert call_args["params"]["format"] == "%Y/%m/%d %I:%M:%S %p"
        assert call_args["params"]["zone"] == "UTC"


@pytest.mark.asyncio
async def test_add_event_to_case(security_onion_client):
    """Test add_event_to_case method."""
    # Setup client
    security_onion_client._client = AsyncMock()
    security_onion_client._access_token = "test_token"
    security_onion_client._token_expires = datetime.utcnow() + timedelta(hours=1)
    
    # Create mock success response
    success_response = AsyncMock(spec=httpx.Response)
    success_response.status_code = 200
    
    # Event fields
    event_fields = {
        "id": "event123",
        "title": "Alert Title",
        "description": "Alert description"
    }
    
    # Mock client responses
    with patch.object(security_onion_client, '_ensure_token', return_value=await_mock(True)), \
         patch.object(security_onion_client._client, 'post', return_value=await_mock(success_response)):
        
        # Add event to case
        result = await security_onion_client.add_event_to_case("case123", event_fields)
        
        # Verify result
        assert result is True
        
        # Verify request
        security_onion_client._client.post.assert_called_once_with(
            "connect/case/events",
            headers=ANY,
            json={
                "caseId": "case123",
                "fields": event_fields
            }
        )


@pytest.mark.asyncio
async def test_add_event_to_case_token_failure(security_onion_client):
    """Test add_event_to_case with token failure."""
    # Setup client
    security_onion_client._client = AsyncMock()
    
    # Event fields
    event_fields = {
        "id": "event123",
        "title": "Alert Title"
    }
    
    # Mock token failure
    with patch.object(security_onion_client, '_ensure_token', return_value=await_mock(False)):
        
        # Add event to case
        result = await security_onion_client.add_event_to_case("case123", event_fields)
        
        # Verify result
        assert result is False


@pytest.mark.asyncio
async def test_add_event_to_case_api_failure(security_onion_client):
    """Test add_event_to_case with API failure."""
    # Setup client
    security_onion_client._client = AsyncMock()
    security_onion_client._access_token = "test_token"
    security_onion_client._token_expires = datetime.utcnow() + timedelta(hours=1)
    
    # Create mock error response
    error_response = AsyncMock(spec=httpx.Response)
    error_response.status_code = 400
    
    # Event fields
    event_fields = {
        "id": "event123",
        "title": "Alert Title"
    }
    
    # Mock client responses
    with patch.object(security_onion_client, '_ensure_token', return_value=await_mock(True)), \
         patch.object(security_onion_client._client, 'post', return_value=await_mock(error_response)):
        
        # Add event to case
        result = await security_onion_client.add_event_to_case("case123", event_fields)
        
        # Verify result
        assert result is False


@pytest.mark.asyncio
async def test_add_event_to_case_api_accepted(security_onion_client):
    """Test add_event_to_case with 202 Accepted response."""
    # Setup client
    security_onion_client._client = AsyncMock()
    security_onion_client._access_token = "test_token"
    security_onion_client._token_expires = datetime.utcnow() + timedelta(hours=1)
    
    # Create mock accepted response
    accepted_response = AsyncMock(spec=httpx.Response)
    accepted_response.status_code = 202
    
    # Event fields
    event_fields = {
        "id": "event123",
        "title": "Alert Title"
    }
    
    # Mock client responses
    with patch.object(security_onion_client, '_ensure_token', return_value=await_mock(True)), \
         patch.object(security_onion_client._client, 'post', return_value=await_mock(accepted_response)):
        
        # Add event to case
        result = await security_onion_client.add_event_to_case("case123", event_fields)
        
        # Verify result
        assert result is True


@pytest.mark.asyncio
async def test_add_event_to_case_exception(security_onion_client):
    """Test add_event_to_case with exception."""
    # Setup client
    security_onion_client._client = AsyncMock()
    security_onion_client._access_token = "test_token"
    security_onion_client._token_expires = datetime.utcnow() + timedelta(hours=1)
    
    # Event fields
    event_fields = {
        "id": "event123",
        "title": "Alert Title"
    }
    
    # Mock client responses
    with patch.object(security_onion_client, '_ensure_token', return_value=await_mock(True)), \
         patch.object(security_onion_client._client, 'post', side_effect=Exception("API error")):
        
        # Add event to case
        result = await security_onion_client.add_event_to_case("case123", event_fields)
        
        # Verify result
        assert result is False
        assert "Failed to add event to case: API error" in security_onion_client._last_error


@pytest.mark.asyncio
async def test_close(security_onion_client):
    """Test close method."""
    # Setup client
    security_onion_client._client = AsyncMock()
    
    # Close client
    await security_onion_client.close()
    
    # Verify client was closed
    security_onion_client._client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_close_no_client(security_onion_client):
    """Test close method with no client."""
    # Setup client with no client
    security_onion_client._client = None
    
    # Close client should not raise exception
    await security_onion_client.close()


@pytest.mark.asyncio
async def test_global_client_instance():
    """Test the global client instance."""
    # Verify global client is an instance of SecurityOnionClient
    assert isinstance(global_client, SecurityOnionClient)