import pytest
from unittest.mock import MagicMock, patch
import json
import requests
import responses
from src.services.pcap import PcapService
from src.services.base import BaseSecurityOnionClient

@pytest.fixture
def pcap_service(app, mock_responses):
    """Fixture to create a PcapService with mocked client."""
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
        
        # Return service
        return PcapService(client)

def test_create_pcap_job_success(pcap_service, mock_responses):
    """Test successful PCAP job creation."""
    # Mock job creation endpoint with less strict matching
    mock_responses.post(
        "https://mock-so-api/connect/job",
        json={"id": 123, "status": "pending"},
        status=200,
        match_querystring=False
    )
    
    # Create PCAP job
    job_data = {
        "nodeId": "node1",
        "sensorId": "sensor1",
        "filter": {
            "beginTime": "2023-01-01T00:00:00Z",
            "endTime": "2023-01-01T01:00:00Z"
        }
    }
    job_id = pcap_service.create_pcap_job(job_data)
    
    # Verify job ID
    assert job_id == 123

def test_create_pcap_job_with_all_parameters(pcap_service, mock_responses):
    """Test PCAP job creation with all optional parameters."""
    # Mock job creation endpoint with less strict matching
    mock_responses.post(
        "https://mock-so-api/connect/job",
        json={"id": 456, "status": "pending"},
        status=200,
        match_querystring=False
    )
    
    # Create PCAP job with all parameters
    job_data = {
        "type": "custom_type",
        "nodeId": "node1",
        "sensorId": "sensor1",
        "filter": {
            "beginTime": "2023-01-01T00:00:00Z",
            "endTime": "2023-01-01T01:00:00Z",
            "srcIp": "192.168.1.1",
            "dstIp": "192.168.1.2",
            "srcPort": 80,
            "dstPort": 443,
            "protocol": "tcp",
            "importId": "import123",
            "parameters": {"param1": "value1"}
        }
    }
    job_id = pcap_service.create_pcap_job(job_data)
    
    # Verify job ID
    assert job_id == 456

def test_create_pcap_job_error(pcap_service, mock_responses):
    """Test error handling when creating a PCAP job."""
    # Mock error response
    mock_responses.post(
        "https://mock-so-api/connect/job",
        json={"error": "Invalid parameters"},
        status=400
    )
    
    # Create PCAP job should raise an exception
    job_data = {
        "nodeId": "node1",
        "sensorId": "sensor1",
        "filter": {
            "beginTime": "2023-01-01T00:00:00Z",
            "endTime": "2023-01-01T01:00:00Z"
        }
    }
    with pytest.raises(requests.exceptions.HTTPError):
        pcap_service.create_pcap_job(job_data)

def test_create_pcap_job_connection_error(app):
    """Test handling of connection errors when creating a PCAP job."""
    with app.app_context():
        # Create client manually without using the fixture
        client = BaseSecurityOnionClient(
            base_url="https://test-so-api",
            client_id="test-client",
            client_secret="test-secret"
        )
        
        pcap_service = PcapService(client)
        
        # Patch the session and authentication
        with patch.object(client.session, 'post') as mock_post, \
             patch.object(client, '_ensure_authenticated') as mock_auth:
            # Skip authentication check
            mock_auth.return_value = None
            # Make post request fail
            mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
            
            # Create PCAP job should raise the connection error
            job_data = {
                "nodeId": "node1",
                "sensorId": "sensor1",
                "filter": {
                    "beginTime": "2023-01-01T00:00:00Z",
                    "endTime": "2023-01-01T01:00:00Z"
                }
            }
            with pytest.raises(requests.exceptions.ConnectionError):
                pcap_service.create_pcap_job(job_data)

def test_get_job_status_success(pcap_service, mock_responses):
    """Test successful retrieval of job status."""
    # Mock job status endpoint
    mock_responses.get(
        "https://mock-so-api/connect/job/123",
        json={
            "id": 123,
            "status": "complete",
            "progress": 100,
            "result": {"location": "/data/pcap/123.pcap"}
        },
        status=200
    )
    
    # Get job status
    status = pcap_service.get_job_status(123)
    
    # Verify status
    assert status["id"] == 123
    assert status["status"] == "complete"
    assert status["progress"] == 100

def test_get_job_status_error(pcap_service, mock_responses):
    """Test error handling when getting job status."""
    # Mock error response
    mock_responses.get(
        "https://mock-so-api/connect/job/123",
        json={"error": "Job not found"},
        status=404
    )
    
    # Get job status should raise an exception
    with pytest.raises(requests.exceptions.HTTPError):
        pcap_service.get_job_status(123)

def test_get_job_status_connection_error(app):
    """Test handling of connection errors when getting job status."""
    with app.app_context():
        # Create client manually without using the fixture
        client = BaseSecurityOnionClient(
            base_url="https://test-so-api",
            client_id="test-client",
            client_secret="test-secret"
        )
        
        pcap_service = PcapService(client)
        
        # Patch the session and authentication
        with patch.object(client.session, 'get') as mock_get, \
             patch.object(client, '_ensure_authenticated') as mock_auth:
            # Skip authentication check
            mock_auth.return_value = None
            # Make get request fail
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
            
            # Get job status should raise the connection error
            with pytest.raises(requests.exceptions.ConnectionError):
                pcap_service.get_job_status(123)

def test_download_pcap_success(pcap_service, mock_responses):
    """Test successful PCAP download."""
    # Mock PCAP download endpoint
    mock_responses.get(
        "https://mock-so-api/connect/stream/123?ext=pcap&unwrap=true",
        body=b"PCAP_DATA",
        status=200
    )
    
    # Download PCAP
    pcap_data = pcap_service.download_pcap(123)
    
    # Verify PCAP data
    assert pcap_data == b"PCAP_DATA"

def test_download_pcap_error(pcap_service, mock_responses):
    """Test error handling when downloading PCAP."""
    # Mock error response
    mock_responses.get(
        "https://mock-so-api/connect/stream/123?ext=pcap&unwrap=true",
        json={"error": "PCAP not found"},
        status=404
    )
    
    # Download PCAP should raise an exception
    with pytest.raises(requests.exceptions.HTTPError):
        pcap_service.download_pcap(123)

def test_download_pcap_connection_error(app):
    """Test handling of connection errors when downloading PCAP."""
    with app.app_context():
        # Create client manually without using the fixture
        client = BaseSecurityOnionClient(
            base_url="https://test-so-api",
            client_id="test-client",
            client_secret="test-secret"
        )
        
        pcap_service = PcapService(client)
        
        # Patch the session and authentication
        with patch.object(client.session, 'get') as mock_get, \
             patch.object(client, '_ensure_authenticated') as mock_auth:
            # Skip authentication check
            mock_auth.return_value = None
            # Make get request fail
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
            
            # Download PCAP should raise the connection error
            with pytest.raises(requests.exceptions.ConnectionError):
                pcap_service.download_pcap(123)