"""Tests for users service."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, MagicMock
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
async def test_users_service_mock():
    """Test users service with a completely mocked DB."""
    # Create a mock DB session
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Test get_user_count with mocked DB
    mock_result = MagicMock()
    
    async def mock_scalar_one():
        return 10
    
    mock_result.scalar_one = AsyncMock(side_effect=mock_scalar_one)
    
    async def mock_execute(*args, **kwargs):
        return mock_result
    
    mock_db.execute = AsyncMock(side_effect=mock_execute)
    
    # Call the function
    count = await get_user_count(mock_db)
    
    # Verify the result
    assert count == 10
    
    # Verify DB was called correctly
    mock_db.execute.assert_called_once()
    
    # Get args passed to execute
    args, kwargs = mock_db.execute.call_args
    
    # The first arg should be a select statement with a count function
    # The exact SQL might vary slightly by SQLAlchemy version
    select_str = str(args[0]).lower()
    assert "select count" in select_str
    assert "from users" in select_str


# Using await_mock from tests.utils

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
    # Create a more reliable mock with proper async behavior
    mock_result = MagicMock()
    
    # Create an async function that will properly return the value when awaited
    async def mock_scalar_one():
        return 5
    
    # Set up the mock's scalar_one method to return our awaitable function
    mock_result.scalar_one = AsyncMock(side_effect=mock_scalar_one)
    
    # Create a mock for db.execute
    async def mock_execute(*args, **kwargs):
        return mock_result
    
    # Mock db.execute to return our async result
    with patch.object(db, 'execute', AsyncMock(side_effect=mock_execute)):
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
    
    # Mock the database query result with proper async behavior
    mock_result = MagicMock()
    
    # Create an async function that will properly return the mock user when awaited
    async def mock_scalar_one_or_none():
        return mock_user
    
    # Set up the mock's scalar_one_or_none method to use our async function
    mock_result.scalar_one_or_none = AsyncMock(side_effect=mock_scalar_one_or_none)
    
    # Create async mock for db.execute to return our result
    async def mock_execute(*args, **kwargs):
        return mock_result
    
    # Test the get_user_by_username function with our mocks
    with patch.object(db, 'execute', AsyncMock(side_effect=mock_execute)):
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
    
    # Create proper async mock for db.get
    async def mock_get_user(*args, **kwargs):
        return mock_user
        
    # Mock db.get
    with patch.object(db, 'get', AsyncMock(side_effect=mock_get_user)):
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
async def test_create_user_chat(db: AsyncSession):
    """Test creating a CHAT user."""
    # Create user data for CHAT user (replacing API with CHAT)
    user_data = UserCreate(
        username="newchatuser",
        password="chatpassword",
        is_active=True,
        is_superuser=True,
        user_type=UserType.CHAT
    )
    
    # Create the user
    user = await create_user(db, user_data)
    
    # Verify user was created
    assert user.username == "newchatuser"
    assert user.is_active is True
    assert user.is_superuser is True
    assert user.user_type == UserType.CHAT
    
    # Verify password was hashed
    assert user.hashed_password != "chatpassword"
    assert verify_password("chatpassword", user.hashed_password)


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
    # Create a test user with CHAT type (replacing API with CHAT)
    test_user = User(
        username="updatefieldsuser",
        hashed_password=get_password_hash("password"),
        is_active=True,
        is_superuser=False,
        user_type=UserType.CHAT
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