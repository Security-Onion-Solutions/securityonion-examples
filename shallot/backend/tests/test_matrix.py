"""Tests for Matrix integration."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import nio

from app.core.matrix import MatrixClient
from app.models.settings import Settings
from app.services.settings import get_setting
from app.core.chat_services import MatrixService


@pytest.fixture
def matrix_client():
    """Create MatrixClient instance for testing."""
    return MatrixClient()


@pytest.mark.asyncio
async def test_matrix_client_initialization(matrix_client):
    """Test MatrixClient initialization."""
    assert matrix_client.client is None
    assert not matrix_client._enabled
    assert matrix_client._status == "not initialized"
    assert matrix_client._command_prefix == "!"


@pytest.mark.asyncio
async def test_matrix_client_connect(matrix_client):
    """Test MatrixClient connect method."""
    with patch('nio.AsyncClientConfig') as mock_config, \
         patch('nio.AsyncClient', new_callable=AsyncMock) as mock_client, \
         patch('app.core.matrix.get_setting') as mock_get_setting:
        # Mock config
        mock_config.return_value = MagicMock()
        
        # Mock client
        mock_client_instance = mock_client.return_value
        # Mock successful login response
        mock_login_response = nio.LoginResponse()
        mock_login_response.access_token = "test-token"
        mock_client_instance.login.return_value = mock_login_response
        mock_client_instance.load_store = AsyncMock()
        mock_client_instance.encryption_enabled = True
        mock_client_instance.olm = MagicMock()
        mock_client_instance.trusted_devices = MagicMock()
        
        # Mock settings for encryption enabled (default)
        mock_setting = MagicMock()
        mock_setting.value = json.dumps({
            "enabled": True,
            "homeserverUrl": "https://matrix.org",
            "userId": "@bot:matrix.org",
            "accessToken": "test-token",
            "deviceId": "TESTDEVICE",
            "encryptionEnabled": True
        })
        mock_get_setting.return_value = mock_setting
        
        # Test with encryption enabled
        await matrix_client.initialize()
        
        assert matrix_client.client is not None
        assert matrix_client._status == "initialized"
        assert matrix_client._enabled
        mock_client.assert_called_once()
        mock_client_instance.load_store.assert_called_once()
        mock_config.assert_called_with(encryption_enabled=True, store_sync_tokens=True)
        # Verify login was called with only token
        mock_client_instance.login.assert_called_with(token="test-token")
        
        # Reset mocks for next test
        mock_client.reset_mock()
        mock_client_instance.load_store.reset_mock()
        mock_config.reset_mock()
        
        # Mock settings for encryption disabled
        mock_setting.value = json.dumps({
            "enabled": True,
            "homeserverUrl": "https://matrix.org",
            "userId": "@bot:matrix.org",
            "accessToken": "test-token",
            "deviceId": "TESTDEVICE",
            "encryptionEnabled": False
        })
        
        # Test with encryption disabled
        await matrix_client.initialize()
        
        assert matrix_client.client is not None
        assert matrix_client._status == "initialized"
        assert matrix_client._enabled
        mock_client.assert_called_once()
        mock_client_instance.load_store.assert_not_called()
        mock_config.assert_called_with(encryption_enabled=False, store_sync_tokens=True)


@pytest.mark.asyncio
async def test_matrix_client_connect_login_error(matrix_client):
    """Test MatrixClient connect with login error."""
    with patch('nio.AsyncClient', new_callable=AsyncMock) as mock_client:
        mock_client_instance = mock_client.return_value
        mock_client_instance.login.return_value = nio.LoginError("Login failed")
        
        with pytest.raises(Exception):
            await matrix_client.initialize()
        
        assert matrix_client._status.startswith("error")
        assert not matrix_client._enabled


@pytest.mark.asyncio
async def test_matrix_client_send_message(matrix_client):
    """Test MatrixClient send_message method."""
    # Setup mock client
    matrix_client.client = AsyncMock(spec=nio.AsyncClient)
    matrix_client._enabled = True
    matrix_client._status = "initialized"
    
    room_id = "!test:matrix.org"
    message = "Test message"
    
    # Mock successful message send
    matrix_client.client.room_send.return_value = nio.RoomSendResponse()
    
    # Test sending message
    success = await matrix_client.send_message(room_id, message)
    
    assert success
    matrix_client.client.room_send.assert_called_once()
    call_args = matrix_client.client.room_send.call_args[1]
    assert call_args["room_id"] == room_id
    assert call_args["message_type"] == "m.room.message"
    assert call_args["content"]["body"] == message


@pytest.mark.asyncio
async def test_matrix_client_send_message_error(matrix_client):
    """Test MatrixClient send_message with error."""
    matrix_client.client = AsyncMock(spec=nio.AsyncClient)
    matrix_client._enabled = True
    matrix_client._status = "initialized"
    
    # Mock failed message send
    matrix_client.client.room_send.return_value = nio.RoomSendError("Failed to send")
    
    success = await matrix_client.send_message("!test:matrix.org", "test")
    
    assert not success


@pytest.mark.asyncio
async def test_matrix_client_upload_file(matrix_client):
    """Test MatrixClient upload_file method."""
    matrix_client.client = AsyncMock(spec=nio.AsyncClient)
    matrix_client._enabled = True
    matrix_client._status = "initialized"
    
    room_id = "!test:matrix.org"
    file_content = b"test file content"
    filename = "test.txt"
    
    # Mock successful file upload
    mock_upload_response = MagicMock()
    mock_upload_response.content_uri = "mxc://test/file"
    matrix_client.client.upload.return_value = mock_upload_response
    matrix_client.client.room_send.return_value = nio.RoomSendResponse()
    
    success = await matrix_client.upload_file(room_id, file_content, filename)
    
    assert success
    matrix_client.client.upload.assert_called_once()
    matrix_client.client.room_send.assert_called_once()
    call_args = matrix_client.client.room_send.call_args[1]
    assert call_args["content"]["msgtype"] == "m.file"
    assert call_args["content"]["url"] == "mxc://test/file"


@pytest.mark.asyncio
async def test_matrix_client_join_room(matrix_client):
    """Test MatrixClient join_room method."""
    matrix_client.client = AsyncMock(spec=nio.AsyncClient)
    matrix_client._enabled = True
    matrix_client._status = "initialized"
    
    room_id = "!test:matrix.org"
    
    # Mock successful room join
    matrix_client.client.join.return_value = nio.JoinResponse()
    
    success = await matrix_client.join_room(room_id)
    
    assert success
    matrix_client.client.join.assert_called_once_with(room_id)


@pytest.mark.asyncio
async def test_matrix_client_sync_loop(matrix_client):
    """Test MatrixClient sync loop."""
    matrix_client.client = AsyncMock(spec=nio.AsyncClient)
    matrix_client._enabled = True
    
    # Mock sync response with room invite and message
    mock_sync_response = MagicMock()
    mock_sync_response.rooms.invite = {"!room:matrix.org": MagicMock()}
    mock_sync_response.rooms.join = {
        "!room:matrix.org": MagicMock(
            timeline=MagicMock(
                events=[nio.RoomMessageText(
                    body="!test command",
                    formatted_body=None,
                    format=None,
                    sender="@user:matrix.org",
                    room_id="!room:matrix.org"
                )]
            )
        )
    }
    matrix_client.client.sync.return_value = mock_sync_response
    
    # Mock join and message handling
    matrix_client.join_room = AsyncMock()
    matrix_client._handle_message = AsyncMock()
    
    # Run one iteration of sync loop
    await matrix_client._sync_loop()
    
    matrix_client.join_room.assert_called_once()
    matrix_client._handle_message.assert_called_once()


@pytest.mark.asyncio
async def test_matrix_client_handle_message(matrix_client):
    """Test MatrixClient message handling."""
    matrix_client._enabled = True
    matrix_client._command_prefix = "!"
    
    room_id = "!test:matrix.org"
    event = nio.RoomMessageText(
        body="!test command",
        formatted_body=None,
        format=None,
        sender="@user:matrix.org",
        room_id=room_id
    )
    
    # Mock command processing and Matrix service
    with patch('app.api.commands.process_command') as mock_process, \
         patch('app.core.chat_services.MatrixService') as mock_matrix_service_class:
        mock_process.return_value = "Command response"
        matrix_client.send_message = AsyncMock()
        
        # Setup Matrix service mock
        mock_matrix_service = AsyncMock()
        mock_matrix_service.validate_user_id.return_value = True
        mock_matrix_service.get_display_name.return_value = "Test User"
        mock_matrix_service.format_message.return_value = "Formatted: Command response"
        mock_matrix_service_class.return_value = mock_matrix_service
        
        await matrix_client._handle_message(room_id, event)
        
        # Verify Matrix service usage
        mock_matrix_service.validate_user_id.assert_called_once_with("@user:matrix.org")
        mock_matrix_service.get_display_name.assert_called_once_with("@user:matrix.org")
        mock_matrix_service.format_message.assert_called_once_with("Command response")
        
        # Verify command processing
        mock_process.assert_called_once_with(
            "!test command",
            "matrix",
            user_id="@user:matrix.org",
            username="Test User"
        )
        
        # Verify formatted message was sent
        matrix_client.send_message.assert_called_once_with(room_id, "Formatted: Command response")


@pytest.mark.asyncio
async def test_matrix_client_handle_message_invalid_user(matrix_client):
    """Test MatrixClient message handling with invalid user ID."""
    matrix_client._enabled = True
    matrix_client._command_prefix = "!"
    
    room_id = "!test:matrix.org"
    event = nio.RoomMessageText(
        body="!test command",
        formatted_body=None,
        format=None,
        sender="invalid_user_id",
        room_id=room_id
    )
    
    # Mock Matrix service to reject invalid user ID
    with patch('app.core.chat_services.MatrixService') as mock_matrix_service_class:
        mock_matrix_service = AsyncMock()
        mock_matrix_service.validate_user_id.return_value = False
        mock_matrix_service_class.return_value = mock_matrix_service
        
        matrix_client.send_message = AsyncMock()
        
        await matrix_client._handle_message(room_id, event)
        
        # Verify validation was called
        mock_matrix_service.validate_user_id.assert_called_once_with("invalid_user_id")
        # Verify no message was sent
        matrix_client.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_matrix_client_get_status(matrix_client):
    """Test MatrixClient get_status method."""
    matrix_client._enabled = True
    matrix_client._status = "initialized"
    matrix_client.client = MagicMock()
    matrix_client.client.config = MagicMock()
    matrix_client.client.config.encryption_enabled = True
    matrix_client.client.olm = MagicMock()
    matrix_client.client.device_id = "TESTDEVICE"
    
    status = matrix_client.get_status()
    
    assert status["enabled"] == True
    assert status["status"] == "initialized"
    assert status["connected"] == True
    assert status["alert_notifications"] == False
    assert status["alert_room_configured"] == False
    assert status["command_prefix"] == "!"
    assert "encryption" in status
    assert status["encryption"]["encryption_enabled"] == True
    assert status["encryption"]["olm_account_shared"] == True
    assert status["encryption"]["device_verified"] == True


@pytest.mark.asyncio
async def test_matrix_client_key_verification_loop(matrix_client):
    """Test MatrixClient key verification loop."""
    matrix_client.client = AsyncMock(spec=nio.AsyncClient)
    matrix_client._enabled = True
    
    # Mock key verification states
    matrix_client.client.should_upload_keys = True
    matrix_client.client.should_query_keys = True
    
    # Mock key operations
    matrix_client.client.keys_upload = AsyncMock()
    matrix_client.client.keys_query = AsyncMock()
    
    # Run one iteration of key verification loop
    await matrix_client._key_verification_loop()
    
    matrix_client.client.keys_upload.assert_called_once()
    matrix_client.client.keys_query.assert_called_once()


@pytest.mark.asyncio
async def test_matrix_client_close(matrix_client):
    """Test MatrixClient close method."""
    matrix_client.client = AsyncMock(spec=nio.AsyncClient)
    mock_task = AsyncMock()
    matrix_client._background_tasks.add(mock_task)
    
    await matrix_client.close()
    
    assert matrix_client.client is None
    assert matrix_client._status == "closed"
    mock_task.cancel.assert_called_once()
    matrix_client.client.close.assert_called_once()
