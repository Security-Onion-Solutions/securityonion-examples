import pytest
from datetime import datetime, timedelta
import json
from urllib.parse import parse_qs, urlparse
from src.services.alerts import AlertsService
from src.services.base import BaseSecurityOnionClient

def test_get_alerts_with_valid_json_message(app, mock_responses):
    """Test alert parsing with valid JSON message containing observer field."""
    with app.app_context():
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
        service = AlertsService(client)
        
        # Calculate expected time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        date_range = f"{start_time.strftime('%Y/%m/%d %I:%M:%S %p')} - {end_time.strftime('%Y/%m/%d %I:%M:%S %p')}"
        
        # Mock successful API response with message containing valid JSON and observer field
        mock_responses.get(
            "https://mock-so-api/connect/events/",
            json={
                "events": [{
                    "_id": "test-alert-1",
                    "_source": {
                        "@timestamp": "2024-01-01T00:00:00Z",
                        "title": "Test Alert",
                        "description": "Test Description",
                        "severity": "high",
                        "message": '{"observer": {"name": "test-sensor", "ip": "192.168.1.1"}}'
                    }
                }]
            },
            status=200,
            match_querystring=False
        )
        
        # Get alerts
        alerts = service.get_alerts()
        
        # Verify response 
        assert len(alerts) == 1
        assert alerts[0]["_id"] == "test-alert-1"
        assert alerts[0]["_source"]["title"] == "Test Alert"

def test_get_alerts_with_invalid_json_message(app, mock_responses):
    """Test alert parsing with invalid JSON message."""
    with app.app_context():
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
        service = AlertsService(client)
        
        # Calculate expected time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        date_range = f"{start_time.strftime('%Y/%m/%d %I:%M:%S %p')} - {end_time.strftime('%Y/%m/%d %I:%M:%S %p')}"
        
        # Mock successful API response with message containing invalid JSON
        mock_responses.get(
            "https://mock-so-api/connect/events/",
            json={
                "events": [{
                    "_id": "test-alert-2",
                    "_source": {
                        "@timestamp": "2024-01-01T00:00:00Z",
                        "title": "Test Alert",
                        "description": "Test Description",
                        "severity": "high",
                        "message": "This is not valid JSON {{"
                    }
                }]
            },
            status=200,
            match_querystring=False
        )
        
        # Get alerts
        alerts = service.get_alerts()
        
        # Verify response processed successfully despite invalid JSON
        assert len(alerts) == 1
        assert alerts[0]["_id"] == "test-alert-2"
        assert alerts[0]["_source"]["title"] == "Test Alert"