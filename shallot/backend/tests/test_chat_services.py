"""Tests for chat service implementations."""
import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock

from app.core.chat_services import (
    BaseChatService,
    DiscordService,
    SlackService,
    MatrixService,
    TeamsService,
    get_chat_service
)
from app.models.chat_users import ChatService, ChatUserRole


@pytest.fixture
def mock_discord_client():
    """Create a mock Discord client."""
    client = MagicMock()
    client.client = MagicMock()
    client.client.is_ready.return_value = True
    client.send_message = AsyncMock(return_value=True)
    client._alert_channel_id = "12345"
    return client


@pytest.fixture
def mock_slack_client():
    """Create a mock Slack client."""
    client = MagicMock()
    client.client = MagicMock()
    client.get_user_info = AsyncMock(return_value={
        "real_name": "Test User",
        "profile": {
            "real_name": "Test User Profile",
            "display_name": "testuser"
        },
        "name": "testuser"
    })
    client.upload_file = AsyncMock(return_value=True)
    client._alert_channel = "C12345"
    return client


@pytest.fixture
def mock_matrix_client():
    """Create a mock Matrix client."""
    client = MagicMock()
    client._enabled = True
    client.client = MagicMock()
    client.send_message = AsyncMock(return_value=True)
    client.upload_file = AsyncMock(return_value=("mxc://test/file", None))
    client.join_room = AsyncMock(return_value=True)
    client._alert_room = "!room:matrix.org"
    return client


def test_get_chat_service_discord():
    """Test get_chat_service with Discord."""
    # Test getting Discord service
    service = get_chat_service(ChatService.DISCORD)
    assert isinstance(service, DiscordService)
    assert service.service == ChatService.DISCORD


def test_get_chat_service_slack():
    """Test get_chat_service with Slack."""
    # Test getting Slack service
    service = get_chat_service(ChatService.SLACK)
    assert isinstance(service, SlackService)
    assert service.service == ChatService.SLACK


def test_get_chat_service_matrix():
    """Test get_chat_service with Matrix."""
    # Test getting Matrix service
    service = get_chat_service(ChatService.MATRIX)
    assert isinstance(service, MatrixService)
    assert service.service == ChatService.MATRIX


def test_get_chat_service_teams():
    """Test get_chat_service with Teams."""
    # Test getting Teams service
    service = get_chat_service(ChatService.TEAMS)
    assert isinstance(service, TeamsService)
    assert service.service == ChatService.TEAMS


def test_get_chat_service_invalid():
    """Test get_chat_service with invalid service."""
    # Test getting invalid service
    with pytest.raises(ValueError):
        get_chat_service("INVALID_SERVICE")


# Discord service tests

@pytest.mark.asyncio
async def test_discord_format_message():
    """Test Discord format_message."""
    discord_service = DiscordService()
    message = "Test message"
    
    # Format should return the same message for Discord
    formatted = await discord_service.format_message(message)
    assert formatted == message


@pytest.mark.asyncio
async def test_discord_validate_user_id():
    """Test Discord validate_user_id."""
    discord_service = DiscordService()
    
    # Valid Discord IDs are numeric
    assert await discord_service.validate_user_id("123456789") is True
    
    # Invalid Discord IDs are non-numeric
    assert await discord_service.validate_user_id("not_numeric") is False


@pytest.mark.asyncio
async def test_discord_get_display_name():
    """Test Discord get_display_name."""
    discord_service = DiscordService()
    
    # Currently returns None as not implemented
    result = await discord_service.get_display_name("123456789")
    assert result is None


@pytest.mark.asyncio
async def test_discord_send_file(mock_discord_client):
    """Test Discord send_file."""
    with patch("app.core.chat_services.discord.client", mock_discord_client):
        discord_service = DiscordService()
        
        # Test sending file with channel ID
        result = await discord_service.send_file("/path/to/file.txt", "file.txt", "67890")
        
        # Verify file was sent through appropriate channel
        assert result is True
        mock_discord_client.client.get_channel.assert_called_once_with(67890)
        mock_discord_client.client.get_channel.return_value.send.assert_called_once()
        
        # Reset mock
        mock_discord_client.client.get_channel.reset_mock()
        
        # Test sending file without channel ID (uses alert channel)
        result = await discord_service.send_file("/path/to/file.txt", "file.txt")
        
        # Verify file was sent through alert channel
        assert result is True
        mock_discord_client.client.get_channel.assert_called_once_with(12345)
        mock_discord_client.client.get_channel.return_value.send.assert_called_once()


