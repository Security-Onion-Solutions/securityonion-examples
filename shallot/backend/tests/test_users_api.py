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
from .utils import await_mock, make_mock_awaitable

client = TestClient(app)


def await_mock(return_value):
    # Helper function to make mock return values awaitable in Python 3.13
    async def _awaitable():
        return return_value
    return _awaitable()

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock(spec=AsyncSession)


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
async def test_get_user_count(db):
    """Test get_user_count service function."""
    # Mock DB query result
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 5

    mock_result.scalar_one.return_value = await_mock(mock_result.scalar_one.return_value)

    mock_result.scalar_one.return_value = await_mock(mock_result.scalar_one.return_value)  # Make awaitable for Python 3.13


    mock_result.scalar_one.return_value = await_mock(mock_result.scalar_one.return_value)
    make_mock_awaitable(mock_result, "scalar_one")
    
    db.execute.return_value = mock_result

    
    db.execute.return_value = await_mock(db.execute.return_value)  # Make awaitable for Python 3.13
    make_mock_awaitable(db, "execute")
    
    # Test function
    count = await get_user_count(db)
    
    # Verify
    assert count == 5
    db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_by_username(db, mock_user):
    """Test get_user_by_username service function."""
    # Mock DB query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user

    mock_result.scalar_one_or_none.return_value = await_mock(mock_result.scalar_one_or_none.return_value)

    mock_result.scalar_one_or_none.return_value = await_mock(mock_result.scalar_one_or_none.return_value)  # Make awaitable for Python 3.13


    mock_result.scalar_one_or_none.return_value = await_mock(mock_result.scalar_one_or_none.return_value)
    make_mock_awaitable(mock_result, "scalar_one_or_none")
    
    db.execute.return_value = mock_result

    
    db.execute.return_value = await_mock(db.execute.return_value)  # Make awaitable for Python 3.13
    make_mock_awaitable(db, "execute")
    
    # Test function
    user = await get_user_by_username(db, "testuser")
    
    # Verify
    assert user == mock_user
    db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_by_username_not_found(db):
    """Test get_user_by_username with nonexistent user."""
    # Mock DB query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_result.scalar_one_or_none.return_value = await_mock(mock_result.scalar_one_or_none.return_value)

    mock_result.scalar_one_or_none.return_value = await_mock(mock_result.scalar_one_or_none.return_value)  # Make awaitable for Python 3.13


    mock_result.scalar_one_or_none.return_value = await_mock(mock_result.scalar_one_or_none.return_value)
    make_mock_awaitable(mock_result, "scalar_one_or_none")
    
    db.execute.return_value = mock_result

    
    db.execute.return_value = await_mock(db.execute.return_value)  # Make awaitable for Python 3.13
    make_mock_awaitable(db, "execute")
    
    # Test function
    user = await get_user_by_username(db, "nonexistent")
    
    # Verify
    assert user is None
    db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_by_id(db, mock_user):
    """Test get_user_by_id service function."""
    # Mock DB get
    db.get.return_value = mock_user
    make_mock_awaitable(db, "get")
    
    # Test function
    user = await get_user_by_id(db, 1)
    
    # Verify
    assert user == mock_user
    db.get.assert_called_once_with(User, 1)


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(db):
    """Test get_user_by_id with nonexistent user."""
    # Mock DB get
    db.get.return_value = None
    make_mock_awaitable(db, "get")
    
    # Test function
    user = await get_user_by_id(db, 999)
    
    # Verify
    assert user is None
    db.get.assert_called_once_with(User, 999)


