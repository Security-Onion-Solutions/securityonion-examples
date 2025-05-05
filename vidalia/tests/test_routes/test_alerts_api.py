import pytest
from flask import url_for
from urllib.parse import parse_qs, urlparse
import json
from datetime import datetime, timedelta
from io import BytesIO
import requests

def test_from_json_filter(app, client):
    """Test the from_json template filter."""
    with app.app_context():
        # This is a direct test for the template filter
        from src.routes.alerts import from_json
        
        # Valid JSON
        assert from_json('{"key": "value"}') == {"key": "value"}
        
        # Invalid JSON
        assert from_json('{"bad json') == {}
        
        # None value
        assert from_json(None) == {}

def test_parse_alert_message(app):
    """Test the _parse_alert_message function."""
    with app.app_context():
        from src.routes.alerts import _parse_alert_message
        
        # Valid message
        _parse_alert_message('{"key": "value"}')
        
        # Invalid message
        _parse_alert_message('{"invalid json')
        
        # None message
        _parse_alert_message(None)

def test_alerts_json_response(app, client, mock_responses, api_client):
    """Test the alerts list route returns JSON when requested."""
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

    # Mock API response - must match the query params used in AlertsService
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
                            "signature": "Test Alert"
                        }
                    }),
                    "observer.name": "test-sensor"
                }
            }]
        },
        status=200
    )

    # Get the alerts as JSON
    response = client.get("/alerts", headers={"Accept": "application/json"})
    
    # Check response
    assert response.status_code == 200
    assert response.content_type == "application/json"
    data = json.loads(response.data)
    assert len(data) > 0

def test_create_job_data(app):
    """Test the _create_job_data function."""
    with app.app_context():
        from src.routes.alerts import _create_job_data
        
        # Create a test alert
        alert = {
            "id": "test-alert-1",
            "timestamp": "2024-01-01T00:00:00Z",
            "payload": {
                "message": json.dumps({
                    "src_ip": "192.168.1.1",
                    "src_port": "80",
                    "dest_ip": "192.168.1.2",
                    "dest_port": "443",
                    "proto": "TCP",
                    "pkt_src": "eth0"
                }),
                "observer.name": "test-sensor"
            }
        }
        
        # Call function
        job_data = _create_job_data(alert)
        
        # Check results
        assert job_data["type"] == "pcap"
        assert job_data["nodeId"] == "test-sensor"
        assert job_data["sensorId"] == "test-sensor"
        assert "filter" in job_data
        assert job_data["filter"]["srcIp"] == "192.168.1.1"
        assert job_data["filter"]["dstIp"] == "192.168.1.2"
        assert job_data["filter"]["srcPort"] == 80
        assert job_data["filter"]["dstPort"] == 443
        assert job_data["filter"]["protocol"] == "tcp"

def test_create_job_data_missing_timestamp(app):
    """Test _create_job_data function with missing timestamp."""
    with app.app_context():
        from src.routes.alerts import _create_job_data
        
        # Create an alert with missing timestamp
        alert = {
            "id": "test-alert-1",
            "payload": {
                "observer.name": "test-sensor"
            }
        }
        
        # Call should raise ValueError
        with pytest.raises(ValueError, match="Alert missing required timestamp"):
            _create_job_data(alert)

def test_create_job_data_invalid_timestamp(app):
    """Test _create_job_data function with invalid timestamp."""
    with app.app_context():
        from src.routes.alerts import _create_job_data
        
        # Create an alert with invalid timestamp
        alert = {
            "id": "test-alert-1",
            "timestamp": "not-a-timestamp",
            "payload": {
                "observer.name": "test-sensor"
            }
        }
        
        # Call should raise ValueError
        with pytest.raises(ValueError, match="Invalid timestamp format"):
            _create_job_data(alert)

def test_create_job_data_missing_sensor(app):
    """Test _create_job_data function with missing sensor info."""
    with app.app_context():
        from src.routes.alerts import _create_job_data
        
        # Create an alert with missing sensor info
        alert = {
            "id": "test-alert-1",
            "timestamp": "2024-01-01T00:00:00Z",
            "payload": {}
        }
        
        # Call should raise ValueError
        with pytest.raises(ValueError, match="Alert missing required sensor information"):
            _create_job_data(alert)