@pytest.mark.asyncio
async def test_discord_send_file_error(mock_discord_client):
    """Test Discord send_file with errors."""
    with patch("app.core.chat_services.discord.client", mock_discord_client):
        discord_service = DiscordService()
        
        # Mock channel not found
        mock_discord_client.client.get_channel.return_value = None
        
        # Test sending file with no valid channel
        result = await discord_service.send_file("/path/to/file.txt", "file.txt", "67890")
        
        # Verify error is handled gracefully
        assert result is False
        mock_discord_client.client.get_channel.assert_called_once_with(67890)
        
        # Mock send raising exception
        mock_discord_client.client.get_channel.return_value = MagicMock()
        mock_discord_client.client.get_channel.return_value.send.side_effect = Exception("Send error")
        
        # Test sending file with error
        result = await discord_service.send_file("/path/to/file.txt", "file.txt", "67890")
        
        # Verify error is handled gracefully
        assert result is False


@pytest.mark.asyncio
async def test_discord_send_message(mock_discord_client):
    """Test Discord send_message."""
    with patch("app.core.chat_services.discord.client", mock_discord_client):
        discord_service = DiscordService()
        
        # Test sending message
        result = await discord_service.send_message("Test message", "channel123")
        
        # Verify message was sent
        assert result is True
        mock_discord_client.send_message.assert_called_once_with("Test message", "channel123")


@pytest.mark.asyncio
async def test_discord_process_command():
    """Test Discord process_command."""
    with patch("app.core.chat_services.process_command") as mock_process, \
         patch.object(DiscordService, "format_message") as mock_format, \
         patch.object(DiscordService, "send_message") as mock_send:
        discord_service = DiscordService()
        
        # Mock command processing
        mock_process.return_value = "Command response"
        mock_format.return_value = "Formatted: Command response"
        mock_send.return_value = True
        
        # Test processing command
        result = await discord_service.process_command(
            "!test",
            "user123",
            username="testuser",
            channel_id="channel123"
        )
        
        # Verify command was processed and response sent
        assert result is None
        mock_process.assert_called_once_with(
            command="!test",
            platform=ChatService.DISCORD,
            user_id="user123",
            username="testuser",
            display_name=None
        )
        mock_format.assert_called_once_with("Command response")
        mock_send.assert_called_once_with("Formatted: Command response", "channel123")


@pytest.mark.asyncio
async def test_discord_process_command_send_fails():
    """Test Discord process_command with send failure."""
    with patch("app.core.chat_services.process_command") as mock_process, \
         patch.object(DiscordService, "format_message") as mock_format, \
         patch.object(DiscordService, "send_message") as mock_send:
        discord_service = DiscordService()
        
        # Mock command processing with send failure
        mock_process.return_value = "Command response"
        mock_format.return_value = "Formatted: Command response"
        mock_send.return_value = False
        
        # Test processing command
        result = await discord_service.process_command(
            "!test",
            "user123",
            username="testuser",
            channel_id="channel123"
        )
        
        # Verify failure message
        assert result == "Failed to send response"


# Slack service tests

@pytest.mark.asyncio
async def test_slack_format_message():
    """Test Slack format_message."""
    slack_service = SlackService()
    message = "Test message"
    
    # Format should return the same message for Slack
    formatted = await slack_service.format_message(message)
    assert formatted == message


@pytest.mark.asyncio
async def test_slack_validate_user_id():
    """Test Slack validate_user_id."""
    slack_service = SlackService()
    
    # Valid Slack IDs start with 'U'
    assert await slack_service.validate_user_id("U12345") is True
    
    # Invalid Slack IDs don't start with 'U'
    assert await slack_service.validate_user_id("12345") is False
    assert await slack_service.validate_user_id("X12345") is False