@pytest.mark.asyncio
async def test_authenticate_user_success(db, mock_user):
    """Test authenticate_user with valid credentials."""
    with patch("app.services.users.get_user_by_username") as mock_get_user, \
         patch("app.services.users.verify_password") as mock_verify:
        # Mock user retrieval
        mock_get_user.return_value = mock_user
        
        # Mock password verification
        mock_verify.return_value = True
        
        # Test function
        user = await authenticate_user(db, "testuser", "password")
        
        # Verify
        assert user == mock_user
        mock_get_user.assert_called_once_with(db, "testuser")
        mock_verify.assert_called_once_with("password", mock_user.hashed_password)


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(db, mock_user):
    """Test authenticate_user with wrong password."""
    with patch("app.services.users.get_user_by_username") as mock_get_user, \
         patch("app.services.users.verify_password") as mock_verify:
        # Mock user retrieval
        mock_get_user.return_value = mock_user
        
        # Mock password verification
        mock_verify.return_value = False
        
        # Test function
        user = await authenticate_user(db, "testuser", "wrongpassword")
        
        # Verify
        assert user is None
        mock_get_user.assert_called_once_with(db, "testuser")
        mock_verify.assert_called_once_with("wrongpassword", mock_user.hashed_password)


@pytest.mark.asyncio
async def test_authenticate_user_nonexistent(db):
    """Test authenticate_user with nonexistent user."""
    with patch("app.services.users.get_user_by_username") as mock_get_user:
        # Mock user retrieval
        mock_get_user.return_value = None
        
        # Test function
        user = await authenticate_user(db, "nonexistent", "password")
        
        # Verify
        assert user is None
        mock_get_user.assert_called_once_with(db, "nonexistent")


@pytest.mark.asyncio
async def test_create_user(db):
    """Test create_user service function."""
    # Mock DB operations
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    
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
        
        user = await create_user(db, user_in)
        
        # Verify user creation
        assert user.username == "newuser"
        assert user.hashed_password == "hashed_password"
        assert user.is_active is True
        # Web users should always be superusers
        assert user.is_superuser is True
        assert user.user_type == UserType.WEB
        
        # Verify DB operations
        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_api(db, mock_superuser):
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
        user = await create_new_user(user_in, db, mock_superuser)
        
        # Verify
        assert user == new_user
        mock_get_user.assert_called_once_with(db, "newuser")
        mock_create.assert_called_once_with(db, user_in)


@pytest.mark.asyncio
async def test_create_user_username_exists(db, mock_superuser, mock_user):
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
            await create_new_user(user_in, db, mock_superuser)
        
        # Verify exception details
        assert exc_info.value.status_code == 400
        assert "Username already taken" in exc_info.value.detail


@pytest.mark.asyncio
async def test_read_users(db, mock_superuser):
    """Test read_users API endpoint."""
    # Mock DB query result
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_superuser]
    mock_result.scalars.return_value = mock_scalars
    make_mock_awaitable(mock_result, "scalars")
    
    db.execute.return_value = mock_result

    
    db.execute.return_value = await_mock(db.execute.return_value)  # Make awaitable for Python 3.13
    make_mock_awaitable(db, "execute")
    
    # Test function
    users = await read_users(db, mock_superuser)
    
    # Verify
    assert len(users) == 1
    assert users[0] == mock_superuser
    db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_read_users_with_filter(db, mock_superuser):
    """Test read_users with user_type filter."""
    # Mock DB query result
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_superuser]
    mock_result.scalars.return_value = mock_scalars
    make_mock_awaitable(mock_result, "scalars")
    
    db.execute.return_value = mock_result

    
    db.execute.return_value = await_mock(db.execute.return_value)  # Make awaitable for Python 3.13
    make_mock_awaitable(db, "execute")
    
    # Test function
    users = await read_users(db, mock_superuser, user_type=UserType.WEB)
    
    # Verify
    assert len(users) == 1
    assert users[0] == mock_superuser
    db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_read_user_by_id(db, mock_user):
    """Test read_user API endpoint (user reading own data)."""
    with patch("app.api.users.get_user_by_id") as mock_get_user:
        # Mock user retrieval
        mock_get_user.return_value = mock_user
        
        # Test function
        user = await read_user(1, db, mock_user)
        
        # Verify
        assert user == mock_user
        mock_get_user.assert_called_once_with(db, 1)


