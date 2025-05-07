"""Tests for database module."""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock, call
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from tests.utils import await_mock, setup_mock_db

from app.database import (
    engine,
    AsyncSessionLocal,
    Base,
    get_db,
    init_db,
    close_db
)
from app.models.users import User
from app.models.settings import Settings as SettingsModel
from app.models.chat_users import ChatUser


@pytest.fixture
def mock_engine():
    """Create a mock SQLAlchemy engine."""
    mock = AsyncMock(spec=AsyncEngine)
    mock.begin.return_value.__aenter__.return_value = mock
    mock.run_sync = AsyncMock()
    mock.dispose = AsyncMock()
    return mock


@pytest.fixture
def mock_session():
    """Create a mock SQLAlchemy session."""
    mock = AsyncMock(spec=AsyncSession)
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_session_maker():
    """Create a mock SQLAlchemy session maker."""
    mock = MagicMock()
    return mock


@pytest.mark.asyncio
async def test_get_db(mock_session):
    """Test get_db dependency."""
    with patch("app.database.AsyncSessionLocal") as mock_session_local:
        # Mock session context manager
        mock_session_local.return_value.__aenter__.return_value = mock_session
        
        # Get database session using dependency
        async for session in get_db():
            # Verify session is yielded
            assert session == mock_session
            # Simulate successful operation
            pass
        
        # Verify session was committed and closed
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()
        mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_db_with_exception(mock_session):
    """Test get_db dependency with exception."""
    with patch("app.database.AsyncSessionLocal") as mock_session_local:
        # Create a context manager that will properly handle the exception
        ctx_manager = AsyncMock()
        ctx_manager.__aenter__.return_value = mock_session
        mock_session_local.return_value = ctx_manager
        
        # Create proper async mock methods that will be awaited
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        
        # Test the exception handling path
        try:
            # Start the generator
            db_gen = get_db()
            # Get the yielded session
            session = await anext(db_gen)
            # Verify we got the expected session
            assert session is mock_session
            
            # Raise an exception to trigger error handling in generator
            try:
                with pytest.raises(ValueError):
                    await db_gen.athrow(ValueError, ValueError("Test exception"))
            except StopAsyncIteration:
                # This is expected as generator will complete after the exception
                pass
            
            # Verify rollback was called but not commit
            mock_session.commit.assert_not_called()
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()
        except Exception as e:
            pytest.fail(f"Unexpected exception: {e}")


@pytest.mark.asyncio
async def test_init_db():
    """Test init_db function."""
    # Create a mock connection
    mock_conn = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [('users',), ('settings',)]
    
    # In Python 3.13, we need to handle async calls differently
    async def mock_execute(*args, **kwargs):
        return mock_result
    
    mock_conn.execute = AsyncMock(side_effect=mock_execute)
    
    # Create a mock engine
    mock_eng = AsyncMock(spec=AsyncEngine)
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_conn
    mock_eng.begin.return_value = mock_context
    
    # Mock dependencies
    with patch("app.database.engine", mock_eng), \
         patch("app.database.Base") as mock_base, \
         patch("app.database.text") as mock_text:
        
        # Mock Base.metadata.create_all
        mock_base.metadata.create_all = MagicMock()
        
        # Mock text function
        mock_text.return_value = "SELECT name FROM sqlite_master WHERE type='table';"
        
        # Initialize database
        await init_db()
        
        # Verify tables were created
        mock_eng.begin.assert_called_once()
        mock_conn.run_sync.assert_called_once_with(mock_base.metadata.create_all)
        mock_conn.execute.assert_called_once_with(mock_text.return_value)
        assert mock_result.fetchall.call_count == 1


@pytest.mark.asyncio
async def test_init_db_error():
    """Test init_db function with error."""
    # Create a mock engine that raises exception
    mock_eng = AsyncMock(spec=AsyncEngine)
    mock_eng.begin.side_effect = SQLAlchemyError("Database error")
    
    # Mock dependencies and print
    with patch("app.database.engine", mock_eng), \
         patch("builtins.print") as mock_print:
        
        # Initialize database with error
        with pytest.raises(SQLAlchemyError) as exc_info:
            await init_db()
        
        # Verify exception was raised and error printed
        assert "Database error" in str(exc_info.value)
        mock_print.assert_called_with("Error creating database tables: Database error")


@pytest.mark.asyncio
async def test_close_db():
    """Test close_db function."""
    # Create mock engine
    mock_eng = AsyncMock(spec=AsyncEngine)
    mock_eng.dispose = AsyncMock()
    
    with patch("app.database.engine", mock_eng):
        # Close database
        await close_db()
        
        # Verify engine was disposed
        mock_eng.dispose.assert_called_once()


def test_engine_configuration():
    """Test engine configuration."""
    # Check engine is configured with expected parameters
    assert engine.dialect.name == "sqlite"  # SQLite for tests
    
    # Verify pool parameters
    assert engine.pool._pre_ping is True
    assert engine.echo is False  # Debug mode is off


@pytest.mark.asyncio
async def test_db_real_connection(db):
    """Test real database connection with SQLite."""
    # This test uses the actual in-memory test database (db fixture)
    
    # Create a test user
    test_user = User(
        username="db_test_user",
        hashed_password="hashed_pw_for_test",
        is_active=True,
        is_superuser=False,
        user_type="WEB"
    )
    
    # Add the user to the database
    db.add(test_user)
    await db.commit()
    
    # Fetch the user back
    result = await db.execute(
        select(User).where(User.username == "db_test_user")
    )
    user = result.scalar_one_or_none()
    
    # Verify user was stored correctly
    assert user is not None
    assert user.username == "db_test_user"
    assert user.hashed_password == "hashed_pw_for_test"
    assert user.is_active is True
    assert user.is_superuser is False
    assert user.user_type == "WEB"
    
    # Cleanup - delete the test user
    await db.delete(user)
    await db.commit()


@pytest.mark.asyncio
async def test_table_relationships(db):
    """Test relationships between tables."""
    # Create a test setting
    test_setting = SettingsModel(
        key="TEST_RELATIONSHIP_KEY",
        value="test_value",
        description="Test setting for relationship testing"
    )
    
    # Add the setting to the database
    db.add(test_setting)
    await db.commit()
    await db.refresh(test_setting)
    
    # Fetch setting by key
    result = await db.execute(
        select(SettingsModel).where(SettingsModel.key == "TEST_RELATIONSHIP_KEY")
    )
    setting = result.scalar_one_or_none()
    
    # Verify setting was retrieved correctly
    assert setting is not None
    assert setting.key == "TEST_RELATIONSHIP_KEY"
    assert setting.value == "test_value"
    
    # Cleanup - delete the test setting
    await db.delete(setting)
    await db.commit()