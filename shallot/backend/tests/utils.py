"""Test utilities for the backend."""
from cryptography.fernet import Fernet

# Generate a valid Fernet key for tests
VALID_TEST_KEY = Fernet.generate_key().decode()