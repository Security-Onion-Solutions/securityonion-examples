"""Test utilities for the backend."""
import base64
import os
from unittest.mock import AsyncMock, MagicMock
from cryptography.fernet import Fernet

# Generate a valid Fernet key for tests
# Ensure it's properly formatted as 32 url-safe base64-encoded bytes
VALID_TEST_KEY = Fernet.generate_key().decode()

# Function to generate a valid Fernet key
def generate_valid_fernet_key():
    """Generate a valid Fernet key for testing."""
    return Fernet.generate_key().decode()

# Function to validate if a key is a valid Fernet key
def is_valid_fernet_key(key):
    """Check if a key is a valid Fernet key."""
    try:
        Fernet(key.encode())
        return True
    except Exception:
        return False


def await_mock(return_value):
    """Helper function to make mock return values awaitable in Python 3.13.
    
    This function takes a return value and wraps it in a coroutine that can be awaited.
    Especially useful for tests in Python 3.13 where mocks need to be awaitable.
    
    Args:
        return_value: The value to be returned when the coroutine is awaited
        
    Returns:
        A coroutine that when awaited, returns the given return_value
    """
    async def _awaitable():
        return return_value
    return _awaitable()


def make_mock_awaitable(mock_obj, method_name, return_value=None):
    """Make a mock method's return value awaitable.
    
    Sets up a mock method to return an awaitable coroutine that resolves to the 
    provided return_value.
    
    Args:
        mock_obj: The mock object
        method_name: The name of the method to make awaitable
        return_value: The value to be returned when the coroutine is awaited.
                     If None, will use the current return_value of the method.
    """
    method = getattr(mock_obj, method_name)
    
    # If return_value is not provided, use the existing one
    if return_value is None:
        return_value = method.return_value
        
    # Set the return value
    method.return_value = return_value
    
    # Make it awaitable
    method.return_value = await_mock(return_value)


def setup_mock_db():
    """Set up a mock database with AsyncMock methods for testing.
    
    This is particularly helpful for Python 3.13 compatibility
    when we need to mock db.execute.return_value.
    
    Returns:
        A fully configured mock database session with AsyncMock methods.
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    
    # Create the mock
    db = MagicMock(spec=AsyncSession)
    
    # Add async methods
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.close = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.get = AsyncMock()
    
    # Special setup for execute
    db.execute = AsyncMock()
    
    return db


def create_mock_db_session():
    """Create a mock database session with proper awaitable return values.
    
    Use this function in all new tests to avoid asyncio coroutine errors in Python 3.13.
    
    Returns:
        db: A properly configured mock database session
        db_result: A configured result object ready to have its methods mocked
    """
    # Create the database session mock
    db = setup_mock_db()
    
    # Mock the execute method
    async def mock_execute(*args, **kwargs):
        # Return an awaitable result object
        result = MagicMock()
        return result
    
    # Replace the execute method with our custom implementation
    db.execute = mock_execute
    
    # Create a mock result that can be configured
    db_result = MagicMock()
    
    return db, db_result