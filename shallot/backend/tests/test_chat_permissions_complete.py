"""Comprehensive tests for chat permissions service."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.chat_users import ChatUser, ChatUserRole, ChatService
from app.core.permissions import CommandPermission
from app.services.chat_permissions import (
    get_chat_user_role,
    check_command_permission
)
from tests.utils import await_mock, setup_mock_db


@pytest.mark.asyncio
async def test_chat_permissions_mock():
    """Test chat permissions with mocked DB for Python 3.13 compatibility."""
    # Create a mock database session
    mock_db = setup_mock_db()
    
    # Test get_chat_user_role
    # Set up mock db.execute to return a user with ADMIN role
    admin_user = MagicMock(spec=ChatUser)
    admin_user.role = ChatUserRole.ADMIN
    
    async def execute_mock_admin(*args, **kwargs):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = AsyncMock(return_value=admin_user)
        return result_mock
    
    with patch.object(mock_db, 'execute', new=AsyncMock(side_effect=execute_mock_admin)):
        # Test the function
        role = await get_chat_user_role(mock_db, ChatService.DISCORD, "admin123")
        
        # Verify the result
        assert role == ChatUserRole.ADMIN
    
    # Test get_chat_user_role with no user found
    async def execute_mock_no_user(*args, **kwargs):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = AsyncMock(return_value=None)
        return result_mock
    
    with patch.object(mock_db, 'execute', new=AsyncMock(side_effect=execute_mock_no_user)):
        # Test the function
        role = await get_chat_user_role(mock_db, ChatService.DISCORD, "nonexistent")
        
        # Verify the result
        assert role is None
    
    # Test check_command_permission with ADMIN user and ADMIN command
    with patch('app.services.chat_permissions.get_chat_user_role', new=AsyncMock(return_value=ChatUserRole.ADMIN)), \
         patch('app.services.chat_permissions.has_permission', new=AsyncMock(return_value=True)):
        
        # Test the function
        allowed, message = await check_command_permission(
            mock_db, "!admin_command", "discord", "admin123", CommandPermission.ADMIN
        )
        
        # Verify the result
        assert allowed is True
        assert message == ""
    
    # Test check_command_permission with USER role and ADMIN command (permission denied)
    with patch('app.services.chat_permissions.get_chat_user_role', new=AsyncMock(return_value=ChatUserRole.USER)), \
         patch('app.services.chat_permissions.has_permission', new=AsyncMock(return_value=False)):
        
        # Test the function
        allowed, message = await check_command_permission(
            mock_db, "!admin_command", ChatService.DISCORD, "user123", CommandPermission.ADMIN
        )
        
        # Verify the result
        assert allowed is False
        assert "Permission denied" in message
        assert "admin role" in message
        assert "your role: user" in message
    
    # Test check_command_permission with no platform_id (unauthenticated)
    with patch('app.services.chat_permissions.has_permission', new=AsyncMock(return_value=False)):
        
        # Test the function
        allowed, message = await check_command_permission(
            mock_db, "!admin_command", ChatService.DISCORD, None, CommandPermission.ADMIN
        )
        
        # Verify the result
        assert allowed is False
        assert "Permission denied" in message
        assert "admin role" in message
        assert "your role: unauthenticated" in message
    
    # Test check_command_permission using default permission from command
    with patch('app.services.chat_permissions.get_chat_user_role', new=AsyncMock(return_value=ChatUserRole.BASIC)), \
         patch('app.services.chat_permissions.get_command_permission', return_value=CommandPermission.BASIC), \
         patch('app.services.chat_permissions.has_permission', new=AsyncMock(return_value=True)):
        
        # Test the function
        allowed, message = await check_command_permission(
            mock_db, "!basic_command", ChatService.DISCORD, "basic123"  # No override_permission
        )
        
        # Verify the result
        assert allowed is True
        assert message == ""
    
    # Test check_command_permission with exception in get_chat_user_role
    with patch('app.services.chat_permissions.get_chat_user_role', side_effect=Exception("Test error")), \
         pytest.raises(Exception):
        
        await check_command_permission(
            mock_db, "!command", ChatService.DISCORD, "user123", CommandPermission.ADMIN
        )


@pytest.mark.asyncio
async def test_get_chat_user_role(db: AsyncSession):
    """Test getting a chat user's role."""
    # Create a test user
    test_user = ChatUser(
        platform_id="test123",
        username="testuser",
        platform=ChatService.DISCORD,
        role=ChatUserRole.ADMIN
    )
    db.add(test_user)
    await db.commit()
    
    # Get the user's role
    role = await get_chat_user_role(db, ChatService.DISCORD, "test123")
    assert role == ChatUserRole.ADMIN
    
    # Test user not found
    not_found_role = await get_chat_user_role(db, ChatService.DISCORD, "nonexistent")
    assert not_found_role is None


@pytest.mark.asyncio
async def test_check_command_permission_allowed(db: AsyncSession):
    """Test check_command_permission when user has permission."""
    # Create an admin user
    admin_user = ChatUser(
        platform_id="admin123",
        username="adminuser",
        platform=ChatService.DISCORD,
        role=ChatUserRole.ADMIN
    )
    db.add(admin_user)
    await db.commit()
    
    # Check permission for admin command
    allowed, message = await check_command_permission(
        db, "!admin_command", ChatService.DISCORD, "admin123", CommandPermission.ADMIN
    )
    
    # Verify permission granted
    assert allowed is True
    assert message == ""


