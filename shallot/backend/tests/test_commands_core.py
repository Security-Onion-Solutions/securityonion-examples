"""Tests for command processing core module."""
import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.api.commands import process_command
from app.api.commands.core import (
    router,
    validate_command_access,
    list_commands,
    test_command
)
from app.models.chat_users import ChatService, ChatUserRole
from app.models.users import User, UserType
from app.schemas.commands import (
    Command,
    CommandTestRequest,
    CommandTestResponse,
    CommandListResponse,
    AVAILABLE_COMMANDS,
    PlatformType
)
from app.core.permissions import CommandPermission

client = TestClient(app)


@pytest.fixture

def await_mock(return_value):
    """Helper function to make mock return values awaitable in Python 3.13."""
    async def _awaitable():
        return return_value
    return _awaitable()

def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    user.is_active = True
    user.is_superuser = False
    user.user_type = UserType.WEB
    return user


@pytest.fixture
def mock_chat_user():
    """Create a mock chat user."""
    user = MagicMock()
    user.platform_id = "12345"
    user.username = "chatuser"
    user.platform = ChatService.DISCORD
    user.role = ChatUserRole.BASIC
    return user


@pytest.fixture
def mock_command():
    """Create a mock command definition."""
    return Command(
        name="test",
        description="Test command",
        example="!test",  # Changed from examples (list) to example (str) and removed usage
        platforms=["DISCORD", "SLACK"],
        permission=CommandPermission.BASIC
    )


@pytest.mark.asyncio
async def test_process_command_valid():
    """Test process_command with valid command."""
    with patch("app.api.commands.get_setting") as mock_get_setting, \
         patch("app.api.commands.help.process") as mock_process:
        # Mock platform settings
        mock_setting = MagicMock()
        mock_setting.value = json.dumps({"commandPrefix": "!"})
        mock_get_setting.return_value = mock_setting
        
        # Mock command process
        mock_process.return_value = "Help information"
        
        # Test processing a valid command
        result = await process_command(
            command="!help",
            platform=ChatService.DISCORD,
            user_id="12345",
            username="testuser"
        )
        
        # Verify
        assert result == "Help information"
        mock_get_setting.assert_called_once()
        mock_process.assert_called_once()


@pytest.mark.asyncio
async def test_process_command_missing_prefix():
    """Test process_command with missing prefix."""
    with patch("app.api.commands.get_setting") as mock_get_setting:
        # Mock platform settings
        mock_setting = MagicMock()
        mock_setting.value = json.dumps({"commandPrefix": "!"})
        mock_get_setting.return_value = mock_setting
        
        # Test processing a command without prefix
        result = await process_command(
            command="help",
            platform=ChatService.DISCORD,
            user_id="12345",
            username="testuser"
        )
        
        # Verify
        assert "Commands must start with !" in result
        mock_get_setting.assert_called_once()


@pytest.mark.asyncio
async def test_process_command_empty():
    """Test process_command with empty command."""
    with patch("app.api.commands.get_setting") as mock_get_setting:
        # Mock platform settings
        mock_setting = MagicMock()
        mock_setting.value = json.dumps({"commandPrefix": "!"})
        mock_get_setting.return_value = mock_setting
        
        # Test processing an empty command
        result = await process_command(
            command="!",
            platform=ChatService.DISCORD,
            user_id="12345",
            username="testuser"
        )
        
        # Verify
        assert "Please provide a command" in result
        mock_get_setting.assert_called_once()


@pytest.mark.asyncio
async def test_process_command_unknown():
    """Test process_command with unknown command."""
    with patch("app.api.commands.get_setting") as mock_get_setting:
        # Mock platform settings
        mock_setting = MagicMock()
        mock_setting.value = json.dumps({"commandPrefix": "!"})
        mock_get_setting.return_value = mock_setting
        
        # Test processing an unknown command
        result = await process_command(
            command="!unknown",
            platform=ChatService.DISCORD,
            user_id="12345",
            username="testuser"
        )
        
        # Verify
        assert "Unknown command: unknown" in result
        mock_get_setting.assert_called_once()


@pytest.mark.asyncio
async def test_process_command_error():
    """Test process_command handling errors."""
    with patch("app.api.commands.get_setting") as mock_get_setting, \
         patch("app.api.commands.help.process") as mock_process:
        # Mock platform settings
        mock_setting = MagicMock()
        mock_setting.value = json.dumps({"commandPrefix": "!"})
        mock_get_setting.return_value = mock_setting
        
        # Mock command process with error
        mock_process.side_effect = Exception("Command error")
        
        # Test processing a command that raises an error
        result = await process_command(
            command="!help",
            platform=ChatService.DISCORD,
            user_id="12345",
            username="testuser"
        )
        
        # Verify
        assert "Error executing command: Command error" in result
        mock_get_setting.assert_called_once()
        mock_process.assert_called_once()


