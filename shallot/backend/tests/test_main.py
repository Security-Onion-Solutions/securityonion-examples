from fastapi.testclient import TestClient
import pytest
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test the root endpoint returns correct response."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Security Onion Chat Bot API"}


def test_health_check():
    """Test the health check endpoint returns correct response."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert "database" in data


@pytest.mark.asyncio
async def test_async_context():
    """Test that async context is properly set up."""
    assert True  # This test exists to verify pytest-asyncio is working