def test_create_job_data_invalid_message(app):
    """Test _create_job_data function with invalid message format."""
    with app.app_context():
        from src.routes.alerts import _create_job_data
        
        # Create an alert with invalid message JSON
        alert = {
            "id": "test-alert-1",
            "timestamp": "2024-01-01T00:00:00Z",
            "payload": {
                "message": "{invalid json",
                "observer.name": "test-sensor"
            }
        }
        
        # Function should handle error gracefully
        job_data = _create_job_data(alert)
        
        # Check default values were used
        assert job_data["filter"]["srcIp"] == ""
        assert job_data["filter"]["dstIp"] == ""
        assert job_data["filter"]["srcPort"] == None
        assert job_data["filter"]["dstPort"] == None
        assert job_data["filter"]["protocol"] == None

def test_create_pcap_job_success(app, client, mock_responses, api_client):
    """Test successful PCAP job creation."""
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
    
    # Mock alerts endpoint
    mock_responses.get(
        "https://mock-so-api/connect/events/",
        json={
            "events": [{
                "_id": "test-alert-1",
                "timestamp": "2024-01-01T00:00:00Z",
                "payload": {
                    "message": json.dumps({
                        "src_ip": "192.168.1.1",
                        "src_port": "80",
                        "dest_ip": "192.168.1.2",
                        "dest_port": "443",
                        "proto": "TCP",
                        "pkt_src": "eth0"
                    }),
                    "observer.name": "test-sensor"
                }
            }]
        },
        status=200
    )
    
    # Mock job creation endpoint - note the correct endpoint from pcap.py
    mock_responses.post(
        "https://mock-so-api/connect/job",
        json={"id": 12345},
        status=201
    )
    
    # Create PCAP job
    response = client.post("/alerts/test-alert-1/pcap/job")
    
    # Check response
    assert response.status_code == 202
    data = json.loads(response.data)
    assert data["status"] == "pending"
    assert data["job_id"] == 12345

def test_create_pcap_job_alert_not_found(app, client, mock_responses, api_client):
    """Test PCAP job creation with non-existent alert."""
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
    
    # Mock alerts endpoint with empty results
    mock_responses.get(
        "https://mock-so-api/connect/events/",
        json={"events": []},
        status=200
    )
    
    # Try to create PCAP job for non-existent alert
    response = client.post("/alerts/non-existent-alert/pcap/job")
    
    # Check response
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data["error"] == "Alert not found"

def test_create_pcap_job_api_error(app, client, mock_responses, api_client):
    """Test PCAP job creation with API error."""
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
    
    # Mock alerts endpoint
    mock_responses.get(
        "https://mock-so-api/connect/events/",
        json={
            "events": [{
                "_id": "test-alert-1",
                "timestamp": "2024-01-01T00:00:00Z",
                "payload": {
                    "message": json.dumps({
                        "src_ip": "192.168.1.1",
                        "src_port": "80",
                        "dest_ip": "192.168.1.2",
                        "dest_port": "443",
                        "proto": "TCP",
                        "pkt_src": "eth0"
                    }),
                    "observer.name": "test-sensor"
                }
            }]
        },
        status=200
    )
    
    # Mock job creation endpoint with error - using correct endpoint from pcap.py
    mock_responses.post(
        "https://mock-so-api/connect/job",
        json={"error": "API Error"},
        status=500
    )
    
    # Try to create PCAP job
    response = client.post("/alerts/test-alert-1/pcap/job")
    
    # Check response
    assert response.status_code == 500
    data = json.loads(response.data)
    assert "error" in data

def test_check_pcap_status_pending(app, client, mock_responses, api_client):
    """Test checking status of a pending PCAP job."""
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
    
    # Mock job status endpoint with pending status - using correct endpoint from pcap.py
    mock_responses.get(
        "https://mock-so-api/connect/job/12345",
        json={"status": 0, "progress": 50},
        status=200
    )
    
    # Check job status
    response = client.get("/alerts/test-alert-1/pcap/status/12345")
    
    # Check response
    assert response.status_code == 202
    data = json.loads(response.data)
    assert data["status"] == "pending"
    assert data["job_id"] == 12345

