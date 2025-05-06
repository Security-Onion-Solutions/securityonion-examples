"""Tests for Security Onion client module."""
import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import httpx

from app.core.securityonion import SecurityOnionClient


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_so_settings():
    """Create mock Security Onion settings."""
    settings = MagicMock()
    settings.value = json.dumps({
        "apiUrl": "https://securityonion.example.com",
        "clientId": "test_client",
        "clientSecret": "test_secret",
        "verifySSL": False
    })
    return settings


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx AsyncClient."""
    client = AsyncMock(spec=httpx.AsyncClient)
    
    # Default to successful responses
    response = AsyncMock()
    response.status_code = 200
    response.text = "{}"
    response.json.return_value = {}
    client.get.return_value = response
    client.post.return_value = response
    
    return client


@pytest.fixture
def so_client():
    """Create a SecurityOnionClient for testing."""
    return SecurityOnionClient()


@pytest.mark.asyncio
async def test_initialize_success(so_client, mock_db, mock_so_settings, mock_httpx_client):
    """Test successful client initialization."""
    with patch("app.core.securityonion.AsyncSessionLocal") as mock_session, \
         patch("app.core.securityonion.get_setting") as mock_get_setting, \
         patch("app.core.securityonion.httpx.AsyncClient") as mock_client_class, \
         patch.object(SecurityOnionClient, "test_connection") as mock_test:
        # Mock session context manager
        mock_session.return_value.__aenter__.return_value = mock_db
        
        # Mock settings retrieval
        mock_get_setting.return_value = mock_so_settings
        
        # Mock client creation
        mock_client_class.return_value = mock_httpx_client
        
        # Mock successful connection test
        mock_test.return_value = True
        
        # Initialize client
        await so_client.initialize()
        
        # Verify client was properly initialized
        assert so_client._base_url == "https://securityonion.example.com/"
        assert so_client._client_id == "test_client"
        assert so_client._client_secret == "test_secret"
        assert so_client._verify_ssl is False
        assert so_client._client == mock_httpx_client
        
        # Verify client creation
        mock_client_class.assert_called_once_with(
            base_url="https://securityonion.example.com/",
            verify=False,
            follow_redirects=True
        )
        
        # Verify connection test was performed
        mock_test.assert_called_once()


@pytest.mark.asyncio
async def test_initialize_missing_settings(so_client, mock_db):
    """Test initialization with missing settings."""
    with patch("app.core.securityonion.AsyncSessionLocal") as mock_session, \
         patch("app.core.securityonion.get_setting") as mock_get_setting:
        # Mock session context manager
        mock_session.return_value.__aenter__.return_value = mock_db
        
        # Mock missing settings
        mock_get_setting.return_value = None
        
        # Initialize client
        await so_client.initialize()
        
        # Verify error state
        assert so_client._connected is False
        assert "Security Onion settings not found" in so_client._last_error


@pytest.mark.asyncio
async def test_initialize_invalid_settings(so_client, mock_db):
    """Test initialization with invalid settings JSON."""
    with patch("app.core.securityonion.AsyncSessionLocal") as mock_session, \
         patch("app.core.securityonion.get_setting") as mock_get_setting:
        # Mock session context manager
        mock_session.return_value.__aenter__.return_value = mock_db
        
        # Mock invalid settings JSON
        settings = MagicMock()
        settings.value = "not_json"
        mock_get_setting.return_value = settings
        
        # Initialize client
        await so_client.initialize()
        
        # Verify error state
        assert so_client._connected is False
        assert "Invalid settings format" in so_client._last_error


@pytest.mark.asyncio
async def test_initialize_missing_required_fields(so_client, mock_db):
    """Test initialization with missing required settings fields."""
    with patch("app.core.securityonion.AsyncSessionLocal") as mock_session, \
         patch("app.core.securityonion.get_setting") as mock_get_setting:
        # Mock session context manager
        mock_session.return_value.__aenter__.return_value = mock_db
        
        # Mock settings with missing fields
        settings = MagicMock()
        settings.value = json.dumps({
            "apiUrl": "https://securityonion.example.com"
            # Missing clientId and clientSecret
        })
        mock_get_setting.return_value = settings
        
        # Initialize client
        await so_client.initialize()
        
        # Verify error state
        assert so_client._connected is False
        assert "Missing required settings" in so_client._last_error
        assert "clientId" in so_client._last_error
        assert "clientSecret" in so_client._last_error


@pytest.mark.asyncio
async def test_initialize_url_formatting(so_client, mock_db, mock_httpx_client):
    """Test URL formatting during initialization."""
    with patch("app.core.securityonion.AsyncSessionLocal") as mock_session, \
         patch("app.core.securityonion.get_setting") as mock_get_setting, \
         patch("app.core.securityonion.httpx.AsyncClient") as mock_client_class, \
         patch.object(SecurityOnionClient, "test_connection") as mock_test:
        # Mock session context manager
        mock_session.return_value.__aenter__.return_value = mock_db
        
        # Mock client creation
        mock_client_class.return_value = mock_httpx_client
        
        # Mock successful connection test
        mock_test.return_value = True
        
        # Test different URL formats
        test_cases = [
            # [input, expected]
            ["securityonion.example.com", "https://securityonion.example.com/"],
            ["http://securityonion.example.com", "http://securityonion.example.com/"],
            ["https://securityonion.example.com", "https://securityonion.example.com/"],
            ["https://securityonion.example.com/", "https://securityonion.example.com/"],
            ["https://securityonion.example.com//", "https://securityonion.example.com/"]
        ]
        
        for input_url, expected_url in test_cases:
            # Mock settings with test URL
            settings = MagicMock()
            settings.value = json.dumps({
                "apiUrl": input_url,
                "clientId": "test_client",
                "clientSecret": "test_secret"
            })
            mock_get_setting.return_value = settings
            
            # Initialize client
            await so_client.initialize()
            
            # Verify URL was properly formatted
            assert so_client._base_url == expected_url
            
            # Verify client was created with formatted URL
            mock_client_class.assert_called_with(
                base_url=expected_url,
                verify=True,  # Default is True
                follow_redirects=True
            )


@pytest.mark.asyncio
async def test_test_connection_success(so_client, mock_httpx_client):
    """Test successful connection test."""
    with patch.object(SecurityOnionClient, "_ensure_token") as mock_ensure_token:
        # Set up client
        so_client._client = mock_httpx_client
        so_client._base_url = "https://securityonion.example.com/"
        
        # Mock successful token
        mock_ensure_token.return_value = True
        
        # Mock successful health check
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = "{}"
        mock_response.json.return_value = {}
        mock_httpx_client.get.return_value = mock_response
        
        # Test connection
        result = await so_client.test_connection()
        
        # Verify success
        assert result is True
        assert so_client._connected is True
        assert so_client._last_error is None
        
        # Verify health check was attempted
        mock_httpx_client.get.assert_called()


@pytest.mark.asyncio
async def test_test_connection_no_client(so_client):
    """Test connection test with no client."""
    # Set client to None
    so_client._client = None
    
    # Test connection
    result = await so_client.test_connection()
    
    # Verify failure
    assert result is False
    assert so_client._connected is False
    assert "Client not initialized" in so_client._last_error


@pytest.mark.asyncio
async def test_test_connection_token_failure(so_client, mock_httpx_client):
    """Test connection test with token failure."""
    with patch.object(SecurityOnionClient, "_ensure_token") as mock_ensure_token:
        # Set up client
        so_client._client = mock_httpx_client
        so_client._base_url = "https://securityonion.example.com/"
        
        # Mock token failure
        mock_ensure_token.return_value = False
        so_client._last_error = "Token error"
        
        # Test connection
        result = await so_client.test_connection()
        
        # Verify failure
        assert result is False
        assert so_client._connected is False
        assert "Token error" in so_client._last_error
        
        # Verify health check was not attempted
        mock_httpx_client.get.assert_not_called()


@pytest.mark.asyncio
async def test_test_connection_health_failure(so_client, mock_httpx_client):
    """Test connection test with health check failure."""
    with patch.object(SecurityOnionClient, "_ensure_token") as mock_ensure_token:
        # Set up client
        so_client._client = mock_httpx_client
        so_client._base_url = "https://securityonion.example.com/"
        
        # Mock successful token
        mock_ensure_token.return_value = True
        
        # Mock failed health check
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = '{"detail": "Not found"}'
        mock_response.json.return_value = {"detail": "Not found"}
        mock_httpx_client.get.return_value = mock_response
        
        # Test connection
        result = await so_client.test_connection()
        
        # Verify failure
        assert result is False
        assert so_client._connected is False
        assert "Not found" in so_client._last_error
        
        # Verify health check was attempted for multiple paths
        assert mock_httpx_client.get.call_count > 0


@pytest.mark.asyncio
async def test_ensure_token_valid_existing(so_client):
    """Test _ensure_token with valid existing token."""
    # Set up existing valid token
    so_client._access_token = "valid_token"
    so_client._token_expires = datetime.utcnow() + timedelta(minutes=10)
    
    # Check token
    result = await so_client._ensure_token()
    
    # Verify existing token was used
    assert result is True


@pytest.mark.asyncio
async def test_ensure_token_expired(so_client, mock_httpx_client):
    """Test _ensure_token with expired token."""
    # Set up expired token
    so_client._client = mock_httpx_client
    so_client._base_url = "https://securityonion.example.com/"
    so_client._client_id = "test_client"
    so_client._client_secret = "test_secret"
    so_client._access_token = "expired_token"
    so_client._token_expires = datetime.utcnow() - timedelta(minutes=10)
    
    # Mock successful token request
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = '{"access_token": "new_token", "expires_in": 3600}'
    mock_response.json.return_value = {"access_token": "new_token", "expires_in": 3600}
    mock_httpx_client.post.return_value = mock_response
    
    # Get new token
    result = await so_client._ensure_token()
    
    # Verify new token was obtained
    assert result is True
    assert so_client._access_token == "new_token"
    assert so_client._token_expires > datetime.utcnow()


@pytest.mark.asyncio
async def test_ensure_token_no_token(so_client, mock_httpx_client):
    """Test _ensure_token with no existing token."""
    # Set up client with no token
    so_client._client = mock_httpx_client
    so_client._base_url = "https://securityonion.example.com/"
    so_client._client_id = "test_client"
    so_client._client_secret = "test_secret"
    so_client._access_token = None
    so_client._token_expires = None
    
    # Mock successful token request
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = '{"access_token": "new_token", "expires_in": 3600}'
    mock_response.json.return_value = {"access_token": "new_token", "expires_in": 3600}
    mock_httpx_client.post.return_value = mock_response
    
    # Get new token
    result = await so_client._ensure_token()
    
    # Verify new token was obtained
    assert result is True
    assert so_client._access_token == "new_token"
    assert so_client._token_expires > datetime.utcnow()


@pytest.mark.asyncio
async def test_ensure_token_request_failure(so_client, mock_httpx_client):
    """Test _ensure_token with token request failure."""
    # Set up client with no token
    so_client._client = mock_httpx_client
    so_client._base_url = "https://securityonion.example.com/"
    so_client._client_id = "test_client"
    so_client._client_secret = "test_secret"
    so_client._access_token = None
    so_client._token_expires = None
    
    # Mock failed token request
    mock_response = AsyncMock()
    mock_response.status_code = 401
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = '{"detail": "Unauthorized"}'
    mock_response.json.return_value = {"detail": "Unauthorized"}
    mock_httpx_client.post.return_value = mock_response
    
    # Try to get token
    result = await so_client._ensure_token()
    
    # Verify failure
    assert result is False
    assert "Unauthorized" in so_client._last_error


@pytest.mark.asyncio
async def test_ensure_token_invalid_response(so_client, mock_httpx_client):
    """Test _ensure_token with invalid response."""
    # Set up client with no token
    so_client._client = mock_httpx_client
    so_client._base_url = "https://securityonion.example.com/"
    so_client._client_id = "test_client"
    so_client._client_secret = "test_secret"
    so_client._access_token = None
    so_client._token_expires = None
    
    # Mock response missing required fields
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = '{"token": "new_token"}'  # Wrong field name
    mock_response.json.return_value = {"token": "new_token"}
    mock_httpx_client.post.return_value = mock_response
    
    # Try to get token
    result = await so_client._ensure_token()
    
    # Verify failure
    assert result is False
    assert "missing access_token" in so_client._last_error.lower()


@pytest.mark.asyncio
async def test_get_headers(so_client):
    """Test _get_headers method."""
    # Set access token
    so_client._access_token = "test_token"
    
    # Get headers
    headers = so_client._get_headers()
    
    # Verify headers structure
    assert headers["Authorization"] == "Bearer test_token"
    assert headers["Content-Type"] == "application/json"


def test_get_status(so_client):
    """Test get_status method."""
    # Test connected status
    so_client._connected = True
    so_client._last_error = None
    
    status = so_client.get_status()
    assert status["connected"] is True
    assert status["error"] is None
    
    # Test disconnected status with error
    so_client._connected = False
    so_client._last_error = "Connection error"
    
    status = so_client.get_status()
    assert status["connected"] is False
    assert status["error"] == "Connection error"


@pytest.mark.asyncio
async def test_get_event(so_client, mock_httpx_client):
    """Test get_event method."""
    with patch.object(SecurityOnionClient, "_ensure_token") as mock_ensure_token:
        # Set up client
        so_client._client = mock_httpx_client
        so_client._access_token = "test_token"
        
        # Mock successful token
        mock_ensure_token.return_value = True
        
        # Mock successful event retrieval
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "events": [
                {"_id": "event1", "data": "event_data"}
            ]
        }
        mock_httpx_client.get.return_value = mock_response
        
        # Get event
        event = await so_client.get_event("event1")
        
        # Verify event was retrieved
        assert event == {"_id": "event1", "data": "event_data"}
        mock_httpx_client.get.assert_called_once_with(
            "connect/events/?query=_id:event1",
            headers=so_client._get_headers()
        )


@pytest.mark.asyncio
async def test_get_event_not_found(so_client, mock_httpx_client):
    """Test get_event with event not found."""
    with patch.object(SecurityOnionClient, "_ensure_token") as mock_ensure_token:
        # Set up client
        so_client._client = mock_httpx_client
        so_client._access_token = "test_token"
        
        # Mock successful token
        mock_ensure_token.return_value = True
        
        # Mock empty event response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"events": []}
        mock_httpx_client.get.return_value = mock_response
        
        # Get nonexistent event
        event = await so_client.get_event("nonexistent")
        
        # Verify no event was found
        assert event is None


@pytest.mark.asyncio
async def test_get_event_token_failure(so_client, mock_httpx_client):
    """Test get_event with token failure."""
    with patch.object(SecurityOnionClient, "_ensure_token") as mock_ensure_token:
        # Set up client
        so_client._client = mock_httpx_client
        
        # Mock token failure
        mock_ensure_token.return_value = False
        
        # Try to get event
        event = await so_client.get_event("event1")
        
        # Verify failure
        assert event is None
        mock_httpx_client.get.assert_not_called()


@pytest.mark.asyncio
async def test_create_case(so_client, mock_httpx_client):
    """Test create_case method."""
    with patch.object(SecurityOnionClient, "_ensure_token") as mock_ensure_token:
        # Set up client
        so_client._client = mock_httpx_client
        so_client._access_token = "test_token"
        
        # Mock successful token
        mock_ensure_token.return_value = True
        
        # Mock successful case creation
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "case1", "title": "Test Case"}
        mock_httpx_client.post.return_value = mock_response
        
        # Create case
        case_data = {"title": "Test Case", "status": "new"}
        case = await so_client.create_case(case_data)
        
        # Verify case was created
        assert case == {"id": "case1", "title": "Test Case"}
        mock_httpx_client.post.assert_called_once_with(
            "connect/case/",
            headers=so_client._get_headers(),
            json=case_data
        )


@pytest.mark.asyncio
async def test_create_case_failure(so_client, mock_httpx_client):
    """Test create_case with creation failure."""
    with patch.object(SecurityOnionClient, "_ensure_token") as mock_ensure_token:
        # Set up client
        so_client._client = mock_httpx_client
        so_client._access_token = "test_token"
        
        # Mock successful token
        mock_ensure_token.return_value = True
        
        # Mock failed case creation
        mock_response = AsyncMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Invalid data"}
        mock_httpx_client.post.return_value = mock_response
        
        # Try to create case
        case_data = {"title": "Test Case", "status": "new"}
        case = await so_client.create_case(case_data)
        
        # Verify failure
        assert case is None


@pytest.mark.asyncio
async def test_search_events(so_client, mock_httpx_client):
    """Test search_events method."""
    with patch.object(SecurityOnionClient, "_ensure_token") as mock_ensure_token:
        # Set up client
        so_client._client = mock_httpx_client
        so_client._access_token = "test_token"
        
        # Mock successful token
        mock_ensure_token.return_value = True
        
        # Mock successful event search
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "events": [
                {"_id": "event1", "data": "event1_data"},
                {"_id": "event2", "data": "event2_data"}
            ]
        }
        mock_httpx_client.get.return_value = mock_response
        
        # Search events
        events = await so_client.search_events("test query")
        
        # Verify events were found
        assert len(events) == 2
        assert events[0]["_id"] == "event1"
        assert events[1]["_id"] == "event2"
        
        # Verify request parameters
        mock_httpx_client.get.assert_called_once()
        call_args = mock_httpx_client.get.call_args[1]
        assert call_args["headers"] == so_client._get_headers()
        assert call_args["params"]["query"] == "test query"
        assert "range" in call_args["params"]
        assert call_args["params"]["eventLimit"] == 100  # Default limit


@pytest.mark.asyncio
async def test_search_events_custom_limit(so_client, mock_httpx_client):
    """Test search_events with custom limit."""
    with patch.object(SecurityOnionClient, "_ensure_token") as mock_ensure_token:
        # Set up client
        so_client._client = mock_httpx_client
        so_client._access_token = "test_token"
        
        # Mock successful token
        mock_ensure_token.return_value = True
        
        # Mock successful event search
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"events": []}
        mock_httpx_client.get.return_value = mock_response
        
        # Search events with custom limit
        await so_client.search_events("test query", limit=10)
        
        # Verify request parameters
        call_args = mock_httpx_client.get.call_args[1]
        assert call_args["params"]["eventLimit"] == 10


@pytest.mark.asyncio
async def test_search_events_no_results(so_client, mock_httpx_client):
    """Test search_events with no results."""
    with patch.object(SecurityOnionClient, "_ensure_token") as mock_ensure_token:
        # Set up client
        so_client._client = mock_httpx_client
        so_client._access_token = "test_token"
        
        # Mock successful token
        mock_ensure_token.return_value = True
        
        # Mock empty search results
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"events": []}
        mock_httpx_client.get.return_value = mock_response
        
        # Search events
        events = await so_client.search_events("test query")
        
        # Verify no events were found
        assert len(events) == 0


@pytest.mark.asyncio
async def test_add_event_to_case(so_client, mock_httpx_client):
    """Test add_event_to_case method."""
    with patch.object(SecurityOnionClient, "_ensure_token") as mock_ensure_token:
        # Set up client
        so_client._client = mock_httpx_client
        so_client._access_token = "test_token"
        
        # Mock successful token
        mock_ensure_token.return_value = True
        
        # Mock successful event addition
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_httpx_client.post.return_value = mock_response
        
        # Add event to case
        event_fields = {"id": "event1", "type": "alert"}
        result = await so_client.add_event_to_case("case1", event_fields)
        
        # Verify event was added
        assert result is True
        mock_httpx_client.post.assert_called_once_with(
            "connect/case/events",
            headers=so_client._get_headers(),
            json={"caseId": "case1", "fields": event_fields}
        )


@pytest.mark.asyncio
async def test_add_event_to_case_failure(so_client, mock_httpx_client):
    """Test add_event_to_case with failure."""
    with patch.object(SecurityOnionClient, "_ensure_token") as mock_ensure_token:
        # Set up client
        so_client._client = mock_httpx_client
        so_client._access_token = "test_token"
        
        # Mock successful token
        mock_ensure_token.return_value = True
        
        # Mock failed event addition
        mock_response = AsyncMock()
        mock_response.status_code = 400
        mock_httpx_client.post.return_value = mock_response
        
        # Try to add event to case
        event_fields = {"id": "event1", "type": "alert"}
        result = await so_client.add_event_to_case("case1", event_fields)
        
        # Verify failure
        assert result is False


@pytest.mark.asyncio
async def test_close(so_client, mock_httpx_client):
    """Test close method."""
    # Set up client
    so_client._client = mock_httpx_client
    
    # Close client
    await so_client.close()
    
    # Verify client was closed
    mock_httpx_client.aclose.assert_called_once()
@pytest.mark.asyncio
async def test_initialize_exception_handling(so_client, mock_db):
    """Test exception handling in the initialize method."""
    with patch("app.core.securityonion.AsyncSessionLocal") as mock_session, \
         patch("app.core.securityonion.get_setting") as mock_get_setting:
        # Mock session context manager
        mock_session.return_value.__aenter__.return_value = mock_db
        
        # Mock get_setting to raise an exception
        mock_get_setting.side_effect = Exception("Database connection error")
        
        # Initialize client
        await so_client.initialize()
        
        # Verify error state
        assert so_client._connected is False
        assert "Initialization error: Database connection error" in so_client._last_error


@pytest.mark.asyncio
async def test_test_connection_health_endpoint_exception(so_client, mock_httpx_client):
    """Test exception handling in the test_connection method when health endpoint fails."""
    with patch.object(SecurityOnionClient, "_ensure_token") as mock_ensure_token:
        # Set up client
        so_client._client = mock_httpx_client
        so_client._base_url = "https://securityonion.example.com/"
        
        # Mock successful token
        mock_ensure_token.return_value = True
        
        # Mock health endpoint request raising an exception
        mock_httpx_client.get.side_effect = httpx.RequestError("Connection refused")
        
        # Test connection
        result = await so_client.test_connection()
        
        # Verify failure
        assert result is False
        assert so_client._connected is False
        assert "Connection refused" in so_client._last_error


@pytest.mark.asyncio
async def test_get_event_exception_handling(so_client, mock_httpx_client):
    """Test exception handling in the get_event method."""
    with patch.object(SecurityOnionClient, "_ensure_token") as mock_ensure_token:
        # Set up client
        so_client._client = mock_httpx_client
        so_client._access_token = "test_token"
        
        # Mock successful token
        mock_ensure_token.return_value = True
        
        # Mock get request raising an exception
        mock_httpx_client.get.side_effect = Exception("Network error")
        
        # Try to get event
        event = await so_client.get_event("event1")
        
        # Verify failure
        assert event is None
        assert so_client._last_error == "Failed to get event: Network error"


@pytest.mark.asyncio
async def test_search_events_exception_handling(so_client, mock_httpx_client):
    """Test exception handling in the search_events method."""
    with patch.object(SecurityOnionClient, "_ensure_token") as mock_ensure_token:
        # Set up client
        so_client._client = mock_httpx_client
        so_client._access_token = "test_token"
        
        # Mock successful token
        mock_ensure_token.return_value = True
        
        # Mock search request raising an exception
        mock_httpx_client.get.side_effect = Exception("API timeout")
        
        # Try to search events
        events = await so_client.search_events("test query")
        
        # Verify failure
        assert events == []
        assert so_client._last_error == "Failed to search events: API timeout"


def test_get_status_exception_handling(so_client):
    """Test exception handling in the get_status method."""
    # Set up client to trigger exception
    so_client._connected = "not-a-boolean"  # Will cause bool() to be called on a non-boolean
    
    # Get status
    status = so_client.get_status()
    
    # Verify error handling
    assert status["connected"] is False
    assert "Status error:" in status["error"]
@pytest.mark.asyncio
async def test_create_case_exception_handling(so_client, mock_httpx_client):
    """Test exception handling in the create_case method."""
    with patch.object(SecurityOnionClient, "_ensure_token") as mock_ensure_token:
        # Set up client
        so_client._client = mock_httpx_client
        so_client._access_token = "test_token"
        
        # Mock successful token
        mock_ensure_token.return_value = True
        
        # Mock post request raising an exception
        mock_httpx_client.post.side_effect = Exception("Server error")
        
        # Try to create case
        case_data = {"title": "Test Case", "status": "new"}
        case = await so_client.create_case(case_data)
        
        # Verify failure
        assert case is None
        assert so_client._last_error == "Failed to create case: Server error"
@pytest.mark.asyncio
async def test_add_event_to_case_exception_handling(so_client, mock_httpx_client):
    """Test exception handling in the add_event_to_case method."""
    with patch.object(SecurityOnionClient, "_ensure_token") as mock_ensure_token:
        # Set up client
        so_client._client = mock_httpx_client
        so_client._access_token = "test_token"
        
        # Mock successful token
        mock_ensure_token.return_value = True
        
        # Mock post request raising an exception
        mock_httpx_client.post.side_effect = Exception("Connection timeout")
        
        # Try to add event to case
        event_fields = {"id": "event1", "type": "alert"}
        result = await so_client.add_event_to_case("case1", event_fields)
        
        # Verify failure
        assert result is False
        assert so_client._last_error == "Failed to add event to case: Connection timeout"