"""Tests for authentication API endpoints."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.api.auth import (
    get_current_user,
    get_current_active_user,
    get_current_active_superuser,
    login_for_access_token,
    refresh_token,
    check_setup_required,
    initial_setup
)
from app.models.users import User
from app.schemas.users import UserCreate, Token

client = TestClient(app)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    user.is_active = True
    user.is_superuser = False
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
    user.hashed_password = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # "password"
    return user


@pytest.mark.asyncio
async def test_get_current_user_valid(mock_db, mock_user):
    """Test get_current_user with valid token."""
    with patch("app.api.auth.jwt.decode") as mock_decode, \
         patch("app.api.auth.get_user_by_username") as mock_get_user:
        # Mock token decoding
        mock_decode.return_value = {"sub": "testuser", "is_superuser": False}
        
        # Mock user retrieval
        mock_get_user.return_value = mock_user
        
        # Test the function
        user = await get_current_user("valid_token", mock_db)
        
        # Verify returned user
        assert user == mock_user
        mock_get_user.assert_called_once_with(mock_db, "testuser")


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(mock_db):
    """Test get_current_user with invalid token."""
    with patch("app.api.auth.jwt.decode") as mock_decode:
        # Mock token decoding to raise exception
        mock_decode.side_effect = Exception("Invalid token")
        
        # Test the function raises expected exception
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("invalid_token", mock_db)
        
        # Verify exception details
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_missing_sub(mock_db):
    """Test get_current_user with token missing subject."""
    with patch("app.api.auth.jwt.decode") as mock_decode:
        # Mock token decoding with missing 'sub' field
        mock_decode.return_value = {"is_superuser": False}
        
        # Test the function raises expected exception
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("invalid_token", mock_db)
        
        # Verify exception details
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_nonexistent(mock_db):
    """Test get_current_user with nonexistent user."""
    with patch("app.api.auth.jwt.decode") as mock_decode, \
         patch("app.api.auth.get_user_by_username") as mock_get_user:
        # Mock token decoding
        mock_decode.return_value = {"sub": "nonexistent", "is_superuser": False}
        
        # Mock user retrieval returns None
        mock_get_user.return_value = None
        
        # Test the function raises expected exception
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("valid_token", mock_db)
        
        # Verify exception details
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_active_user(mock_user):
    """Test get_current_active_user with active user."""
    # Test with active user
    user = await get_current_active_user(mock_user)
    assert user == mock_user


@pytest.mark.asyncio
async def test_get_current_active_user_inactive():
    """Test get_current_active_user with inactive user."""
    # Create inactive user
    inactive_user = MagicMock(spec=User)
    inactive_user.is_active = False
    
    # Test with inactive user
    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_user(inactive_user)
    
    # Verify exception details
    assert exc_info.value.status_code == 400
    assert "Inactive user" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_active_superuser(mock_superuser):
    """Test get_current_active_superuser with superuser."""
    # Test with superuser
    user = await get_current_active_superuser(mock_superuser)
    assert user == mock_superuser


@pytest.mark.asyncio
async def test_get_current_active_superuser_not_admin(mock_user):
    """Test get_current_active_superuser with non-superuser."""
    # Test with non-superuser
    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_superuser(mock_user)
    
    # Verify exception details
    assert exc_info.value.status_code == 403
    assert "Not enough privileges" in exc_info.value.detail


@pytest.mark.asyncio
async def test_login_for_access_token(mock_db, mock_user):
    """Test login_for_access_token with valid credentials."""
    with patch("app.api.auth.get_user_by_username") as mock_get_user, \
         patch("app.api.auth.verify_password") as mock_verify, \
         patch("app.api.auth.create_access_token") as mock_create_token:
        # Mock form data
        form_data = MagicMock()
        form_data.username = "testuser"
        form_data.password = "password"
        
        # Mock user retrieval
        mock_get_user.return_value = mock_user
        
        # Mock password verification
        mock_verify.return_value = True
        
        # Mock token creation
        mock_create_token.return_value = "test_token"
        
        # Test the function
        token = await login_for_access_token(form_data, mock_db)
        
        # Verify response
        assert token == {"access_token": "test_token", "token_type": "bearer"}
        mock_get_user.assert_called_once_with(mock_db, "testuser")
        mock_verify.assert_called_once_with("password", mock_user.hashed_password)
        mock_create_token.assert_called_once()


@pytest.mark.asyncio
async def test_login_for_access_token_invalid_user(mock_db):
    """Test login_for_access_token with nonexistent user."""
    with patch("app.api.auth.get_user_by_username") as mock_get_user:
        # Mock form data
        form_data = MagicMock()
        form_data.username = "nonexistent"
        form_data.password = "password"
        
        # Mock user retrieval returns None
        mock_get_user.return_value = None
        
        # Test the function raises expected exception
        with pytest.raises(HTTPException) as exc_info:
            await login_for_access_token(form_data, mock_db)
        
        # Verify exception details
        assert exc_info.value.status_code == 401
        assert "Incorrect username or password" in exc_info.value.detail


@pytest.mark.asyncio
async def test_login_for_access_token_wrong_password(mock_db, mock_user):
    """Test login_for_access_token with wrong password."""
    with patch("app.api.auth.get_user_by_username") as mock_get_user, \
         patch("app.api.auth.verify_password") as mock_verify:
        # Mock form data
        form_data = MagicMock()
        form_data.username = "testuser"
        form_data.password = "wrongpassword"
        
        # Mock user retrieval
        mock_get_user.return_value = mock_user
        
        # Mock password verification returns False
        mock_verify.return_value = False
        
        # Test the function raises expected exception
        with pytest.raises(HTTPException) as exc_info:
            await login_for_access_token(form_data, mock_db)
        
        # Verify exception details
        assert exc_info.value.status_code == 401
        assert "Incorrect username or password" in exc_info.value.detail


@pytest.mark.asyncio
async def test_refresh_token(mock_user):
    """Test refresh_token endpoint."""
    with patch("app.api.auth.create_access_token") as mock_create_token:
        # Mock token creation
        mock_create_token.return_value = "refreshed_token"
        
        # Test the function
        result = await refresh_token(mock_user)
        
        # Verify response
        assert result == {"access_token": "refreshed_token", "token_type": "bearer"}
        mock_create_token.assert_called_once_with(
            subject=mock_user.username,
            expires_delta=pytest.approx(timedelta(minutes=30), rel=1e-3),
            is_superuser=mock_user.is_superuser
        )


@pytest.mark.asyncio
async def test_check_setup_required_empty(mock_db):
    """Test check_setup_required when no users exist."""
    with patch("app.api.auth.select") as mock_select:
        # Setup mock for query result (no users)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Test the function
        result = await check_setup_required(mock_db)
        
        # Verify result indicates setup is required
        assert result == {"setup_required": True}


@pytest.mark.asyncio
async def test_check_setup_required_with_users(mock_db, mock_user):
    """Test check_setup_required when users exist."""
    with patch("app.api.auth.select") as mock_select:
        # Setup mock for query result (with user)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        # Test the function
        result = await check_setup_required(mock_db)
        
        # Verify result indicates setup is not required
        assert result == {"setup_required": False}


@pytest.mark.asyncio
async def test_initial_setup_first_user(mock_db):
    """Test initial_setup when no users exist."""
    with patch("app.api.auth.select") as mock_select, \
         patch("app.api.auth.create_user") as mock_create_user, \
         patch("app.api.auth.create_access_token") as mock_create_token:
        # Setup mock for query result (no users)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Mock user creation
        new_user = MagicMock(spec=User)
        new_user.username = "adminuser"
        new_user.is_superuser = True
        mock_create_user.return_value = new_user
        
        # Mock token creation
        mock_create_token.return_value = "admin_token"
        
        # Create user data
        user_in = UserCreate(
            username="adminuser",
            email="admin@example.com",
            password="adminpass",
            is_superuser=False  # Should be overridden to True
        )
        
        # Test the function
        result = await initial_setup(user_in, mock_db)
        
        # Verify result contains token
        assert result == {"access_token": "admin_token", "token_type": "bearer"}
        
        # Verify user was created as superuser
        assert user_in.is_superuser is True
        mock_create_user.assert_called_once_with(mock_db, user_in)


@pytest.mark.asyncio
async def test_initial_setup_users_exist(mock_db, mock_user):
    """Test initial_setup when users already exist."""
    with patch("app.api.auth.select") as mock_select:
        # Setup mock for query result (with user)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        # Create user data
        user_in = UserCreate(
            username="adminuser",
            email="admin@example.com",
            password="adminpass"
        )
        
        # Test the function raises expected exception
        with pytest.raises(HTTPException) as exc_info:
            await initial_setup(user_in, mock_db)
        
        # Verify exception details
        assert exc_info.value.status_code == 400
        assert "Setup already completed" in exc_info.value.detail


# Integration tests with actual API endpoints

def test_api_token_endpoint():
    """Test token endpoint integration."""
    with patch("app.api.auth.get_user_by_username") as mock_get_user, \
         patch("app.api.auth.verify_password") as mock_verify, \
         patch("app.api.auth.create_access_token") as mock_create_token:
        # Mock user
        user = MagicMock(spec=User)
        user.username = "testuser"
        user.hashed_password = "hashedpass"
        user.is_superuser = False
        
        # Set up mocks
        mock_get_user.return_value = user
        mock_verify.return_value = True
        mock_create_token.return_value = "test_token"
        
        # Make the request
        response = client.post(
            "/api/auth/token",
            data={"username": "testuser", "password": "password"}
        )
        
        # Verify response
        assert response.status_code == 200
        assert response.json() == {"access_token": "test_token", "token_type": "bearer"}


def test_api_setup_required_endpoint():
    """Test setup_required endpoint integration."""
    with patch("app.database.get_db", new_callable=AsyncMock) as mock_get_db:
        # Mock DB session
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        
        # Mock DB query result (no users)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Make the request
        response = client.get("/api/auth/setup-required")
        
        # Verify response
        assert response.status_code == 200
        assert response.json() == {"setup_required": True}