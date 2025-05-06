"""Tests for users API and services."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.api.users import (
    create_new_user,
    read_users,
    read_user,
    update_user_endpoint
)
from app.services.users import (
    get_user_count,
    get_user_by_username,
    get_user_by_id,
    authenticate_user,
    create_user,
    update_user
)
from app.models.users import User, UserType
from app.schemas.users import UserCreate, UserUpdate

client = TestClient(app)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_user():
    """Create a mock regular user."""
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    user.is_active = True
    user.is_superuser = False
    user.user_type = UserType.WEB
    user.hashed_password = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # "password"
    return user


@pytest.fixture
def mock_superuser():
    """Create a mock superuser."""
    user = MagicMock(spec=User)
    user.id = 2
    user.username = "admin"
    user.email = "admin@example.com"
    user.is_active = True
    user.is_superuser = True
    user.user_type = UserType.WEB
    user.hashed_password = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # "password"
    return user


# Service tests

@pytest.mark.asyncio
async def test_get_user_count(mock_db):
    """Test get_user_count service function."""
    # Mock DB query result
    mock_result = AsyncMock()
    mock_result.scalar_one.return_value = 5
    mock_db.execute.return_value = mock_result
    
    # Test function
    count = await get_user_count(mock_db)
    
    # Verify
    assert count == 5
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_by_username(mock_db, mock_user):
    """Test get_user_by_username service function."""
    # Mock DB query result
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute.return_value = mock_result
    
    # Test function
    user = await get_user_by_username(mock_db, "testuser")
    
    # Verify
    assert user == mock_user
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_by_username_not_found(mock_db):
    """Test get_user_by_username with nonexistent user."""
    # Mock DB query result
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    # Test function
    user = await get_user_by_username(mock_db, "nonexistent")
    
    # Verify
    assert user is None
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_by_id(mock_db, mock_user):
    """Test get_user_by_id service function."""
    # Mock DB get
    mock_db.get.return_value = mock_user
    
    # Test function
    user = await get_user_by_id(mock_db, 1)
    
    # Verify
    assert user == mock_user
    mock_db.get.assert_called_once_with(User, 1)


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(mock_db):
    """Test get_user_by_id with nonexistent user."""
    # Mock DB get
    mock_db.get.return_value = None
    
    # Test function
    user = await get_user_by_id(mock_db, 999)
    
    # Verify
    assert user is None
    mock_db.get.assert_called_once_with(User, 999)


@pytest.mark.asyncio
async def test_authenticate_user_success(mock_db, mock_user):
    """Test authenticate_user with valid credentials."""
    with patch("app.services.users.get_user_by_username") as mock_get_user, \
         patch("app.services.users.verify_password") as mock_verify:
        # Mock user retrieval
        mock_get_user.return_value = mock_user
        
        # Mock password verification
        mock_verify.return_value = True
        
        # Test function
        user = await authenticate_user(mock_db, "testuser", "password")
        
        # Verify
        assert user == mock_user
        mock_get_user.assert_called_once_with(mock_db, "testuser")
        mock_verify.assert_called_once_with("password", mock_user.hashed_password)


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(mock_db, mock_user):
    """Test authenticate_user with wrong password."""
    with patch("app.services.users.get_user_by_username") as mock_get_user, \
         patch("app.services.users.verify_password") as mock_verify:
        # Mock user retrieval
        mock_get_user.return_value = mock_user
        
        # Mock password verification
        mock_verify.return_value = False
        
        # Test function
        user = await authenticate_user(mock_db, "testuser", "wrongpassword")
        
        # Verify
        assert user is None
        mock_get_user.assert_called_once_with(mock_db, "testuser")
        mock_verify.assert_called_once_with("wrongpassword", mock_user.hashed_password)


@pytest.mark.asyncio
async def test_authenticate_user_nonexistent(mock_db):
    """Test authenticate_user with nonexistent user."""
    with patch("app.services.users.get_user_by_username") as mock_get_user:
        # Mock user retrieval
        mock_get_user.return_value = None
        
        # Test function
        user = await authenticate_user(mock_db, "nonexistent", "password")
        
        # Verify
        assert user is None
        mock_get_user.assert_called_once_with(mock_db, "nonexistent")


@pytest.mark.asyncio
async def test_create_user(mock_db):
    """Test create_user service function."""
    # Mock DB operations
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    
    # Test data
    user_in = UserCreate(
        username="newuser",
        password="newpassword",
        email="new@example.com",
        is_active=True,
        is_superuser=False,
        user_type=UserType.WEB
    )
    
    # Test function
    with patch("app.services.users.get_password_hash") as mock_get_hash:
        mock_get_hash.return_value = "hashed_password"
        
        user = await create_user(mock_db, user_in)
        
        # Verify user creation
        assert user.username == "newuser"
        assert user.hashed_password == "hashed_password"
        assert user.is_active is True
        # Web users should always be superusers
        assert user.is_superuser is True
        assert user.user_type == UserType.WEB
        
        # Verify DB operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_api(mock_db, mock_superuser):
    """Test create_new_user API endpoint."""
    with patch("app.api.users.create_user") as mock_create, \
         patch("app.api.users.get_user_by_username") as mock_get_user:
        # Mock user creation
        new_user = MagicMock(spec=User)
        new_user.username = "newuser"
        mock_create.return_value = new_user
        
        # Mock username check (no existing user)
        mock_get_user.return_value = None
        
        # Test data
        user_in = UserCreate(
            username="newuser",
            password="newpassword",
            email="new@example.com",
            is_active=True,
            is_superuser=False,
            user_type=UserType.BOT
        )
        
        # Test function
        user = await create_new_user(user_in, mock_db, mock_superuser)
        
        # Verify
        assert user == new_user
        mock_get_user.assert_called_once_with(mock_db, "newuser")
        mock_create.assert_called_once_with(mock_db, user_in)


@pytest.mark.asyncio
async def test_create_user_username_exists(mock_db, mock_superuser, mock_user):
    """Test create_new_user with existing username."""
    with patch("app.api.users.get_user_by_username") as mock_get_user:
        # Mock username check (user exists)
        mock_get_user.return_value = mock_user
        
        # Test data
        user_in = UserCreate(
            username="testuser",  # Existing username
            password="password",
            email="new@example.com",
            is_active=True,
            is_superuser=False,
            user_type=UserType.BOT
        )
        
        # Test function
        with pytest.raises(HTTPException) as exc_info:
            await create_new_user(user_in, mock_db, mock_superuser)
        
        # Verify exception details
        assert exc_info.value.status_code == 400
        assert "Username already taken" in exc_info.value.detail


@pytest.mark.asyncio
async def test_read_users(mock_db, mock_superuser):
    """Test read_users API endpoint."""
    # Mock DB query result
    mock_result = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_superuser]
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result
    
    # Test function
    users = await read_users(mock_db, mock_superuser)
    
    # Verify
    assert len(users) == 1
    assert users[0] == mock_superuser
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_read_users_with_filter(mock_db, mock_superuser):
    """Test read_users with user_type filter."""
    # Mock DB query result
    mock_result = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_superuser]
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result
    
    # Test function
    users = await read_users(mock_db, mock_superuser, user_type=UserType.WEB)
    
    # Verify
    assert len(users) == 1
    assert users[0] == mock_superuser
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_read_user_by_id(mock_db, mock_user):
    """Test read_user API endpoint (user reading own data)."""
    with patch("app.api.users.get_user_by_id") as mock_get_user:
        # Mock user retrieval
        mock_get_user.return_value = mock_user
        
        # Test function
        user = await read_user(1, mock_db, mock_user)
        
        # Verify
        assert user == mock_user
        mock_get_user.assert_called_once_with(mock_db, 1)


@pytest.mark.asyncio
async def test_read_user_by_id_as_admin(mock_db, mock_superuser, mock_user):
    """Test read_user API endpoint (admin reading other user)."""
    with patch("app.api.users.get_user_by_id") as mock_get_user:
        # Mock user retrieval
        mock_get_user.return_value = mock_user
        
        # Test function
        user = await read_user(1, mock_db, mock_superuser)
        
        # Verify
        assert user == mock_user
        mock_get_user.assert_called_once_with(mock_db, 1)


@pytest.mark.asyncio
async def test_read_user_by_id_unauthorized(mock_db, mock_user):
    """Test read_user API endpoint (user trying to read other user)."""
    with patch("app.api.users.get_user_by_id") as mock_get_user:
        # Mock user retrieval - a different user
        other_user = MagicMock(spec=User)
        other_user.id = 2
        mock_get_user.return_value = other_user
        
        # Test function
        with pytest.raises(HTTPException) as exc_info:
            await read_user(2, mock_db, mock_user)
        
        # Verify exception details
        assert exc_info.value.status_code == 403
        assert "Not enough privileges" in exc_info.value.detail


@pytest.mark.asyncio
async def test_read_user_not_found(mock_db, mock_superuser):
    """Test read_user with nonexistent user."""
    with patch("app.api.users.get_user_by_id") as mock_get_user:
        # Mock user retrieval
        mock_get_user.return_value = None
        
        # Test function
        with pytest.raises(HTTPException) as exc_info:
            await read_user(999, mock_db, mock_superuser)
        
        # Verify exception details
        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_user(mock_db, mock_user):
    """Test update_user service function."""
    # Mock DB operations
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    
    # Test data
    user_update = UserUpdate(
        password="newpassword",
        email="updated@example.com",
        is_active=False
    )
    
    # Test function
    with patch("app.services.users.get_password_hash") as mock_get_hash:
        mock_get_hash.return_value = "new_hashed_password"
        
        updated_user = await update_user(mock_db, mock_user, user_update)
        
        # Verify user update
        assert updated_user == mock_user
        assert mock_user.hashed_password == "new_hashed_password"
        assert mock_user.email == "updated@example.com"
        assert mock_user.is_active is False
        
        # Verify DB operations
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_endpoint(mock_db, mock_user):
    """Test update_user_endpoint API function (user updating self)."""
    with patch("app.api.users.get_user_by_id") as mock_get_user, \
         patch("app.api.users.update_user") as mock_update:
        # Mock user retrieval
        mock_get_user.return_value = mock_user
        
        # Mock user update
        mock_update.return_value = mock_user
        
        # Test data
        user_update = UserUpdate(
            password="newpassword",
            email="updated@example.com"
        )
        
        # Test function
        updated_user = await update_user_endpoint(1, user_update, mock_db, mock_user)
        
        # Verify
        assert updated_user == mock_user
        mock_get_user.assert_called_once_with(mock_db, 1)
        mock_update.assert_called_once_with(mock_db, mock_user, user_update)


@pytest.mark.asyncio
async def test_update_user_endpoint_as_admin(mock_db, mock_superuser, mock_user):
    """Test update_user_endpoint (admin updating other user)."""
    with patch("app.api.users.get_user_by_id") as mock_get_user, \
         patch("app.api.users.update_user") as mock_update:
        # Mock user retrieval
        mock_get_user.return_value = mock_user
        
        # Mock user update
        mock_update.return_value = mock_user
        
        # Test data - admin making user a superuser
        user_update = UserUpdate(
            is_superuser=True
        )
        
        # Test function
        updated_user = await update_user_endpoint(1, user_update, mock_db, mock_superuser)
        
        # Verify
        assert updated_user == mock_user
        mock_get_user.assert_called_once_with(mock_db, 1)
        mock_update.assert_called_once_with(mock_db, mock_user, user_update)


@pytest.mark.asyncio
async def test_update_user_endpoint_unauthorized(mock_db, mock_user):
    """Test update_user_endpoint (user trying to update other user)."""
    with patch("app.api.users.get_user_by_id") as mock_get_user:
        # Mock user retrieval - a different user
        other_user = MagicMock(spec=User)
        other_user.id = 2
        mock_get_user.return_value = other_user
        
        # Test data
        user_update = UserUpdate(email="hacked@example.com")
        
        # Test function
        with pytest.raises(HTTPException) as exc_info:
            await update_user_endpoint(2, user_update, mock_db, mock_user)
        
        # Verify exception details
        assert exc_info.value.status_code == 403
        assert "Not enough privileges" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_user_endpoint_change_superuser_unauthorized(mock_db, mock_user):
    """Test update_user_endpoint (user trying to make self superuser)."""
    with patch("app.api.users.get_user_by_id") as mock_get_user:
        # Mock user retrieval
        mock_get_user.return_value = mock_user
        
        # Test data - trying to become superuser
        user_update = UserUpdate(is_superuser=True)
        
        # Test function
        with pytest.raises(HTTPException) as exc_info:
            await update_user_endpoint(1, user_update, mock_db, mock_user)
        
        # Verify exception details
        assert exc_info.value.status_code == 403
        assert "Not enough privileges to modify superuser status" in exc_info.value.detail