@pytest.mark.asyncio
async def test_read_user_by_id_as_admin(db, mock_superuser, mock_user):
    """Test read_user API endpoint (admin reading other user)."""
    with patch("app.api.users.get_user_by_id") as mock_get_user:
        # Mock user retrieval
        mock_get_user.return_value = mock_user
        
        # Test function
        user = await read_user(1, db, mock_superuser)
        
        # Verify
        assert user == mock_user
        mock_get_user.assert_called_once_with(db, 1)


@pytest.mark.asyncio
async def test_read_user_by_id_unauthorized(db, mock_user):
    """Test read_user API endpoint (user trying to read other user)."""
    with patch("app.api.users.get_user_by_id") as mock_get_user:
        # Mock user retrieval - a different user
        other_user = MagicMock(spec=User)
        other_user.id = 2
        mock_get_user.return_value = other_user
        
        # Test function
        with pytest.raises(HTTPException) as exc_info:
            await read_user(2, db, mock_user)
        
        # Verify exception details
        assert exc_info.value.status_code == 403
        assert "Not enough privileges" in exc_info.value.detail


@pytest.mark.asyncio
async def test_read_user_not_found(db, mock_superuser):
    """Test read_user with nonexistent user."""
    with patch("app.api.users.get_user_by_id") as mock_get_user:
        # Mock user retrieval
        mock_get_user.return_value = None
        
        # Test function
        with pytest.raises(HTTPException) as exc_info:
            await read_user(999, db, mock_superuser)
        
        # Verify exception details
        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_user(db, mock_user):
    """Test update_user service function."""
    # Mock DB operations
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    
    # Test data
    user_update = UserUpdate(
        password="newpassword",
        email="updated@example.com",
        is_active=False
    )
    
    # Test function
    with patch("app.services.users.get_password_hash") as mock_get_hash:
        mock_get_hash.return_value = "new_hashed_password"
        
        updated_user = await update_user(db, mock_user, user_update)
        
        # Verify user update
        assert updated_user == mock_user
        assert mock_user.hashed_password == "new_hashed_password"
        assert mock_user.email == "updated@example.com"
        assert mock_user.is_active is False
        
        # Verify DB operations
        db.commit.assert_called_once()
        db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_endpoint(db, mock_user):
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
        updated_user = await update_user_endpoint(1, user_update, db, mock_user)
        
        # Verify
        assert updated_user == mock_user
        mock_get_user.assert_called_once_with(db, 1)
        mock_update.assert_called_once_with(db, mock_user, user_update)


@pytest.mark.asyncio
async def test_update_user_endpoint_as_admin(db, mock_superuser, mock_user):
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
        updated_user = await update_user_endpoint(1, user_update, db, mock_superuser)
        
        # Verify
        assert updated_user == mock_user
        mock_get_user.assert_called_once_with(db, 1)
        mock_update.assert_called_once_with(db, mock_user, user_update)


@pytest.mark.asyncio
async def test_update_user_endpoint_unauthorized(db, mock_user):
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
            await update_user_endpoint(2, user_update, db, mock_user)
        
        # Verify exception details
        assert exc_info.value.status_code == 403
        assert "Not enough privileges" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_user_endpoint_change_superuser_unauthorized(db, mock_user):
    """Test update_user_endpoint (user trying to make self superuser)."""
    with patch("app.api.users.get_user_by_id") as mock_get_user:
        # Mock user retrieval
        mock_get_user.return_value = mock_user
        
        # Test data - trying to become superuser
        user_update = UserUpdate(is_superuser=True)
        
        # Test function
        with pytest.raises(HTTPException) as exc_info:
            await update_user_endpoint(1, user_update, db, mock_user)
        
        # Verify exception details
        assert exc_info.value.status_code == 403
        assert "Not enough privileges to modify superuser status" in exc_info.value.detail