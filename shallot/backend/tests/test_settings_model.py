"""Tests for Settings model."""
import pytest
import time
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.models.settings import Settings
from app.core.security import encrypt_value, decrypt_value


def test_settings_model_init():
    """Test initializing a Settings model."""
    # Create a settings object
    settings = Settings(
        key="TEST_KEY", 
        encrypted_value="encrypted_value",
        description="Test description"
    )
    
    # Verify attributes
    assert settings.key == "TEST_KEY"
    assert settings.encrypted_value == "encrypted_value"
    assert settings.description == "Test description"
    assert settings.updated_at is not None  # Should be set automatically


def test_settings_model_updated_at():
    """Test updated_at is set correctly."""
    # Get current timestamp
    before = int(datetime.now().timestamp())
    
    # Create a settings object
    settings = Settings(
        key="TEST_KEY", 
        encrypted_value="encrypted_value",
        description="Test description"
    )
    
    # Get timestamp after creation
    after = int(datetime.now().timestamp())
    
    # Verify updated_at is between before and after timestamps
    assert settings.updated_at >= before
    assert settings.updated_at <= after


def test_value_getter():
    """Test the value property getter."""
    # Mock decrypt_value
    original_value = "test_value"
    encrypted_value = "encrypted_test_value"
    
    with patch('app.models.settings.decrypt_value', return_value=original_value) as mock_decrypt:
        # Create a settings object with encrypted value
        settings = Settings(
            key="TEST_KEY", 
            encrypted_value=encrypted_value,
            description="Test description"
        )
        
        # Get the value
        value = settings.value
        
        # Verify value was decrypted
        assert value == original_value
        mock_decrypt.assert_called_once_with(encrypted_value)


def test_value_getter_empty():
    """Test the value property getter with empty value."""
    # Create a settings object with empty encrypted value
    settings = Settings(
        key="TEST_KEY", 
        encrypted_value="",
        description="Test description"
    )
    
    # Get the value
    value = settings.value
    
    # Verify empty string is returned without decryption
    assert value == ""


def test_value_getter_error():
    """Test the value property getter with decryption error."""
    # Mock decrypt_value to raise exception
    with patch('app.models.settings.decrypt_value', side_effect=Exception("Test error")) as mock_decrypt, \
         pytest.raises(Exception) as exc_info:
        # Create a settings object
        settings = Settings(
            key="TEST_KEY", 
            encrypted_value="encrypted_value",
            description="Test description"
        )
        
        # Attempt to get value - should raise exception
        _ = settings.value
    
    # Verify exception was raised
    assert "Test error" in str(exc_info.value)


def test_value_setter():
    """Test the value property setter."""
    # Mock encrypt_value
    original_value = "test_value"
    encrypted_value = "encrypted_test_value"
    
    with patch('app.models.settings.encrypt_value', return_value=encrypted_value) as mock_encrypt:
        # Create a settings object
        settings = Settings(key="TEST_KEY", description="Test description")
        
        # Set the value
        settings.value = original_value
        
        # Verify value was encrypted and saved
        assert settings.encrypted_value == encrypted_value
        mock_encrypt.assert_called_once_with(original_value)


def test_value_setter_none():
    """Test the value property setter with None value."""
    # Create a settings object
    settings = Settings(key="TEST_KEY", description="Test description")
    
    # Set the value to None
    settings.value = None
    
    # Verify empty string is set
    assert settings.encrypted_value == ""


def test_value_setter_error():
    """Test the value property setter with encryption error."""
    # Mock encrypt_value to raise exception
    with patch('app.models.settings.encrypt_value', side_effect=Exception("Test error")) as mock_encrypt, \
         pytest.raises(Exception) as exc_info:
        # Create a settings object
        settings = Settings(key="TEST_KEY", description="Test description")
        
        # Attempt to set value - should raise exception
        settings.value = "test_value"
    
    # Verify exception was raised
    assert "Test error" in str(exc_info.value)


def test_settings_repr():
    """Test the __repr__ method."""
    # Create a settings object
    settings = Settings(
        key="TEST_KEY", 
        encrypted_value="encrypted_value",
        description="Test description",
        updated_at=1620000000
    )
    
    # Verify the string representation
    assert repr(settings) == "<Settings key=TEST_KEY updated_at=1620000000>"


def test_encryption_integration():
    """Test integration with actual encryption/decryption functions."""
    # Create a settings object
    settings = Settings(key="INTEGRATION_TEST", description="Integration test")
    
    # Test a simple value
    settings.value = "simple value"
    assert settings.value == "simple value"
    
    # Test a more complex value
    complex_value = '{"key": "value", "nested": {"list": [1, 2, 3]}}'
    settings.value = complex_value
    assert settings.value == complex_value
    
    # Test empty value
    settings.value = ""
    assert settings.value == ""