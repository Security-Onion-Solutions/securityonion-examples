"""Tests for users service."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.users import User
from app.schemas.users import UserCreate, UserUpdate, UserType
from app.services.users import (
    get_user_count,
    get_user_by_username,
    get_user_by_id,
    authenticate_user,
    create_user,
    update_user
)
from app.core.security import get_password_hash, verify_password
from tests.utils import await_mock


@pytest.mark.asyncio
async def test_get_user_count(db: AsyncSession):
    """Test counting users in the database."""
    # Create test users
    for i in range(3):
        user = User(
            username=f"countuser{i}",
            hashed_password=get_password_hash(f"password{i}"),
            is_active=True,
            is_superuser=False,
            user_type=UserType.WEB
        )
        db.add(user)
    await db.commit()
    
    # Get the count
    count = await get_user_count(db)
    
    # There should be at least 3 users (could be more from other tests)
    assert count >= 3
    assert isinstance(count, int)


@pytest.mark.asyncio
async def test_get_user_count_python_313(db: AsyncSession):
    """Test get_user_count with Python 3.13 coroutine handling."""
    # Mock the database query
    mock_result = AsyncMock()
    mock_result.scalar_one.return_value = await_mock(5)
    
    # Mock db.execute
    with patch.object(db, 'execute', return_value=await_mock(mock_result)):
        count = await get_user_count(db)
        assert count == 5


@pytest.mark.asyncio
async def test_get_user_by_username(db: AsyncSession):
    """Test getting a user by username."""
    # Create a test user
    test_user = User(
        username="testgetbyusername",
        hashed_password=get_password_hash("password"),
        is_active=True,
        is_superuser=False,
        user_type=UserType.WEB
    )
    db.add(test_user)
    await db.commit()
    
    # Get the user
    user = await get_user_by_username(db, "testgetbyusername")
    
    # Verify user found
    assert user is not None
    assert user.username == "testgetbyusername"
    
    # Test user not found
    not_found = await get_user_by_username(db, "nonexistent")
    assert not_found is None


@pytest.mark.asyncio
async def test_get_user_by_username_python_313(db: AsyncSession):
    """Test get_user_by_username with Python 3.13 coroutine handling."""
    # Mock user
    mock_user = MagicMock(username="testuser")
    
    # Mock the database query
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = await_mock(mock_user)
    
    # Mock db.execute
    with patch.object(db, 'execute', return_value=await_mock(mock_result)):
        user = await get_user_by_username(db, "testuser")
        assert user == mock_user


@pytest.mark.asyncio
async def test_get_user_by_id(db: AsyncSession):
    """Test getting a user by ID."""
    # Create a test user
    test_user = User(
        username="testgetbyid",
        hashed_password=get_password_hash("password"),
        is_active=True,
        is_superuser=False,
        user_type=UserType.WEB
    )
    db.add(test_user)
    await db.commit()
    await db.refresh(test_user)
    
    # Get the user
    user = await get_user_by_id(db, test_user.id)
    
    # Verify user found
    assert user is not None
    assert user.username == "testgetbyid"
    
    # Test user not found
    not_found = await get_user_by_id(db, 9999)
    assert not_found is None


@pytest.mark.asyncio
async def test_get_user_by_id_python_313(db: AsyncSession):
    """Test get_user_by_id with Python 3.13 coroutine handling."""
    # Mock user
    mock_user = MagicMock(id=1, username="testuser")
    
    # Mock db.get
    with patch.object(db, 'get', return_value=await_mock(mock_user)):
        user = await get_user_by_id(db, 1)
        assert user == mock_user


@pytest.mark.asyncio
async def test_authenticate_user_success(db: AsyncSession):
    """Test successfully authenticating a user."""
    # Create a test user with known password
    password = "correctpassword"
    test_user = User(
        username="testauthuser",
        hashed_password=get_password_hash(password),
        is_active=True,
        is_superuser=False,
        user_type=UserType.WEB
    )
    db.add(test_user)
    await db.commit()
    
    # Authenticate with correct credentials
    authenticated_user = await authenticate_user(db, "testauthuser", password)
    
    # Verify authentication succeeded
    assert authenticated_user is not None
    assert authenticated_user.username == "testauthuser"


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(db: AsyncSession):
    """Test authenticating a user with wrong password."""
    # Create a test user
    test_user = User(
        username="testwrongpassword",
        hashed_password=get_password_hash("correctpassword"),
        is_active=True,
        is_superuser=False,
        user_type=UserType.WEB
    )
    db.add(test_user)
    await db.commit()
    
    # Authenticate with wrong password
    authenticated_user = await authenticate_user(db, "testwrongpassword", "wrongpassword")
    
    # Verify authentication failed
    assert authenticated_user is None


@pytest.mark.asyncio
async def test_authenticate_user_nonexistent(db: AsyncSession):
    """Test authenticating a non-existent user."""
    # Authenticate with non-existent username
    authenticated_user = await authenticate_user(db, "nonexistentuser", "anypassword")
    
    # Verify authentication failed
    assert authenticated_user is None


@pytest.mark.asyncio
async def test_create_user_web(db: AsyncSession):
    """Test creating a web user."""
    # Create user data for web user
    user_data = UserCreate(
        username="newwebuser",
        password="password123",
        is_active=True,
        is_superuser=False,  # Even if False, web users are always superusers
        user_type=UserType.WEB
    )
    
    # Create the user
    user = await create_user(db, user_data)
    
    # Verify user was created
    assert user.username == "newwebuser"
    assert user.is_active is True
    assert user.is_superuser is True  # Web users are always superusers
    assert user.user_type == UserType.WEB
    
    # Verify password was hashed
    assert user.hashed_password != "password123"
    assert verify_password("password123", user.hashed_password)


@pytest.mark.asyncio
async def test_create_user_api(db: AsyncSession):
    """Test creating an API user."""
    # Create user data for API user
    user_data = UserCreate(
        username="newapiuser",
        password="apipassword",
        is_active=True,
        is_superuser=True,
        user_type=UserType.API
    )
    
    # Create the user
    user = await create_user(db, user_data)
    
    # Verify user was created
    assert user.username == "newapiuser"
    assert user.is_active is True
    assert user.is_superuser is True
    assert user.user_type == UserType.API
    
    # Verify password was hashed
    assert user.hashed_password != "apipassword"
    assert verify_password("apipassword", user.hashed_password)


@pytest.mark.asyncio
async def test_update_user_password(db: AsyncSession):
    """Test updating a user's password."""
    # Create a test user
    test_user = User(
        username="updatepwuser",
        hashed_password=get_password_hash("oldpassword"),
        is_active=True,
        is_superuser=False,
        user_type=UserType.WEB
    )
    db.add(test_user)
    await db.commit()
    await db.refresh(test_user)
    
    # Update the user's password
    update_data = UserUpdate(password="newpassword")
    updated_user = await update_user(db, test_user, update_data)
    
    # Verify password was updated
    assert updated_user.username == "updatepwuser"
    assert verify_password("newpassword", updated_user.hashed_password)
    assert not verify_password("oldpassword", updated_user.hashed_password)


@pytest.mark.asyncio
async def test_update_user_fields(db: AsyncSession):
    """Test updating various user fields."""
    # Create a test user
    test_user = User(
        username="updatefieldsuser",
        hashed_password=get_password_hash("password"),
        is_active=True,
        is_superuser=False,
        user_type=UserType.API
    )
    db.add(test_user)
    await db.commit()
    await db.refresh(test_user)
    
    # Update multiple fields
    update_data = UserUpdate(
        is_active=False,
        is_superuser=True,
        user_type=UserType.WEB
    )
    updated_user = await update_user(db, test_user, update_data)
    
    # Verify fields were updated
    assert updated_user.username == "updatefieldsuser"  # Unchanged
    assert updated_user.is_active is False
    assert updated_user.is_superuser is True
    assert updated_user.user_type == UserType.WEB
    assert verify_password("password", updated_user.hashed_password)  # Password unchanged