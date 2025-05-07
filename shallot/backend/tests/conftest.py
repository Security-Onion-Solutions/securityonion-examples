"""Test fixtures for the backend."""
import pytest
import os
import sys
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from tests.utils import VALID_TEST_KEY, await_mock, setup_mock_db
from cryptography.fernet import Fernet
import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from typing import Dict, Generator, AsyncGenerator

# Ensure the src directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Set the encryption key environment variable before any imports
os.environ['ENCRYPTION_KEY'] = VALID_TEST_KEY
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///file:memdb_test?mode=memory&cache=shared'

# Import after setting environment variables
from app.database import Base, get_db
from app.config import settings
from app.models.users import User
from app.models.chat_users import ChatUser, ChatUserRole, ChatService
from app.models.settings import Settings as SettingsModel
from app.schemas.users import UserCreate, Token, UserType
from app.core.security import create_access_token

# Create test database engine
test_engine = create_async_engine(
    'sqlite+aiosqlite:///file:memdb_test?mode=memory&cache=shared',
    pool_pre_ping=True,
    echo=False,
)

# Create test session factory
TestingSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

#
# Core Testing Fixtures 
#

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """Set up the test database."""
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Drop all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db():
    """Get a test database session."""
    async with TestingSessionLocal() as session:
        # Start a transaction
        async with session.begin():
            # Use nested transaction for tests
            try:
                yield session
                # The transaction will be committed when the session.begin() context exits
            except Exception:
                # Rollback happens automatically on exception in the session.begin() context
                raise

@pytest.fixture
def override_get_db():
    """Override the get_db dependency."""
    async def _override_get_db():
        async with TestingSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    return _override_get_db

@pytest.fixture(scope="session", autouse=True)
def mock_encryption_key():
    """
    Automatically mock the encryption key for all tests.
    
    This ensures that all tests use a valid Fernet key instead of the default
    development key, which is not a valid Fernet key.
    """
    # We need to patch both possible import paths
    with patch('app.config.settings.ENCRYPTION_KEY', VALID_TEST_KEY), \
         patch('app.core.security.settings.ENCRYPTION_KEY', VALID_TEST_KEY):
        yield

#
# Database Test Helpers
#

@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return setup_mock_db()

@pytest.fixture
def mock_query_result():
    """Create a mock query result object."""
    result = MagicMock()
    
    # Configure scalar methods to be awaitable
    result.scalar.return_value = await_mock(None)
    result.scalar_one.return_value = await_mock(None)
    result.scalar_one_or_none.return_value = await_mock(None)
    
    # Configure collections methods
    scalars_result = MagicMock()
    scalars_result.all.return_value = []  # Default to empty list
    result.scalars.return_value = await_mock(scalars_result)
    
    return result

@pytest.fixture
def configure_db_execute(mock_db_session, mock_query_result):
    """Helper function to configure db.execute's return value."""
    def _configure(return_value=None):
        """Configure the mock_db_session.execute method.
        
        Args:
            return_value: The value to return from the query result's scalar methods.
                          If None, it will use the default mock_query_result.
        """
        if return_value is not None:
            mock_query_result.scalar.return_value = await_mock(return_value)
            mock_query_result.scalar_one.return_value = await_mock(return_value)
            mock_query_result.scalar_one_or_none.return_value = await_mock(return_value)
            
            # Configure collection results if appropriate
            if isinstance(return_value, list):
                scalars_result = MagicMock()
                scalars_result.all.return_value = return_value
                mock_query_result.scalars.return_value = await_mock(scalars_result)
        
        async def mock_execute(*args, **kwargs):
            return mock_query_result
            
        mock_db_session.execute = mock_execute
        return mock_db_session, mock_query_result
    
    return _configure

#
# Authentication Test Fixtures
#

@pytest.fixture
async def test_user(db: AsyncSession) -> User:
    """Create a test user for authentication tests."""
    # Check if user already exists
    from app.services.users import get_user_by_username
    
    existing_user = await get_user_by_username(db, "testuser")
    if existing_user:
        return existing_user
    
    # Create new user
    from app.services.users import create_user
    
    user_create = UserCreate(
        username="testuser",
        password="password123",
        is_active=True,
        is_superuser=True,
        user_type=UserType.WEB
    )
    
    user = await create_user(db, user_create)
    return user

@pytest.fixture
def test_token(test_user: User) -> str:
    """Create a test JWT token for authentication tests."""
    from datetime import timedelta
    
    access_token = create_access_token(
        subject=test_user.username,
        expires_delta=timedelta(minutes=30),
        is_superuser=test_user.is_superuser
    )
    return access_token

@pytest.fixture
def auth_headers(test_token: str) -> Dict[str, str]:
    """Create authorization headers with test token."""
    return {"Authorization": f"Bearer {test_token}"}

#
# Chat User Test Fixtures
#

@pytest.fixture
async def test_chat_user(db: AsyncSession) -> ChatUser:
    """Create a test chat user."""
    from app.services.chat_users import get_chat_user_by_platform_id, create_chat_user
    
    # Check if user already exists
    existing_user = await get_chat_user_by_platform_id(db, "test_platform_id", ChatService.DISCORD)
    if existing_user:
        return existing_user
    
    # Create new chat user
    chat_user = await create_chat_user(
        db=db,
        platform_id="test_platform_id",
        username="test_chat_user",
        platform=ChatService.DISCORD,
        role=ChatUserRole.ADMIN,
        display_name="Test Chat User"
    )
    
    return chat_user

#
# API Test Fixtures
#

@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI test app with overridden dependencies."""
    from app.main import app
    from fastapi.testclient import TestClient
    
    # Store the original get_db dependency
    original_get_db = app.dependency_overrides.get(get_db)
    
    # Override the get_db dependency for testing
    async def override_get_db():
        async with TestingSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield app
    
    # Restore the original get_db dependency
    if original_get_db:
        app.dependency_overrides[get_db] = original_get_db
    else:
        app.dependency_overrides.pop(get_db, None)

@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
def authenticated_client(client: TestClient, auth_headers: Dict[str, str]) -> TestClient:
    """Create an authenticated test client."""
    client.headers.update(auth_headers)
    return client

#
# Settings Test Fixtures
#

@pytest.fixture
async def test_setting(db: AsyncSession) -> SettingsModel:
    """Create a test setting."""
    from app.services.settings import get_setting, create_setting
    from app.schemas.settings import SettingCreate
    
    # Check if setting already exists
    existing_setting = await get_setting(db, "TEST_SETTING")
    if existing_setting:
        return existing_setting
    
    # Create new setting
    setting_create = SettingCreate(
        key="TEST_SETTING",
        value="test_value",
        description="Test setting for testing purposes"
    )
    
    setting = await create_setting(db, setting_create)
    return setting