@pytest.mark.asyncio
async def test_check_command_permission_denied(db: AsyncSession):
    """Test check_command_permission when user doesn't have permission."""
    # Create a regular user
    regular_user = ChatUser(
        platform_id="user123",
        username="regularuser",
        platform=ChatService.DISCORD,
        role=ChatUserRole.USER
    )
    db.add(regular_user)
    await db.commit()
    
    # Check permission for admin command
    allowed, message = await check_command_permission(
        db, "!admin_command", ChatService.DISCORD, "user123", CommandPermission.ADMIN
    )
    
    # Verify permission denied
    assert allowed is False
    assert "Permission denied" in message
    assert "admin role" in message
    assert "your role: user" in message


@pytest.mark.asyncio
async def test_check_command_permission_unauthenticated(db: AsyncSession):
    """Test check_command_permission for unauthenticated user."""
    # Check permission with no platform_id
    allowed, message = await check_command_permission(
        db, "!admin_command", ChatService.DISCORD, None, CommandPermission.ADMIN
    )
    
    # Verify permission denied
    assert allowed is False
    assert "Permission denied" in message
    assert "admin role" in message
    assert "your role: unauthenticated" in message


@pytest.mark.asyncio
async def test_check_command_permission_no_override(db: AsyncSession):
    """Test check_command_permission using default permission from command."""
    # Create a basic user
    basic_user = ChatUser(
        platform_id="basic123",
        username="basicuser",
        platform=ChatService.DISCORD,
        role=ChatUserRole.BASIC
    )
    db.add(basic_user)
    await db.commit()
    
    # Mock get_command_permission to return BASIC permission
    with patch('app.services.chat_permissions.get_command_permission', return_value=CommandPermission.BASIC):
        # Check permission without override
        allowed, message = await check_command_permission(
            db, "!basic_command", ChatService.DISCORD, "basic123"  # No override_permission
        )
        
        # Verify permission granted
        assert allowed is True
        assert message == ""


@pytest.mark.asyncio
async def test_check_command_permission_basic_to_admin(db: AsyncSession):
    """Test check_command_permission with BASIC user trying to use ADMIN command."""
    # Create a basic user
    basic_user = ChatUser(
        platform_id="basic789",  # Changed ID to avoid integrity error
        username="basicuser",
        platform=ChatService.DISCORD,
        role=ChatUserRole.BASIC
    )
    db.add(basic_user)
    await db.commit()
    
    # Check permission for admin command
    allowed, message = await check_command_permission(
        db, "!admin_command", ChatService.DISCORD, "basic789", CommandPermission.ADMIN
    )
    
    # Verify permission denied
    assert allowed is False
    assert "Permission denied" in message
    assert "admin role" in message
    assert "your role: basic" in message


@pytest.mark.asyncio
async def test_check_command_permission_user_to_basic(db: AsyncSession):
    """Test check_command_permission with USER trying to use BASIC command."""
    # Create a regular user
    regular_user = ChatUser(
        platform_id="user456",
        username="regularuser",
        platform=ChatService.DISCORD,
        role=ChatUserRole.USER
    )
    db.add(regular_user)
    await db.commit()
    
    # Check permission for basic command
    allowed, message = await check_command_permission(
        db, "!basic_command", ChatService.DISCORD, "user456", CommandPermission.BASIC
    )
    
    # Verify permission denied
    assert allowed is False
    assert "Permission denied" in message
    assert "basic role" in message
    assert "your role: user" in message


@pytest.mark.asyncio
async def test_check_command_permission_exception_handling(db: AsyncSession):
    """Test check_command_permission with exception in permission check."""
    # Mock an exception in get_chat_user_role
    with patch('app.services.chat_permissions.get_chat_user_role', side_effect=Exception("Test error")), \
         pytest.raises(Exception):
        await check_command_permission(
            db, "!command", ChatService.DISCORD, "user123", CommandPermission.ADMIN
        )


@pytest.mark.asyncio
async def test_check_command_permission_has_permission_call():
    """Test check_command_permission correctly calls has_permission."""
    # Create mock database
    mock_db = setup_mock_db()
    
    # Mock get_chat_user_role and has_permission
    with patch('app.services.chat_permissions.get_chat_user_role', new=AsyncMock(return_value=ChatUserRole.BASIC)) as mock_get_role, \
         patch('app.services.chat_permissions.has_permission', new=AsyncMock(return_value=True)) as mock_has_permission:
        
        # Call check_command_permission
        allowed, _ = await check_command_permission(
            mock_db, "!command", ChatService.DISCORD, "user123", CommandPermission.BASIC
        )
        
        # Verify has_permission was called with correct arguments
        assert allowed is True
        mock_get_role.assert_called_once_with(mock_db, ChatService.DISCORD, "user123")
        mock_has_permission.assert_called_once_with(ChatUserRole.BASIC, CommandPermission.BASIC)