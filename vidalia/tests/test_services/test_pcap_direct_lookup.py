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

def test_lookup_pcap_by_event_with_esid(pcap_service, mock_responses):
    """Test direct PCAP lookup using Elasticsearch ID."""
    # Mock joblookup endpoint
    mock_responses.get(
        "https://mock-so-api/connect/joblookup?time=2023-01-01T00%3A00%3A00.000Z&esid=test-es-id",
        body=b"PCAP_DATA_FROM_ESID",
        status=200,
        match_querystring=True
    )
    
    # Call the method with esid
    pcap_data = pcap_service.lookup_pcap_by_event(
        time="2023-01-01T00:00:00.000Z",
        esid="test-es-id"
    )
    
    # Verify PCAP data
    assert pcap_data == b"PCAP_DATA_FROM_ESID"

def test_lookup_pcap_by_event_with_ncid(pcap_service, mock_responses):
    """Test direct PCAP lookup using network community ID."""
    # Mock joblookup endpoint
    mock_responses.get(
        "https://mock-so-api/connect/joblookup?time=2023-01-01T00%3A00%3A00.000Z&ncid=1%3AURggUwcolUh%2FBgIWApL6rUUZUK4%3D",
        body=b"PCAP_DATA_FROM_NCID",
        status=200,
        match_querystring=True
    )
    
    # Call the method with ncid
    pcap_data = pcap_service.lookup_pcap_by_event(
        time="2023-01-01T00:00:00.000Z",
        ncid="1:URggUwcolUh/BgIWApL6rUUZUK4="
    )
    
    # Verify PCAP data
    assert pcap_data == b"PCAP_DATA_FROM_NCID"

def test_lookup_pcap_by_event_with_both(pcap_service, mock_responses):
    """Test direct PCAP lookup using both Elasticsearch ID and network community ID."""
    # Mock joblookup endpoint
    mock_responses.get(
        "https://mock-so-api/connect/joblookup?time=2023-01-01T00%3A00%3A00.000Z&esid=test-es-id&ncid=1%3AURggUwcolUh%2FBgIWApL6rUUZUK4%3D",
        body=b"PCAP_DATA_FROM_BOTH",
        status=200,
        match_querystring=True
    )
    
    # Call the method with both
    pcap_data = pcap_service.lookup_pcap_by_event(
        time="2023-01-01T00:00:00.000Z",
        esid="test-es-id",
        ncid="1:URggUwcolUh/BgIWApL6rUUZUK4="
    )
    
    # Verify PCAP data
    assert pcap_data == b"PCAP_DATA_FROM_BOTH"

def test_lookup_pcap_by_event_missing_parameters(app):
    """Test that error is raised if neither esid nor ncid is provided."""
    with app.app_context():
        # Create client manually without using the fixture
        client = BaseSecurityOnionClient(
            base_url="https://test-so-api",
            client_id="test-client",
            client_secret="test-secret"
        )
        
        pcap_service = PcapService(client)
        
        # Skip authentication check since we're not making actual requests
        with patch.object(client, '_ensure_authenticated') as mock_auth:
            mock_auth.return_value = None
            
            with pytest.raises(ValueError, match="Either esid or ncid parameter must be provided"):
                pcap_service.lookup_pcap_by_event(
                    time="2023-01-01T00:00:00.000Z"
                )

def test_lookup_pcap_by_event_error_response(pcap_service, mock_responses):
    """Test error handling when API returns an error."""
    # Mock error response as JSON
    mock_responses.get(
        "https://mock-so-api/connect/joblookup?time=2023-01-01T00%3A00%3A00.000Z&esid=test-es-id",
        json={"error": "PCAP not found"},
        status=404,
        content_type="application/json"
    )
    
    # Call should raise an exception
    with pytest.raises(requests.exceptions.HTTPError):
        pcap_service.lookup_pcap_by_event(
            time="2023-01-01T00:00:00.000Z", 
            esid="test-es-id"
        )

def test_lookup_pcap_by_event_connection_error(app):
    """Test handling of connection errors when looking up PCAP."""
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
            
            # Method call should raise the connection error
            with pytest.raises(requests.exceptions.ConnectionError):
                pcap_service.lookup_pcap_by_event(
                    time="2023-01-01T00:00:00.000Z", 
                    esid="test-es-id"
                )