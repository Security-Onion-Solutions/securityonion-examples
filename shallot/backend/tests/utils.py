"""Test utilities for the backend."""
import base64
import os
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Type
from unittest.mock import AsyncMock, MagicMock, patch

from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, Table
from sqlalchemy.sql.expression import Select, Insert, Update, Delete

# Generate a valid Fernet key for tests
# Ensure it's properly formatted as 32 url-safe base64-encoded bytes
VALID_TEST_KEY = Fernet.generate_key().decode()

#
# Cryptography Helpers
#

def generate_valid_fernet_key():
    """Generate a valid Fernet key for testing."""
    return Fernet.generate_key().decode()

def is_valid_fernet_key(key):
    """Check if a key is a valid Fernet key."""
    try:
        Fernet(key.encode())
        return True
    except Exception:
        return False

#
# Asyncio Testing Helpers
#

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

#
# Database Testing Helpers
#

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
    db.delete = AsyncMock()
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


def configure_mock_execute(db, query_type='select', entity=None, result=None):
    """Configure a mock db.execute method with appropriate result.
    
    Args:
        db: The mock database session
        query_type: Type of query ('select', 'insert', 'update', 'delete')
        entity: Entity class or table for insert operations
        result: For select queries, the object(s) to return
                For insert/update, the number of rows affected
    
    Returns:
        The configured db mock
    """
    # Create a mock result
    mock_result = MagicMock()
    
    if query_type == 'select':
        # For scalar results (single entity)
        if result is not None and not isinstance(result, list):
            mock_result.scalar.return_value = await_mock(result)
            mock_result.scalar_one.return_value = await_mock(result)
            mock_result.scalar_one_or_none.return_value = await_mock(result)
        
        # For multi-result collections
        if result is not None and isinstance(result, list):
            scalars_result = MagicMock()
            scalars_result.all.return_value = result
            scalars_result.first.return_value = result[0] if result else None
            mock_result.scalars.return_value = await_mock(scalars_result)
    
    elif query_type == 'insert':
        # Mock the lastrowid attribute
        mock_result.lastrowid = 1
        
    elif query_type in ('update', 'delete'):
        # Mock the rowcount attribute
        mock_result.rowcount = 1 if result is None else result
    
    # Configure the execute method
    async def mock_execute(*args, **kwargs):
        return mock_result
    
    db.execute = mock_execute
    return db, mock_result


def create_test_model_instance(model_class, **kwargs):
    """Create a test model instance with provided attributes.
    
    Args:
        model_class: The SQLAlchemy model class
        **kwargs: Attribute values for the model
        
    Returns:
        An instance of the model with the provided attributes
    """
    instance = model_class()
    for key, value in kwargs.items():
        setattr(instance, key, value)
    return instance

#
# Chat Command Helpers
#

def create_command_context(
    command: str, 
    args: Optional[List[str]] = None, 
    platform: str = "DISCORD", 
    platform_id: str = "test_user_id",
    username: str = "test_user",
    channel_id: str = "test_channel",
    is_direct_message: bool = False
) -> Dict[str, Any]:
    """Create a command context dictionary for testing command handlers.
    
    Args:
        command: The command name (without the ! prefix)
        args: Command arguments list
        platform: Chat platform (DISCORD, SLACK, MATRIX)
        platform_id: User ID in the platform
        username: Username in the platform
        channel_id: Channel ID
        is_direct_message: Whether this is a DM
        
    Returns:
        Command context dictionary
    """
    return {
        "command": command,
        "args": args or [],
        "platform": platform,
        "user": {
            "platform_id": platform_id,
            "username": username,
        },
        "channel_id": channel_id,
        "is_direct_message": is_direct_message,
        "timestamp": datetime.utcnow().isoformat(),
    }


def mock_chat_service_response():
    """Create a mock for chat service response handling.
    
    Returns:
        A configured mock for send_message/send_file/etc functions
    """
    # Create AsyncMock for response methods
    mock_response = MagicMock()
    mock_response.send_message = AsyncMock(return_value=True)
    mock_response.send_file = AsyncMock(return_value=True)
    mock_response.send_image = AsyncMock(return_value=True)
    
    return mock_response

#
# Authentication Test Helpers
#

def create_test_token(
    username: str = "testuser",
    is_superuser: bool = True,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a test JWT token without requiring a database user.
    
    Args:
        username: Username to include in the token
        is_superuser: Whether the user is a superuser
        expires_delta: Token expiry time delta
        
    Returns:
        JWT token string
    """
    from app.core.security import create_access_token
    
    return create_access_token(
        subject=username,
        expires_delta=expires_delta or timedelta(minutes=30),
        is_superuser=is_superuser
    )


def mock_current_user(
    user_id: int = 1,
    username: str = "testuser",
    is_active: bool = True,
    is_superuser: bool = True,
    user_type: str = "WEB"
) -> MagicMock:
    """Create a mock user for dependency injection.
    
    Args:
        user_id: User ID
        username: Username
        is_active: Whether the user is active
        is_superuser: Whether the user is a superuser
        user_type: User type (WEB, API, etc.)
        
    Returns:
        Mock User object
    """
    from app.models.users import User
    
    # Create a mock user
    mock_user = MagicMock(spec=User)
    mock_user.id = user_id
    mock_user.username = username
    mock_user.is_active = is_active
    mock_user.is_superuser = is_superuser
    mock_user.user_type = user_type
    mock_user.hashed_password = "hashed_password"  # Not used but may be referenced
    
    return mock_user