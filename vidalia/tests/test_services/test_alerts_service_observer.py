import pytest
import json
import logging
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse
from src.services.alerts import AlertsService
from src.services.base import BaseSecurityOnionClient

def test_get_alerts_with_observer_debug_logging(app, mock_responses, caplog):
    """Test debug logging for alert messages containing observer field."""
    with app.app_context():
        caplog.set_level(logging.DEBUG)
        
        # Create mock client
        client = BaseSecurityOnionClient(
            base_url="https://mock-so-api",
            client_id="test-client",
            client_secret="test-secret"
        )
        
        # Mock OAuth token endpoint
        mock_responses.post(
            "https://mock-so-api/oauth2/token",
            json={
                "access_token": "test-token",
                "token_type": "Bearer",
                "expires_in": 3600
            },
            status=200
        )
        
        # Sample alert with observer field in the message
        alert_data = {
            "events": [
                {
                    "_id": "test-alert-1",
                    "_source": {
                        "@timestamp": "2023-01-01T00:00:00Z",
                        "title": "Test Alert With Observer",
                        "description": "Test alert with observer field",
                        "severity": "high"
                    },
                    "payload": {
                        "message": '{"observer": {"name": "sensor1", "ip": "192.168.1.1", "type": "sensor"}}'
                    }
                }
            ]
        }
        
        # Mock the events endpoint
        mock_responses.get(
            "https://mock-so-api/connect/events/",
            json=alert_data,
            status=200,
            match_querystring=False
        )
        
        service = AlertsService(client)
        
        # Get alerts
        alerts = service.get_alerts()
        
        # Verify response was properly processed
        assert len(alerts) == 1
        assert alerts[0]["_source"]["title"] == "Test Alert With Observer"
        
        # Check that the observer debug log message was generated
        assert "Observer in message: " in caplog.text
        assert "sensor1" in caplog.text
        assert "192.168.1.1" in caplog.text