@pytest.mark.asyncio
async def test_validate_command_access_public(mock_command, mock_chat_user):
    """Test validate_command_access with public command."""
    with patch("app.api.commands.core.get_command_permission") as mock_get_permission, \
         patch("app.api.commands.core.get_chat_user_by_platform_id") as mock_get_user, \
         patch("app.api.commands.core.has_permission") as mock_has_permission:
        # Set command to public
        mock_get_permission.return_value = CommandPermission.PUBLIC
        
        # No user_id provided
        result = await validate_command_access(mock_command, "DISCORD")
        
        # Verify public command is accessible without user_id
        assert result is True
        mock_get_permission.assert_called_once_with(mock_command.name)
        mock_get_user.assert_not_called()
        mock_has_permission.assert_not_called()


@pytest.mark.asyncio
async def test_validate_command_access_with_user(mock_command, mock_chat_user):
    """Test validate_command_access with user with sufficient permissions."""
    with patch("app.api.commands.core.get_command_permission") as mock_get_permission, \
         patch("app.api.commands.core.AsyncSessionLocal") as mock_session, \
         patch("app.api.commands.core.get_chat_user_by_platform_id") as mock_get_user, \
         patch("app.api.commands.core.has_permission") as mock_has_permission:
        # Mock session context manager
        mock_session_instance = MagicMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Set command to require basic permission
        mock_get_permission.return_value = CommandPermission.BASIC
        
        # Mock finding the user
        mock_get_user.return_value = mock_chat_user
        
        # Mock permission check
        mock_has_permission.return_value = True
        
        # User has permissions
        result = await validate_command_access(mock_command, "DISCORD", "12345")
        
        # Verify
        assert result is True
        mock_get_permission.assert_called_once_with(mock_command.name)
        mock_get_user.assert_called_once_with(mock_session_instance, "12345", ChatService.DISCORD)
        mock_has_permission.assert_called_once_with(mock_chat_user.role, CommandPermission.BASIC)


@pytest.mark.asyncio
async def test_validate_command_access_insufficient_permissions(mock_command):
    """Test validate_command_access with user without sufficient permissions."""
    with patch("app.api.commands.core.get_command_permission") as mock_get_permission, \
         patch("app.api.commands.core.AsyncSessionLocal") as mock_session, \
         patch("app.api.commands.core.get_chat_user_by_platform_id") as mock_get_user, \
         patch("app.api.commands.core.has_permission") as mock_has_permission:
        # Mock session context manager
        mock_session_instance = MagicMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Set command to require admin permission
        mock_get_permission.return_value = CommandPermission.ADMIN
        
        # Mock finding the user
        user_with_basic_role = MagicMock()
        user_with_basic_role.role = ChatUserRole.BASIC
        mock_get_user.return_value = user_with_basic_role
        
        # Mock permission check - user doesn't have permission
        mock_has_permission.return_value = False
        
        # Test with insufficient permissions
        result = await validate_command_access(mock_command, "DISCORD", "12345")
        
        # Verify
        assert result is False
        mock_get_permission.assert_called_once_with(mock_command.name)
        mock_get_user.assert_called_once_with(mock_session_instance, "12345", ChatService.DISCORD)
        mock_has_permission.assert_called_once_with(ChatUserRole.BASIC, CommandPermission.ADMIN)


@pytest.mark.asyncio
async def test_validate_command_access_user_not_found(mock_command):
    """Test validate_command_access with nonexistent user."""
    with patch("app.api.commands.core.get_command_permission") as mock_get_permission, \
         patch("app.api.commands.core.AsyncSessionLocal") as mock_session, \
         patch("app.api.commands.core.get_chat_user_by_platform_id") as mock_get_user:
        # Mock session context manager
        mock_session_instance = MagicMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Set command to require basic permission
        mock_get_permission.return_value = CommandPermission.BASIC
        
        # Mock user not found
        mock_get_user.return_value = None
        
        # Test with nonexistent user
        result = await validate_command_access(mock_command, "DISCORD", "nonexistent")
        
        # Verify
        assert result is False
        mock_get_permission.assert_called_once_with(mock_command.name)
        mock_get_user.assert_called_once_with(mock_session_instance, "nonexistent", ChatService.DISCORD)


@pytest.mark.asyncio
async def test_list_commands_web_user(mock_user):
    """Test list_commands with web user."""
    # Web users should see all commands
    original_commands = AVAILABLE_COMMANDS
    
    # Test the function
    response = await list_commands(current_user=mock_user)
    
    # Verify all commands are returned for web users
    assert response.commands == original_commands


