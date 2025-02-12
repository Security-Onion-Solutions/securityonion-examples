import pytest
from datetime import datetime, timedelta
import json
from urllib.parse import parse_qs, urlparse
from src.services.alerts import AlertsService
from src.services.base import BaseSecurityOnionClient

def test_get_alerts(app, mock_responses):
    """Test retrieving alerts list."""
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
        
        # Mock successful API response
        def url_matcher(request):
            url = urlparse(request.url)
            params = parse_qs(url.query)
            return (
                'query' in params and params['query'][0] == 'tags:alert',
                'query parameter missing or incorrect'
            )

        mock_responses.get(
            "https://mock-so-api/connect/events/",
            match=[url_matcher],
            json={
                "events": [{
                    "_id": "test-alert-1",
                    "_source": {
                        "@timestamp": "2024-01-01T00:00:00Z",
                        "title": "Test Alert",
                        "description": "Test Description",
                        "severity": "high"
                    }
                }]
            },
            status=200
        )
        
        # Get alerts
        alerts = service.get_alerts()
        
        # Verify response
        assert len(alerts) == 1
        assert alerts[0]["_id"] == "test-alert-1"
        assert alerts[0]["_source"]["title"] == "Test Alert"

def test_get_alerts_api_error(app, mock_responses):
    """Test error handling when API request fails."""
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
        
        # Mock API error
        def url_matcher(request):
            url = urlparse(request.url)
            params = parse_qs(url.query)
            return (
                'query' in params and params['query'][0] == 'tags:alert',
                'query parameter missing or incorrect'
            )

        mock_responses.get(
            "https://mock-so-api/connect/events/",
            match=[url_matcher],
            json={"error": "API Error"},
            status=500
        )
        
        # Verify error handling returns empty list
        alerts = service.get_alerts()
        assert alerts == []

def test_get_alerts_custom_params(app, mock_responses):
    """Test retrieving alerts with custom hours and limit."""
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
        
        # Calculate expected time range for 48 hours
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=48)
        date_range = f"{start_time.strftime('%Y/%m/%d %I:%M:%S %p')} - {end_time.strftime('%Y/%m/%d %I:%M:%S %p')}"
        
        # Mock API response
        def url_matcher(request):
            url = urlparse(request.url)
            params = parse_qs(url.query)
            return (
                'query' in params and params['query'][0] == 'tags:alert' and
                'eventLimit' in params and params['eventLimit'][0] == '10',
                'query or eventLimit parameter missing or incorrect'
            )

        mock_responses.get(
            "https://mock-so-api/connect/events/",
            match=[url_matcher],
            json={
                "events": [
                    {
                        "_id": f"test-alert-{i}",
                        "_source": {
                            "@timestamp": "2024-01-01T00:00:00Z",
                            "title": f"Test Alert {i}",
                            "severity": "high"
                        }
                    }
                    for i in range(10)
                ]
            },
            status=200
        )
        
        # Get alerts with custom parameters
        alerts = service.get_alerts(hours=48, limit=10)
        
        # Verify response
        assert len(alerts) == 10
        assert all("Test Alert" in alert["_source"]["title"] for alert in alerts)

def test_get_alerts_empty_response(app, mock_responses):
    """Test handling of empty API response."""
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
        
        # Mock empty response
        def url_matcher(request):
            url = urlparse(request.url)
            params = parse_qs(url.query)
            return (
                'query' in params and params['query'][0] == 'tags:alert',
                'query parameter missing or incorrect'
            )

        mock_responses.get(
            "https://mock-so-api/connect/events/",
            match=[url_matcher],
            json={"events": []},
            status=200
        )
        
        # Verify empty list is returned
        alerts = service.get_alerts()
        assert alerts == []