@pytest.mark.asyncio
async def test_slack_get_display_name(mock_slack_client):
    """Test Slack get_display_name."""
    with patch("app.core.chat_services.slack.client", mock_slack_client):
        slack_service = SlackService()
        
        # Test getting display name
        result = await slack_service.get_display_name("U12345")
        
        # Verify display name is returned with proper priority
        assert result == "Test User"  # real_name has priority
        mock_slack_client.get_user_info.assert_called_once_with("U12345")
        
        # Test fallback to profile.real_name
        user_info = {
            "profile": {
                "real_name": "Test User Profile",
                "display_name": "testuser"
            },
            "name": "testuser"
        }
        mock_slack_client.get_user_info.return_value = user_info
        
        result = await slack_service.get_display_name("U12345")
        assert result == "Test User Profile"
        
        # Test fallback to profile.display_name
        user_info = {
            "profile": {
                "display_name": "testuser"
            },
            "name": "testuser"
        }
        mock_slack_client.get_user_info.return_value = user_info
        
        result = await slack_service.get_display_name("U12345")
        assert result == "testuser"
        
        # Test fallback to name
        user_info = {
            "profile": {},
            "name": "testuser"
        }
        mock_slack_client.get_user_info.return_value = user_info
        
        result = await slack_service.get_display_name("U12345")
        assert result == "testuser"


@pytest.mark.asyncio
async def test_slack_send_file(mock_slack_client):
    """Test Slack send_file."""
    with patch("app.core.chat_services.slack.client", mock_slack_client):
        slack_service = SlackService()
        
        # Test sending file with channel ID
        result = await slack_service.send_file("/path/to/file.txt", "file.txt", "C67890")
        
        # Verify file was sent
        assert result is True
        mock_slack_client.upload_file.assert_called_once_with(
            "/path/to/file.txt", "file.txt", "C67890"
        )
        
        # Reset mock
        mock_slack_client.upload_file.reset_mock()
        
        # Test sending file without channel ID (uses alert channel)
        result = await slack_service.send_file("/path/to/file.txt", "file.txt")
        
        # Verify file was sent through alert channel
        assert result is True
        mock_slack_client.upload_file.assert_called_once_with(
            "/path/to/file.txt", "file.txt", "C12345"
        )


@pytest.mark.asyncio
async def test_slack_send_file_error(mock_slack_client):
    """Test Slack send_file with errors."""
    with patch("app.core.chat_services.slack.client", mock_slack_client):
        slack_service = SlackService()
        
        # Mock client is not initialized
        mock_slack_client.client = None
        
        # Test sending file with no client
        result = await slack_service.send_file("/path/to/file.txt", "file.txt", "C67890")
        
        # Verify error is handled gracefully
        assert result is False
        
        # Restore client
        mock_slack_client.client = MagicMock()
        
        # Mock upload raising exception
        mock_slack_client.upload_file.side_effect = Exception("Upload error")
        
        # Test sending file with error
        result = await slack_service.send_file("/path/to/file.txt", "file.txt", "C67890")
        
        # Verify error is handled gracefully
        assert result is False


@pytest.mark.asyncio
async def test_slack_send_message(mock_slack_client):
    """Test Slack send_message."""
    with patch("app.core.chat_services.slack.client", mock_slack_client):
        slack_service = SlackService()
        
        # Test sending message with channel ID
        result = await slack_service.send_message("Test message", "C67890")
        
        # Verify message was sent
        assert result is True
        mock_slack_client.client.chat_postMessage.assert_called_once_with(
            channel="C67890", text="Test message"
        )
        
        # Reset mock
        mock_slack_client.client.chat_postMessage.reset_mock()
        
        # Test sending message without channel ID (uses alert channel)
        result = await slack_service.send_message("Test message")
        
        # Verify message was sent through alert channel
        assert result is True
        mock_slack_client.client.chat_postMessage.assert_called_once_with(
            channel="C12345", text="Test message"
        )


