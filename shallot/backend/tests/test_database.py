"""Tests for database module."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, call, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine

from app.database import (
    engine,
    AsyncSessionLocal,
    Base,
    get_db,
    init_db,
    close_db
)


@pytest.fixture

def await_mock(return_value):
    """Helper function to make mock return values awaitable in Python 3.13."""
    async def _awaitable():
        return return_value
    return _awaitable()

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
        # Mock session context manager
        mock_session_local.return_value.__aenter__.return_value = mock_session
        
        # Test exception handling
        with pytest.raises(ValueError):
            async for session in get_db():
                # Verify session is yielded
                assert session == mock_session
                # Simulate exception
                raise ValueError("Test exception")
                
        # Verify session was rolled back and closed
        mock_session.commit.assert_not_called()
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_init_db(mock_engine):
    """Test init_db function."""
    with patch("app.database.engine", mock_engine), \
         patch("app.database.Base") as mock_base, \
         patch("app.database.text") as mock_text:
        # Mock Base.metadata.create_all
        mock_base.metadata.create_all = MagicMock()
        
        # Mock query execution
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("users",), ("settings",)]
        mock_engine.execute.return_value = mock_result

        mock_engine.execute.return_value = await_mock(mock_engine.execute.return_value)

        mock_engine.execute.return_value = await_mock(mock_engine.execute.return_value)


        mock_engine.execute.return_value = await_mock(mock_engine.execute.return_value)
        
        # Mock text function
        mock_text.return_value = "SELECT name FROM sqlite_master WHERE type='table';"
        
        # Initialize database
        await init_db()
        
        # Verify tables were created
        mock_engine.begin.assert_called_once()
        mock_engine.run_sync.assert_called_once_with(mock_base.metadata.create_all)
        mock_engine.execute.assert_called_once_with(mock_text.return_value)


@pytest.mark.asyncio
async def test_init_db_error(mock_engine):
    """Test init_db function with error."""
    with patch("app.database.engine", mock_engine), \
         patch("app.database.Base") as mock_base:
        # Mock Base.metadata.create_all to raise exception
        mock_base.metadata.create_all = MagicMock()
        mock_engine.run_sync.side_effect = Exception("Database error")
        
        # Initialize database with error
        with pytest.raises(Exception) as exc_info:
            await init_db()
        
        # Verify exception was raised and not caught
        assert "Database error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_close_db(mock_engine):
    """Test close_db function."""
    with patch("app.database.engine", mock_engine):
        # Close database
        await close_db()
        
        # Verify engine was disposed
        mock_engine.dispose.assert_called_once()


def test_engine_configuration():
    """Test engine configuration."""
    # Check engine is configured with expected parameters
    assert engine.dialect.name == "sqlite"  # Assuming SQLite for testing
    
    # Verify pool parameters
    assert engine.pool._pre_ping is True