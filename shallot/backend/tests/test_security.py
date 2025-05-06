"""Tests for security module."""
import pytest
import time
from datetime import datetime, timedelta
from jose import jwt
from unittest.mock import patch

from app.core.security import (
    verify_password, 
    get_password_hash, 
    create_access_token, 
    encrypt_value, 
    decrypt_value, 
    generate_key,
    ALGORITHM
)
from app.config import settings


def test_password_hashing():
    """Test password hashing and verification."""
    # Test password hashing
    password = "supersecret"
    hashed = get_password_hash(password)
    
    # Verify that hashed != original password
    assert hashed != password
    
    # Verify that the hash verification works
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_access_token_creation():
    """Test JWT token creation."""
    # Test token with default expiration
    token = create_access_token("testuser")
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    
    assert payload["sub"] == "testuser"
    assert payload["is_superuser"] is False
    assert "exp" in payload
    
    # Test token with custom expiration
    expires = timedelta(minutes=10)
    token = create_access_token("testuser", expires_delta=expires)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    
    assert payload["sub"] == "testuser"
    
    # Test superuser flag
    token = create_access_token("adminuser", is_superuser=True)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    
    assert payload["is_superuser"] is True


def test_token_expiration():
    """Test JWT token expiration."""
    # Create a token that expires in 1 second
    expires = timedelta(seconds=1)
    token = create_access_token("testuser", expires_delta=expires)
    
    # Verify it's valid initially
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "testuser"
    
    # Wait for it to expire
    time.sleep(2)
    
    # Verify it's expired
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def test_encryption():
    """Test Fernet encryption and decryption."""
    # Encryption and decryption should be reversible
    original = "sensitive_data"
    encrypted = encrypt_value(original)
    
    # Encrypted should be different than original
    assert encrypted != original
    
    # Decrypted should match original
    decrypted = decrypt_value(encrypted)
    assert decrypted == original
    
    # Verify different values produce different encrypted results
    other_encrypted = encrypt_value("different_data")
    assert other_encrypted != encrypted


def test_key_generation():
    """Test Fernet key generation."""
    # Generate a key
    key = generate_key()
    
    # Key should be a non-empty string
    assert isinstance(key, str)
    assert len(key) > 0
    
    # Generate another key - should be different
    another_key = generate_key()
    assert another_key != key


@patch('app.core.security.settings')
def test_fernet_initialization_error(mock_settings):
    """Test handling of invalid encryption key."""
    import importlib
    import sys
    from .utils import VALID_TEST_KEY
    
    # Save original key
    original_key = settings.ENCRYPTION_KEY
    
    # Test with invalid key
    mock_settings.ENCRYPTION_KEY = "invalid_key"
    
    # Remove security module from sys.modules to force reload
    if 'app.core.security' in sys.modules:
        del sys.modules['app.core.security']
    
    # Attempt to import the module again, which should raise an exception
    with pytest.raises(Exception):
        importlib.import_module('app.core.security')
    
    # Test with valid key
    mock_settings.ENCRYPTION_KEY = VALID_TEST_KEY
    
    # Remove security module from sys.modules to force reload
    if 'app.core.security' in sys.modules:
        del sys.modules['app.core.security']
    
    # This should not raise an exception
    importlib.import_module('app.core.security')
    
    # Reset the mock settings
    mock_settings.ENCRYPTION_KEY = original_key