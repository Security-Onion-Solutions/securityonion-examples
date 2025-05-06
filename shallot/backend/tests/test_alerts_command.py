"""Tests for alerts command."""
import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
import httpx

from app.api.commands.alerts import process
from app.models.chat_users import ChatService, ChatUserRole
from app.core.securityonion import SecurityOnionClient


@pytest.fixture
def mock_so_client():
    """Create a mock Security Onion client."""
    client = MagicMock(spec=SecurityOnionClient)
    client._connected = True
    client._base_url = "https://securityonion.example.com/"
    client._get_headers.return_value = {"Authorization": "Bearer test_token"}
    client._client = AsyncMock(spec=httpx.AsyncClient)
    
    # Default to successful response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = "{}"
    mock_response.json.return_value = {"events": []}
    client._client.get.return_value = mock_response
    
    return client


@pytest.mark.asyncio
async def test_alerts_command_no_connection():
    """Test alerts command with no Security Onion connection."""
    with patch("app.api.commands.alerts.client") as mock_client:
        # Set client as not connected
        mock_client._connected = False
        
        # Test command
        result = await process("!alerts", "discord", "user123", "testuser")
        
        # Verify error message
        assert "Error: Not connected to Security Onion" in result


@pytest.mark.asyncio
async def test_alerts_command_with_alerts(mock_so_client):
    """Test alerts command with alerts."""
    with patch("app.api.commands.alerts.client", mock_so_client):
        # Mock response with alerts
        alert_data = {
            "events": [
                {
                    "@timestamp": "2025-01-01T12:00:00Z",
                    "payload": {
                        "message": json.dumps({
                            "alert": {
                                "signature": "Test Alert 1",
                                "signature_id": "1000001"
                            },
                            "src_ip": "192.168.1.1",
                            "src_port": 12345,
                            "dest_ip": "10.0.0.1",
                            "dest_port": 80
                        }),
                        "event.severity_label": "HIGH",
                        "log.id.uid": "alert1",
                        "observer.name": "sensor1"
                    }
                },
                {
                    "@timestamp": "2025-01-01T11:00:00Z",
                    "payload": {
                        "message": json.dumps({
                            "alert": {
                                "signature": "Test Alert 2",
                                "signature_id": "1000002"
                            },
                            "src_ip": "192.168.1.2",
                            "src_port": 54321,
                            "dest_ip": "10.0.0.2",
                            "dest_port": 443
                        }),
                        "event.severity_label": "MEDIUM",
                        "log.id.uid": "alert2",
                        "observer.name": "sensor2"
                    }
                }
            ],
            "totalEvents": 2
        }
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps(alert_data)
        mock_response.json.return_value = alert_data
        mock_so_client._client.get.return_value = mock_response
        
        # Test command
        result = await process("!alerts", "discord", "user123", "testuser")
        
        # Verify response contains alert data
        assert "Here are the newest 5 alerts:" in result
        assert "[HIGH] - Test Alert 1" in result
        assert "ruleid: 1000001" in result
        assert "eventid: alert1" in result
        assert "source: 192.168.1.1:12345" in result
        assert "destination: 10.0.0.1:80" in result
        assert "observer.name: sensor1" in result
        
        assert "[MEDIUM] - Test Alert 2" in result
        assert "ruleid: 1000002" in result
        assert "eventid: alert2" in result
        assert "source: 192.168.1.2:54321" in result
        assert "destination: 10.0.0.2:443" in result
        assert "observer.name: sensor2" in result
        
        # Verify API call was made with correct parameters
        mock_so_client._client.get.assert_called_once()
        call_args = mock_so_client._client.get.call_args[1]
        assert call_args["headers"] == {"Authorization": "Bearer test_token"}
        assert "connect/events" in call_args["url"]
        assert "query" in call_args["params"]
        assert "range" in call_args["params"]
        assert "tags:alert" in call_args["params"]["query"]
        assert "NOT event.acknowledged:true" in call_args["params"]["query"]


@pytest.mark.asyncio
async def test_alerts_command_no_alerts(mock_so_client):
    """Test alerts command with no alerts."""
    with patch("app.api.commands.alerts.client", mock_so_client):
        # Mock response with no alerts
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = '{"events": [], "totalEvents": 0}'
        mock_response.json.return_value = {"events": [], "totalEvents": 0}
        mock_so_client._client.get.return_value = mock_response
        
        # Test command
        result = await process("!alerts", "discord", "user123", "testuser")
        
        # Verify response
        assert "No alerts found in the last 24 hours" in result
        assert "Total events: 0" in result


@pytest.mark.asyncio
async def test_alerts_command_api_error(mock_so_client):
    """Test alerts command with API error."""
    with patch("app.api.commands.alerts.client", mock_so_client):
        # Mock API error
        mock_so_client._client.get.side_effect = httpx.HTTPError("Connection failed")
        
        # Test command
        result = await process("!alerts", "discord", "user123", "testuser")
        
        # Verify error message
        assert "Error: Failed to connect to Security Onion API" in result
        assert "Connection failed" in result


@pytest.mark.asyncio
async def test_alerts_command_malformed_response(mock_so_client):
    """Test alerts command with malformed API response."""
    with patch("app.api.commands.alerts.client", mock_so_client):
        # Mock malformed response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "Not JSON"
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "Not JSON", 0)
        mock_so_client._client.get.return_value = mock_response
        
        # Test command
        result = await process("!alerts", "discord", "user123", "testuser")
        
        # Verify error message
        assert "Error: Could not establish connection with Security Onion API" in result


@pytest.mark.asyncio
async def test_alerts_command_invalid_alert_data(mock_so_client):
    """Test alerts command with invalid alert data."""
    with patch("app.api.commands.alerts.client", mock_so_client):
        # Mock response with invalid alert data
        alert_data = {
            "events": [
                {
                    "@timestamp": "2025-01-01T12:00:00Z",
                    "payload": {
                        "message": "Not JSON", # Invalid message format
                        "event.severity_label": "HIGH",
                        "log.id.uid": "alert1",
                        "observer.name": "sensor1"
                    }
                }
            ],
            "totalEvents": 1
        }
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps(alert_data)
        mock_response.json.return_value = alert_data
        mock_so_client._client.get.return_value = mock_response
        
        # Test command - should handle invalid data gracefully
        result = await process("!alerts", "discord", "user123", "testuser")
        
        # Verify response
        assert "No alerts found in the last 24 hours" in result
        assert "Total events: 1" in result


@pytest.mark.asyncio
async def test_alerts_command_missing_alert_field(mock_so_client):
    """Test alerts command with missing alert field in response."""
    with patch("app.api.commands.alerts.client", mock_so_client):
        # Mock response with missing alert field
        alert_data = {
            "events": [
                {
                    "@timestamp": "2025-01-01T12:00:00Z",
                    "payload": {
                        "message": json.dumps({
                            # Missing "alert" field
                            "src_ip": "192.168.1.1",
                            "src_port": 12345,
                            "dest_ip": "10.0.0.1",
                            "dest_port": 80
                        }),
                        "event.severity_label": "HIGH",
                        "log.id.uid": "alert1",
                        "observer.name": "sensor1"
                    }
                }
            ],
            "totalEvents": 1
        }
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps(alert_data)
        mock_response.json.return_value = alert_data
        mock_so_client._client.get.return_value = mock_response
        
        # Test command - should handle missing alert field gracefully
        result = await process("!alerts", "discord", "user123", "testuser")
        
        # Verify response
        assert "No alerts found in the last 24 hours" in result
        assert "Total events: 1" in result