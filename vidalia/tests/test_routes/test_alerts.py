import pytest
from flask import url_for
from urllib.parse import parse_qs, urlparse
import json

def test_alerts_list_route(app, client, mock_responses, sample_alert, api_client):
    """Test the alerts list route returns successfully."""
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

    # Mock the API response for alerts
    def url_matcher(request):
        url = urlparse(request.url)
        params = parse_qs(url.query)
        return (
            'query' in params and params['query'][0] == 'tags:alert' and
            'eventLimit' in params and params['eventLimit'][0] == '5',
            'query or eventLimit parameter missing or incorrect'
        )

    mock_responses.get(
        "https://mock-so-api/connect/events/",
        match=[url_matcher],
        json={
            "events": [{
                "id": "test-alert-1",
                "timestamp": "2024-01-01T00:00:00Z",
                "payload": {
                    "message": json.dumps({
                        "alert": {
                            "signature": "Test Alert",
                            "category": "Test Category",
                            "metadata": {
                                "signature_severity": ["High"],
                                "confidence": ["100"]
                            }
                        },
                        "src_ip": "192.168.1.100",
                        "src_port": "12345",
                        "dest_ip": "192.168.1.200",
                        "dest_port": "80",
                        "proto": "TCP",
                        "pkt_src": "eth0"
                    }),
                    "event.severity_label": "High",
                    "observer.name": "test-sensor"
                }
            }]
        },
        status=200
    )

    # Get the alerts list page
    response = client.get("/alerts")
    
    # Check response
    assert response.status_code == 200
    assert b"Test Alert" in response.data
    assert b"high" in response.data

def test_alerts_list_api_error(app, client, mock_responses, api_client):
    """Test the alerts list handles API errors gracefully."""
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

    # Mock an API error response
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

    # Get the alerts list page
    response = client.get("/alerts")
    
    # Should return 200 and show empty alerts
    assert response.status_code == 200
    assert b"No alerts found" in response.data

def test_alerts_list_empty(app, client, mock_responses, api_client):
    """Test the alerts list handles empty results properly."""
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

    # Get the alerts list page
    response = client.get("/alerts")
    
    # Check response
    assert response.status_code == 200
    assert b"No alerts found" in response.data

def test_alerts_list_pagination(app, client, mock_responses, sample_alert, api_client):
    """Test the alerts list pagination."""
    # Create multiple alerts
    alerts = [
        {
            "id": f"alert-{i}",
            "timestamp": "2024-01-01T00:00:00Z",
            "payload": {
                "message": json.dumps({
                    "alert": {
                        "signature": f"Alert {i}",
                        "category": "Test Category",
                        "metadata": {
                            "signature_severity": ["High"],
                            "confidence": ["100"]
                        }
                    },
                    "src_ip": "192.168.1.100",
                    "src_port": "12345",
                    "dest_ip": "192.168.1.200",
                    "dest_port": "80",
                    "proto": "TCP",
                    "pkt_src": "eth0"
                }),
                "event.severity_label": "High",
                "observer.name": "test-sensor"
            }
        }
        for i in range(1, 11)
    ]
    
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

    # Mock paginated response
    def url_matcher(request):
        url = urlparse(request.url)
        params = parse_qs(url.query)
        return (
            'query' in params and params['query'][0] == 'tags:alert' and
            'eventLimit' in params and params['eventLimit'][0] == '5',
            'query or eventLimit parameter missing or incorrect'
        )

    mock_responses.get(
        "https://mock-so-api/connect/events/",
        match=[url_matcher],
        json={"events": alerts[:5]},
        status=200
    )

    # Get alerts page
    response = client.get("/alerts")
    
    # Check response
    assert response.status_code == 200
    assert b"Alert 1" in response.data
    assert b"Alert 5" in response.data
    # Verify we got exactly 5 alerts by counting alert headers
    assert response.data.count(b'<div class="alert-item">') == 5