@pytest.mark.asyncio
async def test_slack_send_message_error(mock_slack_client):
    """Test Slack send_message with errors."""
    with patch("app.core.chat_services.slack.client", mock_slack_client):
        slack_service = SlackService()
        
        # Mock client is not initialized
        mock_slack_client.client = None
        
        # Test sending message with no client
        result = await slack_service.send_message("Test message", "C67890")
        
        # Verify error is handled gracefully
        assert result is False
        
        # Restore client
        mock_slack_client.client = MagicMock()
        
        # Mock send raising exception
        mock_slack_client.client.chat_postMessage.side_effect = Exception("Send error")
        
        # Test sending message with error
        result = await slack_service.send_message("Test message", "C67890")
        
        # Verify error is handled gracefully
        assert result is False


@pytest.mark.asyncio
async def test_slack_process_command():
    """Test Slack process_command."""
    with patch("app.core.chat_services.process_command") as mock_process, \
         patch.object(SlackService, "format_message") as mock_format, \
         patch.object(SlackService, "send_message") as mock_send:
        slack_service = SlackService()
        
        # Mock command processing
        mock_process.return_value = "Command response"
        mock_format.return_value = "Formatted: Command response"
        mock_send.return_value = True
        
        # Test processing command
        result = await slack_service.process_command(
            "!test",
            "U12345",
            username="testuser",
            channel_id="C67890"
        )
        
        # Verify command was processed and response sent
        assert result is None
        mock_process.assert_called_once_with(
            command="!test",
            platform=ChatService.SLACK,
            user_id="U12345",
            username="testuser",
            display_name=None
        )
        mock_format.assert_called_once_with("Command response")
        mock_send.assert_called_once_with("Formatted: Command response", "C67890")


# Matrix service tests

@pytest.mark.asyncio
async def test_matrix_format_message():
    """Test Matrix format_message."""
    matrix_service = MatrixService()
    message = "Test message"
    
    # Format should return the same message for Matrix
    formatted = await matrix_service.format_message(message)
    assert formatted == message


@pytest.mark.asyncio
async def test_matrix_validate_user_id():
    """Test Matrix validate_user_id."""
    matrix_service = MatrixService()
    
    # Valid Matrix IDs are in @user:domain format
    assert await matrix_service.validate_user_id("@user:matrix.org") is True
    
    # Invalid Matrix IDs don't follow the format
    assert await matrix_service.validate_user_id("user@matrix.org") is False
    assert await matrix_service.validate_user_id("user") is False


@pytest.mark.asyncio
async def test_matrix_get_display_name():
    """Test Matrix get_display_name."""
    matrix_service = MatrixService()
    
    # Currently returns None as not implemented
    result = await matrix_service.get_display_name("@user:matrix.org")
    assert result is None


@pytest.mark.asyncio
async def test_matrix_send_file(mock_matrix_client):
    """Test Matrix send_file."""
    with patch("app.core.chat_services.matrix.client", mock_matrix_client), \
         patch("app.core.chat_services.os.path.exists") as mock_exists, \
         patch("app.core.chat_services.os.path.getsize") as mock_getsize, \
         patch("app.core.chat_services.mimetypes.guess_type") as mock_guess_type:
        matrix_service = MatrixService()
        
        # Mock file checks
        mock_exists.return_value = True
        mock_getsize.return_value = 1024  # 1 KB
        mock_guess_type.return_value = ("text/plain", None)
        
        # Test sending file with room ID
        result = await matrix_service.send_file("/path/to/file.txt", "file.txt", "!room2:matrix.org")
        
        # Verify file was sent through appropriate room
        assert result is True
        mock_matrix_client.join_room.assert_called_once_with("!room2:matrix.org")
        mock_matrix_client.upload_file.assert_called_once_with("/path/to/file.txt", "file.txt", "!room2:matrix.org")
        
        # Reset mocks
        mock_matrix_client.join_room.reset_mock()
        mock_matrix_client.upload_file.reset_mock()
        
        # Test sending file without room ID (uses alert room)
        result = await matrix_service.send_file("/path/to/file.txt", "file.txt")
        
        # Verify file was sent through alert room
        assert result is True
        mock_matrix_client.join_room.assert_called_once_with("!room:matrix.org")
        mock_matrix_client.upload_file.assert_called_once_with("/path/to/file.txt", "file.txt", "!room:matrix.org")


