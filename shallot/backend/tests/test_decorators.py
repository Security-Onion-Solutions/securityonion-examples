"""Tests for decorators module."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional

from app.core.decorators import requires_permission
from app.core.permissions import CommandPermission
from app.models.chat_users import ChatUserRole, ChatUser, ChatService


@pytest.mark.asyncio
async def test_requires_permission_decorator():
    """Test the requires_permission decorator with different user roles."""
    
    # Create a simple async function to decorate
    @requires_permission()
    async def test_command(command: str, platform: str = None, user_id: str = None, username: str = None) -> str:
        return "Success"
    
    # Mock the database session and chat_user service
    with patch('app.core.decorators.AsyncSessionLocal') as mock_db_session:
        with patch('app.core.decorators.get_chat_user_by_platform_id') as mock_get_user:
            # Create a context manager mock
            db_instance = AsyncMock()
            mock_db_session.return_value.__aenter__.return_value = db_instance
            
            # Test for admin user with admin command
            admin_user = ChatUser(
                platform_id="admin123",
                username="admin",
                platform=ChatService.DISCORD,
                role=ChatUserRole.ADMIN
            )
            mock_get_user.return_value = admin_user
            
            result = await test_command("!status check", "discord", "admin123")
            assert result == "Success", "Admin user should have access to admin commands"
            
            # Test for basic user with admin command (should deny)
            basic_user = ChatUser(
                platform_id="basic123",
                username="basic",
                platform=ChatService.DISCORD,
                role=ChatUserRole.BASIC
            )
            mock_get_user.return_value = basic_user
            
            result = await test_command("!status check", "discord", "basic123")
            assert "Permission denied" in result, "Basic user should not have access to admin commands"
            
            # Test basic user with public command (help)
            result = await test_command("!help", "discord", "basic123")
            assert result == "Success", "Basic user should have access to public commands"
            
            # Test user not found
            mock_get_user.return_value = None
            
            result = await test_command("!status check", "discord", "unknown123")
            assert "Permission denied" in result, "Unknown user should not have access to admin commands"
            
            # Test public command for unknown user
            result = await test_command("!help", "discord", "unknown123")
            assert result == "Success", "Unknown user should have access to public commands"


@pytest.mark.asyncio
async def test_explicit_permission_decorator():
    """Test the requires_permission decorator with explicit permission settings."""
    
    # Create decorated functions with explicit permission levels
    @requires_permission(permission=CommandPermission.PUBLIC)
    async def public_command(command: str, platform: str = None, user_id: str = None, username: str = None) -> str:
        return "Public command success"
    
    @requires_permission(permission=CommandPermission.BASIC)
    async def basic_command(command: str, platform: str = None, user_id: str = None, username: str = None) -> str:
        return "Basic command success"
    
    @requires_permission(permission=CommandPermission.ADMIN)
    async def admin_command(command: str, platform: str = None, user_id: str = None, username: str = None) -> str:
        return "Admin command success"
    
    # Mock the database session and chat_user service
    with patch('app.core.decorators.AsyncSessionLocal') as mock_db_session:
        with patch('app.core.decorators.get_chat_user_by_platform_id') as mock_get_user:
            # Create a context manager mock
            db_instance = AsyncMock()
            mock_db_session.return_value.__aenter__.return_value = db_instance
            
            # Test different user roles with explicit permission commands
            
            # Admin user
            admin_user = ChatUser(
                platform_id="admin123",
                username="admin", 
                platform=ChatService.DISCORD,
                role=ChatUserRole.ADMIN
            )
            mock_get_user.return_value = admin_user
            
            # Admin should have access to all commands
            assert await public_command("!test", "discord", "admin123") == "Public command success"
            assert await basic_command("!test", "discord", "admin123") == "Basic command success"
            assert await admin_command("!test", "discord", "admin123") == "Admin command success"
            
            # Basic user
            basic_user = ChatUser(
                platform_id="basic123",
                username="basic",
                platform=ChatService.DISCORD,
                role=ChatUserRole.BASIC
            )
            mock_get_user.return_value = basic_user
            
            # Basic should have access to public and basic commands
            assert await public_command("!test", "discord", "basic123") == "Public command success"
            assert await basic_command("!test", "discord", "basic123") == "Basic command success"
            assert "Permission denied" in await admin_command("!test", "discord", "basic123")
            
            # Regular user
            regular_user = ChatUser(
                platform_id="user123",
                username="user",
                platform=ChatService.DISCORD,
                role=ChatUserRole.USER
            )
            mock_get_user.return_value = regular_user
            
            # Regular user should only have access to public commands
            assert await public_command("!test", "discord", "user123") == "Public command success"
            assert "Permission denied" in await basic_command("!test", "discord", "user123")
            assert "Permission denied" in await admin_command("!test", "discord", "user123")


@pytest.mark.asyncio
async def test_web_user_bypass():
    """Test that web users bypass permission checks."""
    
    @requires_permission(permission=CommandPermission.ADMIN)
    async def admin_command(command: str, platform: str = None, user_id: str = None, 
                           username: str = None, user_type: str = None) -> str:
        return "Command executed"
    
    # Web users should bypass permission checks
    result = await admin_command("!admin", "web", "web_user", user_type="web")
    assert result == "Command executed", "Web user should bypass permission checks"


@pytest.mark.asyncio
async def test_command_parsing():
    """Test command name parsing from command string."""
    
    # Mock function that will return the parsed command name
    @requires_permission()
    async def echo_command(command: str, platform: str = None, user_id: str = None, username: str = None) -> str:
        # We'll replace this implementation in the mock below
        return command
    
    with patch('app.core.decorators.AsyncSessionLocal') as mock_db_session:
        with patch('app.core.decorators.get_chat_user_by_platform_id') as mock_get_user:
            with patch('app.core.decorators.get_command_permission') as mock_get_permission:
                # Setup mocks
                db_instance = AsyncMock()
                mock_db_session.return_value.__aenter__.return_value = db_instance
                
                # Return admin user with ADMIN role to bypass permission checks
                admin_user = ChatUser(
                    platform_id="admin123",
                    username="admin",
                    platform=ChatService.DISCORD,
                    role=ChatUserRole.ADMIN
                )
                mock_get_user.return_value = admin_user
                
                # We'll capture what command name was parsed
                captured_commands = []
                
                def track_command(command_name):
                    captured_commands.append(command_name)
                    return CommandPermission.PUBLIC  # Return public to always allow the command
                
                mock_get_permission.side_effect = track_command
                
                # Test different command formats
                await echo_command("!help", "discord", "admin123")
                assert captured_commands[-1] == "help"
                
                await echo_command("!status check all", "discord", "admin123")
                assert captured_commands[-1] == "status"
                
                await echo_command("help me", "discord", "admin123")
                assert captured_commands[-1] == "help"
                
                # Test empty command (should default to help)
                await echo_command("", "discord", "admin123")
                assert captured_commands[-1] == "help"


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in decorator."""
    
    @requires_permission()
    async def error_command(command: str, platform: str = None, user_id: str = None, username: str = None) -> str:
        raise ValueError("Test error")
    
    with patch('app.core.decorators.AsyncSessionLocal') as mock_db_session:
        with patch('app.core.decorators.get_chat_user_by_platform_id') as mock_get_user:
            # Setup mocks
            db_instance = AsyncMock()
            mock_db_session.return_value.__aenter__.return_value = db_instance
            
            # Return admin user with ADMIN role to bypass permission checks
            admin_user = ChatUser(
                platform_id="admin123",
                username="admin",
                platform=ChatService.DISCORD,
                role=ChatUserRole.ADMIN
            )
            mock_get_user.return_value = admin_user
            
            # The decorator should let the error propagate
            with pytest.raises(ValueError):
                await error_command("!help", "discord", "admin123")