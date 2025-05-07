"""Comprehensive tests for the chat_users service."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from unittest.mock import patch, MagicMock, AsyncMock

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
from tests.utils import await_mock, setup_mock_db, create_mock_db_session


@pytest.mark.asyncio
async def test_chat_users_service_mock():
    """Test chat users service with mocked DB for Python 3.13 compatibility."""
    # Create a mock database session
    mock_db = setup_mock_db()
    
    # Test get_chat_user_by_platform_id
    mock_user = MagicMock(spec=ChatUser)
    mock_user.platform_id = "test123"
    mock_user.username = "testuser" 
    mock_user.platform = ChatService.DISCORD
    mock_user.role = ChatUserRole.ADMIN
    
    # Define a custom side effect function for execute
    async def execute_mock_get_user(*args, **kwargs):
        # Create a result mock that will be returned by execute
        result_mock = MagicMock()
        # Configure the scalar_one_or_none method to return our mock_user
        result_mock.scalar_one_or_none = AsyncMock(return_value=mock_user)
        return result_mock
    
    # Patch the execute method
    with patch.object(mock_db, 'execute', new=AsyncMock(side_effect=execute_mock_get_user)):
        # Test the function
        user = await get_chat_user_by_platform_id(mock_db, "test123", ChatService.DISCORD)
        
        # Verify the result
        assert user is mock_user
        assert user.username == "testuser"
        assert user.platform == ChatService.DISCORD
    
    # Test create_chat_user
    mock_created_user = MagicMock(spec=ChatUser)
    mock_created_user.platform_id = "new123"
    mock_created_user.username = "newuser"
    mock_created_user.platform = ChatService.MATRIX
    mock_created_user.role = ChatUserRole.BASIC
    mock_created_user.display_name = "New User"
    
    # Patch db.add, commit, and refresh
    with patch.object(mock_db, 'add') as mock_add, \
         patch.object(mock_db, 'commit', new=AsyncMock()) as mock_commit, \
         patch.object(mock_db, 'refresh', new=AsyncMock()) as mock_refresh, \
         patch('app.services.chat_users.ChatUser', return_value=mock_created_user):
         
        # Test creating a user
        new_user = await create_chat_user(
            mock_db,
            platform_id="new123",
            username="newuser",
            platform=ChatService.MATRIX,
            role=ChatUserRole.BASIC,
            display_name="New User"
        )
        
        # Verify method calls and result
        mock_add.assert_called_once()
        mock_commit.assert_called_once()
        mock_refresh.assert_called_once_with(mock_created_user)
        assert new_user is mock_created_user
        assert new_user.platform_id == "new123"
        assert new_user.username == "newuser"
    
    # Test is_command_allowed with non-existent user
    async def execute_mock_no_user(*args, **kwargs):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = AsyncMock(return_value=None)
        return result_mock
    
    with patch.object(mock_db, 'execute', new=AsyncMock(side_effect=execute_mock_no_user)):
        # Test permissions for non-existent user
        assert await is_command_allowed(mock_db, "nonexistent", "DISCORD", "!help") is True
        assert await is_command_allowed(mock_db, "nonexistent", "DISCORD", "!register") is True
        assert await is_command_allowed(mock_db, "nonexistent", "DISCORD", "!alerts") is False
    
    # Test is_command_allowed with regular user
    mock_regular_user = MagicMock(spec=ChatUser)
    mock_regular_user.role = ChatUserRole.USER
    
    async def execute_mock_regular_user(*args, **kwargs):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = AsyncMock(return_value=mock_regular_user)
        return result_mock
    
    with patch.object(mock_db, 'execute', new=AsyncMock(side_effect=execute_mock_regular_user)):
        # Test permissions for regular user
        assert await is_command_allowed(mock_db, "user123", "DISCORD", "!help") is True
        assert await is_command_allowed(mock_db, "user123", "DISCORD", "!status") is True
        assert await is_command_allowed(mock_db, "user123", "DISCORD", "!alerts") is False
    
    # Test is_command_allowed with basic user
    mock_basic_user = MagicMock(spec=ChatUser)
    mock_basic_user.role = ChatUserRole.BASIC
    
    async def execute_mock_basic_user(*args, **kwargs):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = AsyncMock(return_value=mock_basic_user)
        return result_mock
    
    with patch.object(mock_db, 'execute', new=AsyncMock(side_effect=execute_mock_basic_user)):
        # Test permissions for basic user
        assert await is_command_allowed(mock_db, "basic123", "DISCORD", "!help") is True
        assert await is_command_allowed(mock_db, "basic123", "DISCORD", "!status") is True
        assert await is_command_allowed(mock_db, "basic123", "DISCORD", "!alerts") is True
        assert await is_command_allowed(mock_db, "basic123", "DISCORD", "!custom") is False
    
    # Test is_command_allowed with admin user
    mock_admin_user = MagicMock(spec=ChatUser)
    mock_admin_user.role = ChatUserRole.ADMIN
    
    async def execute_mock_admin_user(*args, **kwargs):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = AsyncMock(return_value=mock_admin_user)
        return result_mock
    
    with patch.object(mock_db, 'execute', new=AsyncMock(side_effect=execute_mock_admin_user)):
        # Test permissions for admin user
        assert await is_command_allowed(mock_db, "admin123", "DISCORD", "!alerts") is True
        assert await is_command_allowed(mock_db, "admin123", "DISCORD", "!custom") is True
    
    # Test get_chat_user_by_id
    mock_user_by_id = MagicMock(spec=ChatUser)
    mock_user_by_id.id = 1
    mock_user_by_id.username = "byiduser"
    mock_user_by_id.platform_id = "byid123"
    
    async def execute_mock_get_by_id(*args, **kwargs):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = AsyncMock(return_value=mock_user_by_id)
        return result_mock
    
    with patch.object(mock_db, 'execute', new=AsyncMock(side_effect=execute_mock_get_by_id)):
        # Test getting a user by ID
        user = await get_chat_user_by_id(mock_db, 1)
        assert user is mock_user_by_id
        assert user.username == "byiduser"
        assert user.platform_id == "byid123"
    
    # Test get_all_chat_users
    mock_users = [MagicMock(spec=ChatUser) for _ in range(3)]
    for i, user in enumerate(mock_users):
        user.id = i + 1
        user.username = f"user{i}"
    
    async def execute_mock_get_all(*args, **kwargs):
        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all = MagicMock(return_value=mock_users)
        result_mock.scalars = AsyncMock(return_value=scalars_mock)
        return result_mock
    
    with patch.object(mock_db, 'execute', new=AsyncMock(side_effect=execute_mock_get_all)):
        # Test getting all users
        users = await get_all_chat_users(mock_db)
        assert users == mock_users
        assert len(users) == 3
    
    # Test update_chat_user_role
    mock_update_user = MagicMock(spec=ChatUser)
    mock_update_user.id = 1
    mock_update_user.username = "updateuser"
    mock_update_user.role = ChatUserRole.USER
    
    async def execute_mock_get_for_update(*args, **kwargs):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = AsyncMock(return_value=mock_update_user)
        return result_mock
    
    with patch.object(mock_db, 'execute', new=AsyncMock(side_effect=execute_mock_get_for_update)), \
         patch.object(mock_db, 'commit', new=AsyncMock()) as mock_commit, \
         patch.object(mock_db, 'refresh', new=AsyncMock()) as mock_refresh:
        # Test updating a user's role
        updated_user = await update_chat_user_role(mock_db, 1, ChatUserRole.ADMIN)
        
        # Verify the role was updated
        assert updated_user is mock_update_user
        assert updated_user.role == ChatUserRole.ADMIN
        
        # Verify commit and refresh were called
        mock_commit.assert_called_once()
        mock_refresh.assert_called_once_with(mock_update_user)
    
    # Test update_chat_user_role with non-existent user
    async def execute_mock_no_user_for_update(*args, **kwargs):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = AsyncMock(return_value=None)
        return result_mock
    
    with patch.object(mock_db, 'execute', new=AsyncMock(side_effect=execute_mock_no_user_for_update)):
        # Test updating a non-existent user
        updated_user = await update_chat_user_role(mock_db, 999, ChatUserRole.ADMIN)
        assert updated_user is None
    
    # Test delete_chat_user
    mock_delete_user = MagicMock(spec=ChatUser)
    mock_delete_user.id = 1
    
    async def execute_mock_get_for_delete(*args, **kwargs):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = AsyncMock(return_value=mock_delete_user)
        return result_mock
    
    with patch.object(mock_db, 'execute', new=AsyncMock(side_effect=execute_mock_get_for_delete)), \
         patch.object(mock_db, 'delete', new=AsyncMock()) as mock_delete, \
         patch.object(mock_db, 'commit', new=AsyncMock()) as mock_commit:
        # Test deleting a user
        result = await delete_chat_user(mock_db, 1)
        
        # Verify the result
        assert result is True
        
        # Verify delete and commit were called
        mock_delete.assert_called_once_with(mock_delete_user)
        mock_commit.assert_called_once()
    
    # Test delete_chat_user with non-existent user
    async def execute_mock_no_user_for_delete(*args, **kwargs):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = AsyncMock(return_value=None)
        return result_mock
    
    with patch.object(mock_db, 'execute', new=AsyncMock(side_effect=execute_mock_no_user_for_delete)):
        # Test deleting a non-existent user
        result = await delete_chat_user(mock_db, 999)
        assert result is False


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
    # The commit will happen automatically through the fixture
    await db.flush()
    
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
async def test_is_command_allowed_nonexistent_user(db: AsyncSession):
    """Test command permission for non-existent users."""
    # Test non-existent user permissions
    assert await is_command_allowed(db, "nonexistent", "DISCORD", "!help") is True
    assert await is_command_allowed(db, "nonexistent", "DISCORD", "!register") is True
    assert await is_command_allowed(db, "nonexistent", "DISCORD", "!alerts") is False


@pytest.mark.asyncio
async def test_is_command_allowed_user_role(db: AsyncSession):
    """Test command permission for USER role."""
    # Create user with USER role
    await create_chat_user(
        db, "user123", "regularuser", ChatService.DISCORD, ChatUserRole.USER
    )
    
    # Test USER role permissions
    assert await is_command_allowed(db, "user123", "DISCORD", "!help") is True
    assert await is_command_allowed(db, "user123", "DISCORD", "!status") is True
    assert await is_command_allowed(db, "user123", "DISCORD", "!alerts") is False


@pytest.mark.asyncio
async def test_is_command_allowed_basic_role(db: AsyncSession):
    """Test command permission for BASIC role."""
    # Create user with BASIC role
    await create_chat_user(
        db, "basic123", "basicuser", ChatService.DISCORD, ChatUserRole.BASIC
    )
    
    # Test BASIC role permissions
    assert await is_command_allowed(db, "basic123", "DISCORD", "!help") is True
    assert await is_command_allowed(db, "basic123", "DISCORD", "!status") is True
    assert await is_command_allowed(db, "basic123", "DISCORD", "!alerts") is True
    assert await is_command_allowed(db, "basic123", "DISCORD", "!custom") is False


@pytest.mark.asyncio
async def test_is_command_allowed_admin_role(db: AsyncSession):
    """Test command permission for ADMIN role."""
    # Create user with ADMIN role
    await create_chat_user(
        db, "admin123", "adminuser", ChatService.DISCORD, ChatUserRole.ADMIN
    )
    
    # Test ADMIN role permissions
    assert await is_command_allowed(db, "admin123", "DISCORD", "!alerts") is True
    assert await is_command_allowed(db, "admin123", "DISCORD", "!custom") is True


@pytest.mark.asyncio
async def test_get_chat_user_by_id_complete(db: AsyncSession):
    """Test getting a chat user by ID."""
    # Create a test user
    test_user = ChatUser(
        platform_id="byid123_complete",
        username="byiduser_complete",
        platform=ChatService.DISCORD,
        role=ChatUserRole.ADMIN
    )
    db.add(test_user)
    await db.flush()  # Flush to generate ID without committing
    
    # Get the user ID directly from the inserted user
    user_id = test_user.id
    
    # Test getting by ID
    found_user = await get_chat_user_by_id(db, user_id)
    assert found_user is not None
    assert found_user.username == "byiduser_complete"
    assert found_user.platform_id == "byid123_complete"
    
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
    await db.refresh(test_user)  # To get the ID
    
    # Get the user ID directly from the inserted user
    user_id = test_user.id
    
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
    await db.refresh(test_user)  # To get the ID
    
    # Get the user ID directly from the inserted user
    user_id = test_user.id
    
    # Delete the user
    delete_result = await delete_chat_user(db, user_id)
    assert delete_result is True
    
    # Verify user is deleted
    deleted_user = await get_chat_user_by_id(db, user_id)
    assert deleted_user is None
    
    # Test deleting non-existent user
    nonexistent_delete = await delete_chat_user(db, 9999)
    assert nonexistent_delete is False