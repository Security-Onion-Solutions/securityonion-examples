"""
Tests for the SecurityOnionAPI lookup_pcap_by_event function
"""
import pytest
from unittest.mock import MagicMock, patch
from src.services.so_api import SecurityOnionAPI


def test_lookup_pcap_by_event():
    """Test the lookup_pcap_by_event method"""
    # Create a mock PcapService instance
    mock_pcap_service = MagicMock()
    mock_pcap_service.lookup_pcap_by_event.return_value = b'mock pcap data'
    
    # Create a SecurityOnionAPI instance with mock services
    api = SecurityOnionAPI('https://mock-so-api', 'client_id', 'client_secret')
    
    # Replace the PcapService with our mock
    api._pcap_service = mock_pcap_service
    
    # Call the method
    result = api.lookup_pcap_by_event('2024-01-01T00:00:00Z', 'test-esid', 'test-ncid')
    
    # Verify the result
    assert result == b'mock pcap data'
    
    # Verify the mock was called with the correct parameters
    mock_pcap_service.lookup_pcap_by_event.assert_called_once_with(
        '2024-01-01T00:00:00Z', 'test-esid', 'test-ncid'
    )