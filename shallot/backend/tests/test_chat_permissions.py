"""Tests for chat permissions service."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.chat_users import ChatUser, ChatUserRole
from app.core.permissions import CommandPermission
from app.services.chat_permissions import (
    get_chat_user_role,
    check_command_permission
)
from tests.utils import await_mock


@pytest.mark.asyncio
async 

def await_mock(return_value):
    # Helper function to make mock return values awaitable in Python 3.13
    async def _awaitable():
        return return_value
    return _awaitable()

def test_get_chat_user_role(db: AsyncSession):
    """Test getting a chat user's role."""
    # Create a test user
    test_user = ChatUser(
        platform_id="test123",
        username="testuser",
        platform="discord",
        role=ChatUserRole.ADMIN
    )
    db.add(test_user)
    await db.commit()
    
    # Get the user's role
    role = await get_chat_user_role(db, "discord", "test123")
    assert role == ChatUserRole.ADMIN
    
    # Test user not found
    not_found_role = await get_chat_user_role(db, "discord", "nonexistent")
    assert not_found_role is None


@pytest.mark.asyncio
async def test_get_chat_user_role_python_313(db: AsyncSession):
    """Test get_chat_user_role with Python 3.13 coroutine handling."""
    # Mock database query result
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = await_mock(MagicMock(role=ChatUserRole.BASIC))

    mock_scalar.scalar_one_or_none.return_value = await_mock(mock_scalar.scalar_one_or_none.return_value)

    mock_scalar.scalar_one_or_none.return_value = await_mock(mock_scalar.scalar_one_or_none.return_value)  # Make awaitable for Python 3.13


    mock_scalar.scalar_one_or_none.return_value = await_mock(mock_scalar.scalar_one_or_none.return_value)
    
    # Mock db.execute
    with patch.object(db, 'execute', return_value=await_mock(mock_scalar)):
        role = await get_chat_user_role(db, "discord", "test123")
        assert role == ChatUserRole.BASIC


@pytest.mark.asyncio
async def test_check_command_permission_allowed(db: AsyncSession):
    """Test check_command_permission when user has permission."""
    # Create an admin user
    admin_user = ChatUser(
        platform_id="admin123",
        username="adminuser",
        platform="discord",
        role=ChatUserRole.ADMIN
    )
    db.add(admin_user)
    await db.commit()
    
    # Check permission for admin command
    allowed, message = await check_command_permission(
        db, "!admin_command", "discord", "admin123", CommandPermission.ADMIN
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
        platform="discord",
        role=ChatUserRole.USER
    )
    db.add(regular_user)
    await db.commit()
    
    # Check permission for admin command
    allowed, message = await check_command_permission(
        db, "!admin_command", "discord", "user123", CommandPermission.ADMIN
    )
    
    # Verify permission denied
    assert allowed is False
    assert "Permission denied" in message
    assert "admin role" in message
    assert "your role: USER" in message


@pytest.mark.asyncio
async def test_check_command_permission_unauthenticated(db: AsyncSession):
    """Test check_command_permission for unauthenticated user."""
    # Check permission with no platform_id
    allowed, message = await check_command_permission(
        db, "!admin_command", "discord", None, CommandPermission.ADMIN
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
        platform="discord",
        role=ChatUserRole.BASIC
    )
    db.add(basic_user)
    await db.commit()
    
    # Mock get_command_permission to return BASIC permission
    with patch('app.services.chat_permissions.get_command_permission', return_value=CommandPermission.BASIC):
        # Check permission without override
        allowed, message = await check_command_permission(
            db, "!basic_command", "discord", "basic123"  # No override_permission
        )
        
        # Verify permission granted
        assert allowed is True
        assert message == ""


@pytest.mark.asyncio
async def test_check_command_permission_exception_handling(db: AsyncSession):
    """Test check_command_permission with exception in permission check."""
    # Mock an exception in get_chat_user_role
    with patch('app.services.chat_permissions.get_chat_user_role', side_effect=Exception("Test error")), \
         pytest.raises(Exception):
        await check_command_permission(
            db, "!command", "discord", "user123", CommandPermission.ADMIN
        )


@pytest.mark.asyncio
async def test_check_command_permission_has_permission_call(db: AsyncSession):
    """Test check_command_permission correctly calls has_permission."""
    # Mock get_chat_user_role and has_permission
    with patch('app.services.chat_permissions.get_chat_user_role', return_value=await_mock(ChatUserRole.BASIC)) as mock_get_role, \
         patch('app.services.chat_permissions.has_permission', return_value=await_mock(True)) as mock_has_permission:
        
        # Call check_command_permission
        allowed, _ = await check_command_permission(
            db, "!command", "discord", "user123", CommandPermission.BASIC
        )
        
        # Verify has_permission was called with correct arguments
        assert allowed is True
        mock_get_role.assert_called_once_with(db, "discord", "user123")
        mock_has_permission.assert_called_once_with(ChatUserRole.BASIC, CommandPermission.BASIC)