def test_check_pcap_status_complete(app, client, mock_responses, api_client):
    """Test checking status of a completed PCAP job."""
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
    
    # Mock job status endpoint with complete status - using correct endpoint from pcap.py
    mock_responses.get(
        "https://mock-so-api/connect/job/12345",
        json={"status": 1, "progress": 100},
        status=200
    )
    
    # Check job status
    response = client.get("/alerts/test-alert-1/pcap/status/12345")
    
    # Check response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "complete"
    assert data["job_id"] == 12345

def test_check_pcap_status_failed(app, client, mock_responses, api_client):
    """Test checking status of a failed PCAP job."""
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
    
    # Mock job status endpoint with error status - using correct endpoint from pcap.py
    mock_responses.get(
        "https://mock-so-api/connect/job/12345",
        json={"status": 2, "error": "Failed to create PCAP"},
        status=200
    )
    
    # Check job status
    response = client.get("/alerts/test-alert-1/pcap/status/12345")
    
    # Check response
    assert response.status_code == 500
    data = json.loads(response.data)
    assert data["status"] == "failed"
    assert "Failed to create PCAP" in data["message"]

def test_check_pcap_status_api_error(app, client, mock_responses, api_client):
    """Test checking PCAP status with API error."""
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
    
    # Mock job status endpoint with error - using correct endpoint from pcap.py
    mock_responses.get(
        "https://mock-so-api/connect/job/12345",
        json={"error": "API Error"},
        status=500
    )
    
    # Check job status
    response = client.get("/alerts/test-alert-1/pcap/status/12345")
    
    # Check response
    assert response.status_code == 500
    data = json.loads(response.data)
    assert "error" in data

def test_download_pcap_complete(app, client, mock_responses, api_client):
    """Test downloading PCAP data for a completed job."""
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
    
    # Mock job status endpoint with complete status - using correct endpoint from pcap.py
    mock_responses.get(
        "https://mock-so-api/connect/job/12345",
        json={"status": 1, "progress": 100},
        status=200
    )
    
    # Mock PCAP download endpoint - using correct endpoint from pcap.py
    mock_responses.get(
        "https://mock-so-api/connect/stream/12345",
        body=b"mock pcap data",
        status=200,
        content_type="application/octet-stream"
    )
    
    # Download PCAP
    response = client.get("/alerts/test-alert-1/pcap/download/12345")
    
    # Check response
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/octet-stream"
    assert "attachment" in response.headers["Content-Disposition"]
    assert b"mock pcap data" == response.data

def test_download_pcap_job_not_complete(app, client, mock_responses, api_client):
    """Test downloading PCAP for a job that's not complete."""
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
    
    # Mock job status endpoint with pending status - using correct endpoint from pcap.py
    mock_responses.get(
        "https://mock-so-api/connect/job/12345",
        json={"status": 0, "progress": 50},
        status=200
    )
    
    # Try to download PCAP
    response = client.get("/alerts/test-alert-1/pcap/download/12345")
    
    # Check response
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "failed"
    assert "not complete" in data["message"]

def test_download_pcap_api_error(app, client, mock_responses, api_client):
    """Test downloading PCAP with API error."""
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
    
    # Mock job status endpoint with complete status - using correct endpoint from pcap.py
    mock_responses.get(
        "https://mock-so-api/connect/job/12345",
        json={"status": 1, "progress": 100},
        status=200
    )
    
    # Mock PCAP download endpoint with error - using correct endpoint from pcap.py
    mock_responses.get(
        "https://mock-so-api/connect/stream/12345",
        json={"error": "API Error"},
        status=500
    )
    
    # Try to download PCAP
    response = client.get("/alerts/test-alert-1/pcap/download/12345")
    
    # Check response
    assert response.status_code == 500
    data = json.loads(response.data)
    assert "error" in data