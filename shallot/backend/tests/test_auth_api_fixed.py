"""Tests for authentication API endpoints with Python 3.13 compatibility."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

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


# Helper for Python 3.13 compatibility
async def async_return(value):
    """Helper function to make a coroutine that returns a value."""
    return value


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
async def test_check_setup_required_empty():
    """Test check_setup_required when no users exist."""
    # Create mock database session
    db = AsyncMock(spec=AsyncSession)
    
    # Create mock execute result
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    
    # Configure db.execute to return awaitable result
    db.execute.return_value = result
    
    with patch("app.api.auth.select"):
        # Test the function
        response = await check_setup_required(db)
        
        # Verify response
        assert response == {"setup_required": True}


@pytest.mark.asyncio
async def test_check_setup_required_with_users(mock_user):
    """Test check_setup_required when users exist."""
    # Create mock database session
    db = AsyncMock(spec=AsyncSession)
    
    # Create mock execute result
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_user
    
    # Configure db.execute to return awaitable result  
    db.execute.return_value = result
    
    with patch("app.api.auth.select"):
        # Test the function
        response = await check_setup_required(db)
        
        # Verify response
        assert response == {"setup_required": False}


@pytest.mark.asyncio
async def test_initial_setup_first_user():
    """Test initial_setup when no users exist."""
    # Create mock database session
    db = AsyncMock(spec=AsyncSession)
    
    # Create mock execute result (no users)
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    
    # Configure db.execute to return awaitable result
    db.execute.return_value = result
    
    with patch("app.api.auth.select"), \
         patch("app.api.auth.create_user") as mock_create_user, \
         patch("app.api.auth.create_access_token") as mock_create_token:
        
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
        response = await initial_setup(user_in, db)
        
        # Verify result contains token
        assert response == {"access_token": "admin_token", "token_type": "bearer"}
        
        # Verify user was created as superuser
        assert user_in.is_superuser is True
        mock_create_user.assert_called_once_with(db, user_in)


@pytest.mark.asyncio
async def test_initial_setup_users_exist(mock_user):
    """Test initial_setup when users already exist."""
    # Create mock database session
    db = AsyncMock(spec=AsyncSession)
    
    # Create mock execute result (with user)
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_user
    
    # Configure db.execute to return awaitable result
    db.execute.return_value = result
    
    with patch("app.api.auth.select"):
        # Create user data
        user_in = UserCreate(
            username="adminuser",
            email="admin@example.com",
            password="adminpass"
        )
        
        # Test function raises expected exception
        with pytest.raises(HTTPException) as exc_info:
            await initial_setup(user_in, db)
        
        # Verify exception details
        assert exc_info.value.status_code == 400
        assert "Setup already completed" in exc_info.value.detail


def test_api_setup_required_endpoint():
    """Test setup_required endpoint integration."""
    with patch("app.database.get_db") as mock_get_db:
        # Mock DB session
        db = AsyncMock(spec=AsyncSession)
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db.execute.return_value = result
        
        # Configure get_db to return db session
        async def get_db_side_effect():
            yield db
            
        mock_get_db.side_effect = get_db_side_effect
        
        # Make request
        response = client.get("/api/auth/setup-required")
        
        # Verify response
        assert response.status_code == 200
        assert response.json() == {"setup_required": True}