@pytest.mark.asyncio
async def test_matrix_send_file_error(mock_matrix_client):
    """Test Matrix send_file with errors."""
    with patch("app.core.chat_services.matrix.client", mock_matrix_client), \
         patch("app.core.chat_services.os.path.exists") as mock_exists, \
         patch("app.core.chat_services.os.path.getsize") as mock_getsize:
        matrix_service = MatrixService()
        
        # Mock file not existing
        mock_exists.return_value = False
        
        # Test sending nonexistent file
        result = await matrix_service.send_file("/path/to/nonexistent.txt", "file.txt", "!room:matrix.org")
        
        # Verify error is handled gracefully
        assert result is False
        
        # Mock file existing but empty
        mock_exists.return_value = True
        mock_getsize.return_value = 0
        
        # Test sending empty file
        result = await matrix_service.send_file("/path/to/empty.txt", "file.txt", "!room:matrix.org")
        
        # Verify error is handled gracefully
        assert result is False
        
        # Mock file too large
        mock_getsize.return_value = 11 * 1024 * 1024  # 11 MB (over 10 MB limit)
        
        # Test sending oversized file
        result = await matrix_service.send_file("/path/to/large.txt", "file.txt", "!room:matrix.org")
        
        # Verify error is handled gracefully
        assert result is False
        
        # Mock file with appropriate size
        mock_getsize.return_value = 1024  # 1 KB
        
        # Mock invalid room ID
        # Test sending to invalid room
        result = await matrix_service.send_file("/path/to/file.txt", "file.txt", "invalid_room")
        
        # Verify error is handled gracefully
        assert result is False
        
        # Mock join room failure
        mock_matrix_client.join_room.return_value = False
        
        # Test sending to room we can't join
        result = await matrix_service.send_file("/path/to/file.txt", "file.txt", "!room:matrix.org")
        
        # Verify error is handled gracefully
        assert result is False
        
        # Mock upload failure
        mock_matrix_client.join_room.return_value = True
        mock_matrix_client.upload_file.return_value = (None, None)
        
        # Test upload failure
        result = await matrix_service.send_file("/path/to/file.txt", "file.txt", "!room:matrix.org")
        
        # Verify error is handled gracefully
        assert result is False


@pytest.mark.asyncio
async def test_matrix_send_message(mock_matrix_client):
    """Test Matrix send_message."""
    with patch("app.core.chat_services.matrix.client", mock_matrix_client):
        matrix_service = MatrixService()
        
        # Test sending message with room ID
        result = await matrix_service.send_message("Test message", "!room2:matrix.org")
        
        # Verify message was sent
        assert result is True
        mock_matrix_client.send_message.assert_called_once_with("!room2:matrix.org", "Test message")
        
        # Reset mock
        mock_matrix_client.send_message.reset_mock()
        
        # Test sending message without room ID (uses alert room)
        result = await matrix_service.send_message("Test message")
        
        # Verify message was sent through alert room
        assert result is True
        mock_matrix_client.send_message.assert_called_once_with("!room:matrix.org", "Test message")


@pytest.mark.asyncio
async def test_matrix_process_command():
    """Test Matrix process_command."""
    with patch("app.core.chat_services.process_command") as mock_process, \
         patch.object(MatrixService, "format_message") as mock_format, \
         patch.object(MatrixService, "send_message") as mock_send:
        matrix_service = MatrixService()
        
        # Mock command processing
        mock_process.return_value = "Command response"
        mock_format.return_value = "Formatted: Command response"
        mock_send.return_value = True
        
        # Test processing command
        result = await matrix_service.process_command(
            "!test",
            "@user:matrix.org",
            username="user",
            channel_id="!room:matrix.org"
        )
        
        # Verify command was processed and response sent
        assert result is None
        mock_process.assert_called_once_with(
            command="!test",
            platform=ChatService.MATRIX,
            user_id="@user:matrix.org",
            username="user",
            display_name=None
        )
        mock_format.assert_called_once_with("Command response")
        mock_send.assert_called_once_with("Formatted: Command response", "!room:matrix.org")