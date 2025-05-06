"""
Tests for PcapService when the API returns JSON errors
"""
import pytest
import json
import requests
from unittest.mock import patch, MagicMock
from src.services.pcap import PcapService
from src.services.base import BaseSecurityOnionClient


@pytest.fixture
def mock_api_client():
    """Create a mock API client"""
    client = MagicMock(spec=BaseSecurityOnionClient)
    client.base_url = "https://mock-so-api"
    client.session = MagicMock()
    client._get_bearer_header.return_value = {"Authorization": "Bearer test-token"}
    return client


@pytest.fixture
def pcap_service(mock_api_client):
    """Create a PcapService with mock client"""
    return PcapService(mock_api_client)


def test_lookup_pcap_json_error_response(pcap_service, mock_api_client):
    """Test handling JSON error responses in lookup_pcap_by_event"""
    # Mock the response to return a JSON error
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = {"error": "PCAP not found"}
    mock_response.text = json.dumps({"error": "PCAP not found"})
    
    # Configure the mock session to return our mock response
    mock_api_client.session.get.return_value = mock_response
    
    # Call the method and check it raises an exception
    with pytest.raises(requests.exceptions.HTTPError) as excinfo:
        pcap_service.lookup_pcap_by_event(time="2024-01-01T00:00:00Z", esid="test-id")
    
    # Verify the error message contains the API error
    assert "API error: PCAP not found" in str(excinfo.value)
    
    # Verify the mock was called correctly
    mock_api_client.session.get.assert_called_once()
    args, kwargs = mock_api_client.session.get.call_args
    assert args[0] == "https://mock-so-api/connect/joblookup"
    assert kwargs["params"]["time"] == "2024-01-01T00:00:00Z"
    assert kwargs["params"]["esid"] == "test-id"