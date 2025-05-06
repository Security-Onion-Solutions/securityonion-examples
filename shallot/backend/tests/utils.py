"""Test utilities for the backend."""
import base64
import os
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