"""Tests for chat service manager module."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.core.chat_manager import ChatServiceManager
from app.models.chat_users import ChatService, ChatUserRole


@pytest.fixture
def chat_manager():
    """Create a chat manager for testing."""
    with patch('app.core.chat_manager.get_chat_service') as mock_get_service:
        # Mock service instances
        mock_discord = AsyncMock()
        mock_slack = AsyncMock()
        mock_matrix = AsyncMock()
        
        # Configure the mock_get_service to return different mocks based on the input
        def get_service_side_effect(service):
            if service == ChatService.DISCORD:
                return mock_discord
            elif service == ChatService.SLACK:
                return mock_slack
            elif service == ChatService.MATRIX:
                return mock_matrix
            else:
                raise ValueError(f"Unsupported service: {service}")
                
        mock_get_service.side_effect = get_service_side_effect
        
        # Create the manager
        manager = ChatServiceManager()
        
        # Store mocks for later assertions
        manager._mocks = {
            ChatService.DISCORD.value: mock_discord,
            ChatService.SLACK.value: mock_slack,
            ChatService.MATRIX.value: mock_matrix
        }
        
        yield manager


def test_initialization(chat_manager):
    """Test ChatServiceManager initialization."""
    # Check if services were properly initialized
    assert len(chat_manager._services) >= 3
    assert ChatService.DISCORD.value in chat_manager._services
    assert ChatService.SLACK.value in chat_manager._services
    assert ChatService.MATRIX.value in chat_manager._services


def test_get_service(chat_manager):
    """Test retrieving services by platform."""
    # Test with string identifiers
    discord_service = chat_manager.get_service("DISCORD")
    assert discord_service == chat_manager._mocks[ChatService.DISCORD.value]
    
    slack_service = chat_manager.get_service("SLACK")
    assert slack_service == chat_manager._mocks[ChatService.SLACK.value]
    
    matrix_service = chat_manager.get_service("MATRIX")
    assert matrix_service == chat_manager._mocks[ChatService.MATRIX.value]
    
    # Test with enum values
    discord_service = chat_manager.get_service(ChatService.DISCORD)
    assert discord_service == chat_manager._mocks[ChatService.DISCORD.value]
    
    # Test with lowercase
    discord_service = chat_manager.get_service("discord")
    assert discord_service == chat_manager._mocks[ChatService.DISCORD.value]
    
    # Test with invalid platform
    assert chat_manager.get_service("INVALID") is None


@pytest.mark.asyncio
async def test_send_message(chat_manager):
    """Test message sending through different platforms."""
    # Set up mocks
    discord_mock = chat_manager._mocks[ChatService.DISCORD.value]
    discord_mock.send_message.return_value = True
    
    slack_mock = chat_manager._mocks[ChatService.SLACK.value]
    slack_mock.send_message.return_value = True
    
    # Test sending with different platforms
    result = await chat_manager.send_message("DISCORD", "Test message")
    assert result is True
    discord_mock.send_message.assert_called_once_with("Test message", None)
    
    result = await chat_manager.send_message("SLACK", "Test message", "channel123")
    assert result is True
    slack_mock.send_message.assert_called_once_with("Test message", "channel123")
    
    # Test with nonexistent service
    result = await chat_manager.send_message("NONEXISTENT", "Test message")
    assert result is False
    
    # Test service error
    discord_mock.send_message.reset_mock()
    discord_mock.send_message.return_value = False
    result = await chat_manager.send_message("DISCORD", "Test message")
    assert result is False


@pytest.mark.asyncio
async def test_send_file(chat_manager):
    """Test file sending through different platforms."""
    # Set up mocks
    discord_mock = chat_manager._mocks[ChatService.DISCORD.value]
    discord_mock.send_file.return_value = True
    
    slack_mock = chat_manager._mocks[ChatService.SLACK.value]
    slack_mock.send_file.return_value = True
    
    # Test sending with different platforms
    result = await chat_manager.send_file("DISCORD", "/path/to/file.txt", "file.txt")
    assert result is True
    discord_mock.send_file.assert_called_once_with("/path/to/file.txt", "file.txt", None)
    
    result = await chat_manager.send_file("SLACK", "/path/to/file.txt", "file.txt", "channel123")
    assert result is True
    slack_mock.send_file.assert_called_once_with("/path/to/file.txt", "file.txt", "channel123")
    
    # Test with nonexistent service
    result = await chat_manager.send_file("NONEXISTENT", "/path/to/file.txt", "file.txt")
    assert result is False
    
    # Test service error
    discord_mock.send_file.reset_mock()
    discord_mock.send_file.return_value = False
    result = await chat_manager.send_file("DISCORD", "/path/to/file.txt", "file.txt")
    assert result is False


@pytest.mark.asyncio
async def test_format_message(chat_manager):
    """Test message formatting for different platforms."""
    # Set up mocks
    discord_mock = chat_manager._mocks[ChatService.DISCORD.value]
    discord_mock.format_message.return_value = "Formatted for Discord: Test message"
    
    slack_mock = chat_manager._mocks[ChatService.SLACK.value]
    slack_mock.format_message.return_value = "Formatted for Slack: Test message"
    
    # Test formatting with different platforms
    result = await chat_manager.format_message("DISCORD", "Test message")
    assert result == "Formatted for Discord: Test message"
    discord_mock.format_message.assert_called_once_with("Test message")
    
    result = await chat_manager.format_message("SLACK", "Test message")
    assert result == "Formatted for Slack: Test message"
    slack_mock.format_message.assert_called_once_with("Test message")
    
    # Test with nonexistent service
    result = await chat_manager.format_message("NONEXISTENT", "Test message")
    assert result is None


@pytest.mark.asyncio
async def test_validate_user_id(chat_manager):
    """Test user ID validation for different platforms."""
    # Set up mocks
    discord_mock = chat_manager._mocks[ChatService.DISCORD.value]
    discord_mock.validate_user_id.return_value = True
    
    slack_mock = chat_manager._mocks[ChatService.SLACK.value]
    slack_mock.validate_user_id.return_value = False
    
    # Test validation with different platforms
    result = await chat_manager.validate_user_id("DISCORD", "123456789")
    assert result is True
    discord_mock.validate_user_id.assert_called_once_with("123456789")
    
    result = await chat_manager.validate_user_id("SLACK", "invalid_id")
    assert result is False
    slack_mock.validate_user_id.assert_called_once_with("invalid_id")
    
    # Test with nonexistent service
    result = await chat_manager.validate_user_id("NONEXISTENT", "user_id")
    assert result is False


@pytest.mark.asyncio
async def test_get_display_name(chat_manager):
    """Test retrieving display names for different platforms."""
    # Set up mocks
    discord_mock = chat_manager._mocks[ChatService.DISCORD.value]
    discord_mock.get_display_name.return_value = "Discord User"
    
    slack_mock = chat_manager._mocks[ChatService.SLACK.value]
    slack_mock.get_display_name.return_value = "Slack User"
    
    # Test getting display names with different platforms
    result = await chat_manager.get_display_name("DISCORD", "123456789")
    assert result == "Discord User"
    discord_mock.get_display_name.assert_called_once_with("123456789")
    
    result = await chat_manager.get_display_name("SLACK", "U12345")
    assert result == "Slack User"
    slack_mock.get_display_name.assert_called_once_with("U12345")
    
    # Test with nonexistent service
    result = await chat_manager.get_display_name("NONEXISTENT", "user_id")
    assert result is None


@pytest.mark.asyncio
async def test_error_handling(chat_manager):
    """Test error handling during service operations."""
    # Set up mock to raise exception
    discord_mock = chat_manager._mocks[ChatService.DISCORD.value]
    discord_mock.send_message.side_effect = Exception("Test error")
    
    # Test exception doesn't propagate but returns False
    result = await chat_manager.send_message("DISCORD", "Test message")
    assert result is False
    discord_mock.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_chat_manager_service_exception():
    """Test ChatServiceManager handling service initialization exceptions."""
    with patch('app.core.chat_manager.get_chat_service') as mock_get_service:
        # Configure the mock to raise an exception for one service
        def get_service_side_effect(service):
            if service == ChatService.DISCORD:
                raise ValueError("Service initialization error")
            return AsyncMock()
                
        mock_get_service.side_effect = get_service_side_effect
        
        # Create the manager - should handle the exception gracefully
        manager = ChatServiceManager()
        
        # Verify that other services were still initialized
        assert len(manager._services) > 0
        # Discord service should be skipped due to the exception
        assert ChatService.DISCORD.value not in manager._services