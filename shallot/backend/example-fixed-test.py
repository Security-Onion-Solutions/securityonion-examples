"""Example of Python 3.13 compatible AsyncMock test."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

# Helper function for making return values awaitable in Python 3.13
def await_mock(return_value):
    """Helper function to make mock return values awaitable in Python 3.13."""
    async def _awaitable():
        return return_value
    return _awaitable()


# BEFORE: This fails in Python 3.13
@pytest.mark.asyncio
async def test_get_user_count_before(mock_db):
    """Test that fails in Python 3.13."""
    # Mock DB query result
    mock_result = AsyncMock()
    mock_result.scalar_one.return_value = 5
    mock_db.execute.return_value = mock_result
    
    # Test function
    count = await get_user_count(mock_db)
    
    # Verify - will fail with:
    # AssertionError: assert <coroutine object AsyncMockMixin._execute_mock_call at 0x7c294f701840> == 5
    assert count == 5
    mock_db.execute.assert_called_once()


# AFTER: This works in Python 3.13
@pytest.mark.asyncio
async def test_get_user_count_after(mock_db):
    """Test that works in Python 3.13."""
    # Mock DB query result
    mock_result = AsyncMock()
    mock_result.scalar_one.return_value = 5
    mock_result.scalar_one.return_value = await_mock(mock_result.scalar_one.return_value)
    mock_db.execute.return_value = mock_result
    mock_db.execute.return_value = await_mock(mock_db.execute.return_value)
    
    # Test function
    count = await get_user_count(mock_db)
    
    # Verify - now works correctly
    assert count == 5
    mock_db.execute.assert_called_once()


# BEFORE: This also fails in Python 3.13
@pytest.mark.asyncio
async def test_get_users_before(mock_db):
    """Another test that fails in Python 3.13."""
    # Mock DB query result
    mock_result = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_user]
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result
    
    # Test function
    users = await read_users(mock_db, mock_user)
    
    # Verify - will fail with coroutine errors
    assert len(users) == 1
    assert users[0] == mock_user
    mock_db.execute.assert_called_once()


# AFTER: This works in Python 3.13
@pytest.mark.asyncio
async def test_get_users_after(mock_db):
    """Test that works in Python 3.13."""
    # Mock DB query result
    mock_result = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_user]
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result
    mock_db.execute.return_value = await_mock(mock_db.execute.return_value)
    
    # Test function
    users = await read_users(mock_db, mock_user)
    
    # Verify - now works correctly
    assert len(users) == 1
    assert users[0] == mock_user
    mock_db.execute.assert_called_once()