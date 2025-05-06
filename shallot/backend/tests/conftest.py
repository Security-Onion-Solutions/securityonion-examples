"""Test fixtures for the backend."""
import pytest
from unittest.mock import patch
from tests.utils import VALID_TEST_KEY


@pytest.fixture(autouse=True)
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