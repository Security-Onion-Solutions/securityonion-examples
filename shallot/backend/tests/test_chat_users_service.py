"""Tests for chat users service."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from unittest.mock import patch, MagicMock
from app.models.chat_users import ChatUser, ChatUserRole, ChatService
from app.services.chat_users import (
    get_chat_user_by_platform_id,
    create_chat_user,
    is_command_allowed,
    get_chat_user_by_id,
    get_all_chat_users,
    update_chat_user_role,
    delete_chat_user
)
from tests.utils import await_mock


@pytest.mark.asyncio
async def test_get_chat_user_by_platform_id(db: AsyncSession):
    """Test getting a chat user by platform ID."""
    # Create a test user
    test_user = ChatUser(
        platform_id="test123",
        username="testuser",
        platform=ChatService.DISCORD,
        role=ChatUserRole.ADMIN
    )
    db.add(test_user)
    await db.commit()
    
    # Test getting the user
    found_user = await get_chat_user_by_platform_id(db, "test123", ChatService.DISCORD)
    assert found_user is not None
    assert found_user.username == "testuser"
    assert found_user.platform == ChatService.DISCORD
    
    # Test with platform as string
    found_user_string = await get_chat_user_by_platform_id(db, "test123", "DISCORD")
    assert found_user_string is not None
    assert found_user_string.username == "testuser"
    
    # Test user not found
    not_found_user = await get_chat_user_by_platform_id(db, "nonexistent", ChatService.DISCORD)
    assert not_found_user is None


@pytest.mark.asyncio
async def test_create_chat_user(db: AsyncSession):
    """Test creating a chat user."""
    # Create a new user
    new_user = await create_chat_user(
        db,
        platform_id="new123",
        username="newuser",
        platform=ChatService.MATRIX,
        role=ChatUserRole.BASIC,
        display_name="New User"
    )
    
    # Verify user was created
    assert new_user.platform_id == "new123"
    assert new_user.username == "newuser"
    assert new_user.platform == ChatService.MATRIX
    assert new_user.role == ChatUserRole.BASIC
    assert new_user.display_name == "New User"
    
    # Verify user can be retrieved from DB
    stored_user = await get_chat_user_by_platform_id(db, "new123", ChatService.MATRIX)
    assert stored_user is not None
    assert stored_user.username == "newuser"
    
    # Test creating with defaults
    default_user = await create_chat_user(
        db,
        platform_id="default123",
        username="defaultuser",
        platform=ChatService.SLACK
    )
    assert default_user.role == ChatUserRole.USER
    assert default_user.display_name is None


@pytest.mark.asyncio
async def test_is_command_allowed(db: AsyncSession):
    """Test command permission checking."""
    # Create users with different roles
    admin_user = await create_chat_user(
        db, "admin123", "adminuser", ChatService.DISCORD, ChatUserRole.ADMIN
    )
    basic_user = await create_chat_user(
        db, "basic123", "basicuser", ChatService.DISCORD, ChatUserRole.BASIC
    )
    regular_user = await create_chat_user(
        db, "user123", "regularuser", ChatService.DISCORD, ChatUserRole.USER
    )
    
    # Test admin permissions
    assert await is_command_allowed(db, "admin123", "DISCORD", "!alerts") is True
    assert await is_command_allowed(db, "admin123", "DISCORD", "!custom") is True
    
    # Test basic user permissions
    assert await is_command_allowed(db, "basic123", "DISCORD", "!help") is True
    assert await is_command_allowed(db, "basic123", "DISCORD", "!status") is True
    assert await is_command_allowed(db, "basic123", "DISCORD", "!alerts") is True
    assert await is_command_allowed(db, "basic123", "DISCORD", "!custom") is False
    
    # Test regular user permissions
    assert await is_command_allowed(db, "user123", "DISCORD", "!help") is True
    assert await is_command_allowed(db, "user123", "DISCORD", "!status") is True
    assert await is_command_allowed(db, "user123", "DISCORD", "!alerts") is False
    
    # Test non-existent user permissions
    assert await is_command_allowed(db, "nonexistent", "DISCORD", "!help") is True
    assert await is_command_allowed(db, "nonexistent", "DISCORD", "!register") is True
    assert await is_command_allowed(db, "nonexistent", "DISCORD", "!alerts") is False


@pytest.mark.asyncio
async def test_get_chat_user_by_id(db: AsyncSession):
    """Test getting a chat user by ID."""
    # Create a test user
    test_user = ChatUser(
        platform_id="byid123",
        username="byiduser",
        platform=ChatService.DISCORD,
        role=ChatUserRole.ADMIN
    )
    db.add(test_user)
    await db.commit()
    
    # Get the user's ID
    result = await db.execute(
        text("SELECT id FROM chat_users WHERE platform_id = 'byid123'")
    )
    user_id = result.scalar_one()
    
    # Test getting by ID
    found_user = await get_chat_user_by_id(db, user_id)
    assert found_user is not None
    assert found_user.username == "byiduser"
    assert found_user.platform_id == "byid123"
    
    # Test with non-existent ID
    not_found = await get_chat_user_by_id(db, 9999)
    assert not_found is None


@pytest.mark.asyncio
async def test_get_all_chat_users(db: AsyncSession):
    """Test getting all chat users with pagination."""
    # Create multiple test users
    for i in range(5):
        db.add(ChatUser(
            platform_id=f"all{i}",
            username=f"alluser{i}",
            platform=ChatService.DISCORD,
            role=ChatUserRole.USER
        ))
    await db.commit()
    
    # Get all users
    all_users = await get_all_chat_users(db)
    assert len(all_users) >= 5  # Could be more from other tests
    
    # Test pagination
    first_page = await get_all_chat_users(db, skip=0, limit=2)
    assert len(first_page) == 2
    
    second_page = await get_all_chat_users(db, skip=2, limit=2)
    assert len(second_page) == 2
    
    # Ensure different pages have different users
    assert first_page[0].id != second_page[0].id


@pytest.mark.asyncio
async def test_update_chat_user_role(db: AsyncSession):
    """Test updating a chat user's role."""
    # Create a test user
    test_user = ChatUser(
        platform_id="update123",
        username="updateuser",
        platform=ChatService.DISCORD,
        role=ChatUserRole.USER
    )
    db.add(test_user)
    await db.commit()
    
    # Get the user's ID
    result = await db.execute(
        text("SELECT id FROM chat_users WHERE platform_id = 'update123'")
    )
    user_id = result.scalar_one()
    
    # Update the role
    updated_user = await update_chat_user_role(db, user_id, ChatUserRole.ADMIN)
    assert updated_user is not None
    assert updated_user.role == ChatUserRole.ADMIN
    
    # Verify role is updated in the database
    refreshed_user = await get_chat_user_by_id(db, user_id)
    assert refreshed_user.role == ChatUserRole.ADMIN
    
    # Test updating non-existent user
    nonexistent_update = await update_chat_user_role(db, 9999, ChatUserRole.ADMIN)
    assert nonexistent_update is None


@pytest.mark.asyncio
async def test_delete_chat_user(db: AsyncSession):
    """Test deleting a chat user."""
    # Create a test user
    test_user = ChatUser(
        platform_id="delete123",
        username="deleteuser",
        platform=ChatService.DISCORD,
        role=ChatUserRole.USER
    )
    db.add(test_user)
    await db.commit()
    
    # Get the user's ID
    result = await db.execute(
        text("SELECT id FROM chat_users WHERE platform_id = 'delete123'")
    )
    user_id = result.scalar_one()
    
    # Delete the user
    delete_result = await delete_chat_user(db, user_id)
    assert delete_result is True
    
    # Verify user is deleted
    deleted_user = await get_chat_user_by_id(db, user_id)
    assert deleted_user is None
    
    # Test deleting non-existent user
    nonexistent_delete = await delete_chat_user(db, 9999)
    assert nonexistent_delete is False