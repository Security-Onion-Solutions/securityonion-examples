"""Test fixtures for the backend."""
import pytest
import os
import sys
import asyncio
from unittest.mock import patch, AsyncMock
from tests.utils import VALID_TEST_KEY
from cryptography.fernet import Fernet
import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Ensure the src directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Set the encryption key environment variable before any imports
os.environ['ENCRYPTION_KEY'] = VALID_TEST_KEY
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///:memory:'

# Import after setting environment variables
from app.database import Base, get_db
from app.config import settings

# Create test database engine
test_engine = create_async_engine(
    'sqlite+aiosqlite:///:memory:',
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
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

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