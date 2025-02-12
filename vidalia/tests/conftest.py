import os
import pytest
import responses

# Set test environment variables before importing app code
os.environ.clear()
os.environ['FLASK_ENV'] = 'testing'
os.environ['ENV_FILE'] = '.env.test'

# Now import app code after environment is configured
from flask import Flask
from src.app import create_app
from src.config import Config

@pytest.fixture
def app():
    """Create and configure a test Flask application instance."""
    app = create_app()
    
    # Verify test configuration was loaded
    assert app.config['SO_API_URL'] == 'https://mock-so-api'
    assert app.config['SO_CLIENT_ID'] == 'test_client_id'
    assert app.config['SO_CLIENT_SECRET'] == 'test_client_secret'
    
    # Return test app
    return app

@pytest.fixture
def api_client(app):
    """Create API client with test configuration."""
    from src.services.so_api import SecurityOnionAPI
    client = SecurityOnionAPI(
        base_url=app.config['SO_API_URL'],
        client_id=app.config['SO_CLIENT_ID'],
        client_secret=app.config['SO_CLIENT_SECRET']
    )
    app.so_api = client
    return client

@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create a test CLI runner for Flask CLI commands."""
    return app.test_cli_runner()

@pytest.fixture
def mock_responses():
    """Fixture to provide responses library for mocking API calls."""
    with responses.RequestsMock() as rsps:
        yield rsps

@pytest.fixture
def sample_alert():
    """Fixture providing a sample alert data structure."""
    return {
        "id": "test-alert-1",
        "title": "Test Alert",
        "description": "Test alert description",
        "severity": "high",
        "status": "new",
        "created": "2023-01-01T00:00:00Z"
    }

@pytest.fixture
def sample_case():
    """Fixture providing a sample case data structure."""
    return {
        "id": "test-case-1",
        "title": "Test Case",
        "description": "Test case description",
        "status": "open",
        "created": "2023-01-01T00:00:00Z",
        "alerts": []
    }

@pytest.fixture
def sample_grid_data():
    """Fixture providing sample grid data."""
    return {
        "id": "test-grid-1",
        "title": "Test Grid",
        "data": [
            {"column1": "value1", "column2": "value2"},
            {"column1": "value3", "column2": "value4"}
        ]
    }