@pytest.mark.asyncio
async def test_list_commands_chat_user(mock_user, mock_chat_user):
    """Test list_commands with chat user."""
    with patch("app.api.commands.core.AsyncSessionLocal") as mock_session, \
         patch("app.api.commands.core.get_chat_user_by_platform_id") as mock_get_user, \
         patch("app.api.commands.core.get_command_permission") as mock_get_permission, \
         patch("app.api.commands.core.has_permission") as mock_has_permission:
        # Mock session context manager
        mock_session_instance = MagicMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Set user type to chat
        mock_user.user_type = UserType.CHAT
        
        # Mock getting the chat user
        mock_get_user.return_value = mock_chat_user
        
        # Mock permission checks
        def permission_side_effect(cmd_name):
            # Return different permissions for different commands
            permissions = {
                "help": CommandPermission.PUBLIC,
                "register": CommandPermission.PUBLIC,
                "status": CommandPermission.BASIC,
                "alerts": CommandPermission.ADMIN
            }
            return permissions.get(cmd_name, CommandPermission.ADMIN)
            
        mock_get_permission.side_effect = permission_side_effect
        
        # Mock has_permission to return True for BASIC and below
        def has_permission_side_effect(role, permission):
            if permission == CommandPermission.PUBLIC:
                return True
            elif permission == CommandPermission.BASIC and role in [ChatUserRole.BASIC, ChatUserRole.ADMIN]:
                return True
            elif permission == CommandPermission.ADMIN and role == ChatUserRole.ADMIN:
                return True
            return False
            
        mock_has_permission.side_effect = has_permission_side_effect
        
        # Test the function with a BASIC role user
        response = await list_commands(current_user=mock_user, platform="DISCORD")
        
        # Verify only public and basic commands are returned
        assert len(response.commands) < len(AVAILABLE_COMMANDS)
        command_names = [cmd.name for cmd in response.commands]
        assert "help" in command_names
        assert "register" in command_names
        assert "status" in command_names
        assert "alerts" not in command_names


@pytest.mark.asyncio
async def test_test_command_valid(mock_user):
    """Test test_command endpoint with valid command."""
    with patch("app.api.commands.core.process_command") as mock_process:
        # Mock command processing
        mock_process.return_value = "Command executed"
        
        # Test data
        request = CommandTestRequest(
            command="!help",
            platform="DISCORD"
        )
        
        # Test the function
        response = await test_command(request, mock_user)
        
        # Verify
        assert response.command == "!help"
        assert response.response == "Command executed"
        assert response.success is True
        mock_process.assert_called_once_with(
            command="!help",
            platform="DISCORD",
            user_id=mock_user.id if mock_user.user_type == UserType.CHAT else None,
            username=mock_user.username,
            user_type=mock_user.user_type.value
        )


@pytest.mark.asyncio
async def test_test_command_empty(mock_user):
    """Test test_command with empty command."""
    # Test data
    request = CommandTestRequest(
        command="",
        platform="DISCORD"
    )
    
    # Test the function raises exception
    with pytest.raises(HTTPException) as exc_info:
        await test_command(request, mock_user)
    
    # Verify exception details
    assert exc_info.value.status_code == 400
    assert "Command cannot be empty" in exc_info.value.detail


@pytest.mark.asyncio
async def test_test_command_unknown(mock_user):
    """Test test_command with unknown command."""
    # Test data
    request = CommandTestRequest(
        command="!unknown",
        platform="DISCORD"
    )
    
    # Test the function
    response = await test_command(request, mock_user)
    
    # Verify
    assert response.command == "!unknown"
    assert "Unknown command: unknown" in response.response
    assert response.success is False


@pytest.mark.asyncio
async def test_test_command_invalid_platform(mock_user, mock_command):
    """Test test_command with command not available on platform."""
    with patch("app.api.commands.core.AVAILABLE_COMMANDS", [mock_command]):
        # Use a platform not supported by the command
        mock_command.platforms = ["SLACK"]
        
        # Test data
        request = CommandTestRequest(
            command="!test",
            platform="DISCORD"
        )
        
        # Test the function
        response = await test_command(request, mock_user)
        
        # Verify
        assert response.command == "!test"
        assert "Command test is not available on discord" in response.response
        assert response.success is False


@pytest.mark.asyncio
async def test_test_command_insufficient_permissions(mock_user, mock_chat_user, mock_command):
    """Test test_command with insufficient permissions."""
    with patch("app.api.commands.core.AVAILABLE_COMMANDS", [mock_command]), \
         patch("app.api.commands.core.AsyncSessionLocal") as mock_session, \
         patch("app.api.commands.core.get_chat_user_by_platform_id") as mock_get_user, \
         patch("app.api.commands.core.get_command_permission") as mock_get_permission, \
         patch("app.api.commands.core.has_permission") as mock_has_permission:
        # Mock session context manager
        mock_session_instance = MagicMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Set user type to chat
        mock_user.user_type = UserType.CHAT
        
        # Make command available on Discord
        mock_command.platforms = ["DISCORD"]
        
        # Mock getting the chat user
        mock_get_user.return_value = mock_chat_user
        
        # Mock permission check - user doesn't have permission
        mock_get_permission.return_value = CommandPermission.ADMIN
        mock_has_permission.return_value = False
        
        # Test data
        request = CommandTestRequest(
            command="!test",
            platform="DISCORD"
        )
        
        # Test the function
        response = await test_command(request, mock_user)
        
        # Verify
        assert response.command == "!test"
        assert "You don't have permission to use this command" in response.response
        assert response.success is False