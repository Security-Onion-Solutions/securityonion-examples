import pytest
from unittest.mock import MagicMock, patch
import json
from datetime import datetime
from io import BytesIO
import requests

@pytest.fixture
def mock_alert_data():
    """Fixture to provide sample alert data"""
    return [
        {
            "_id": "test-alert-id",
            "timestamp": "2023-01-01T12:34:56Z",
            "payload": {
                "network.community_id": "1:URggUwcolUh/BgIWApL6rUUZUK4=",
                "observer.name": "sensor1"
            }
        },
        {
            "_id": "alert-with-nested",
            "timestamp": "2023-01-01T12:34:56Z",
            "payload": {
                "network": {
                    "community_id": "1:NestedCommunityId="
                },
                "observer.name": "sensor1"
            }
        },
        {
            "_id": "alert-with-message",
            "timestamp": "2023-01-01T12:34:56Z",
            "payload": {
                "message": json.dumps({
                    "network": {
                        "community_id": "1:MessageCommunityId="
                    }
                }),
                "observer.name": "sensor1"
            }
        }
    ]

def test_direct_pcap_download_with_esid(client, app, mock_alert_data):
    """Test direct PCAP download route with Elasticsearch ID"""
    with app.app_context():
        # Mock the get_alerts method
        app.so_api.get_alerts = MagicMock(return_value=mock_alert_data)
        
        # Mock the lookup_pcap_by_event method
        app.so_api.lookup_pcap_by_event = MagicMock(return_value=b"TEST_PCAP_DATA")
        
        # Call the route
        response = client.get('/alerts/test-alert-id/pcap/direct')
        
        # Check response
        assert response.status_code == 200
        assert response.mimetype == 'application/octet-stream'
        assert response.data == b"TEST_PCAP_DATA"
        
        # Verify the lookup was called with the correct parameters
        app.so_api.lookup_pcap_by_event.assert_called_once()
        args, kwargs = app.so_api.lookup_pcap_by_event.call_args
        assert kwargs['esid'] == 'test-alert-id'
        assert kwargs['ncid'] == '1:URggUwcolUh/BgIWApL6rUUZUK4='
        assert 'time' in kwargs  # Don't check exact format as it depends on datetime.now()

def test_direct_pcap_download_with_nested_community_id(client, app, mock_alert_data):
    """Test direct PCAP download with nested community ID field"""
    with app.app_context():
        # Mock the get_alerts method
        app.so_api.get_alerts = MagicMock(return_value=mock_alert_data)
        
        # Mock the lookup_pcap_by_event method
        app.so_api.lookup_pcap_by_event = MagicMock(return_value=b"TEST_PCAP_DATA")
        
        # Call the route
        response = client.get('/alerts/alert-with-nested/pcap/direct')
        
        # Check response
        assert response.status_code == 200
        
        # Verify the lookup was called with the correct parameters
        app.so_api.lookup_pcap_by_event.assert_called_once()
        args, kwargs = app.so_api.lookup_pcap_by_event.call_args
        assert kwargs['esid'] == 'alert-with-nested'
        assert kwargs['ncid'] == '1:NestedCommunityId='

def test_direct_pcap_download_with_message_community_id(client, app, mock_alert_data):
    """Test direct PCAP download with community ID in message field"""
    with app.app_context():
        # Mock the get_alerts method
        app.so_api.get_alerts = MagicMock(return_value=mock_alert_data)
        
        # Mock the lookup_pcap_by_event method
        app.so_api.lookup_pcap_by_event = MagicMock(return_value=b"TEST_PCAP_DATA")
        
        # Call the route
        response = client.get('/alerts/alert-with-message/pcap/direct')
        
        # Check response
        assert response.status_code == 200
        
        # Verify the lookup was called with the correct parameters
        app.so_api.lookup_pcap_by_event.assert_called_once()
        args, kwargs = app.so_api.lookup_pcap_by_event.call_args
        assert kwargs['esid'] == 'alert-with-message'
        assert kwargs['ncid'] == '1:MessageCommunityId='

def test_direct_pcap_download_alert_not_found(client, app):
    """Test direct PCAP download when alert is not found"""
    with app.app_context():
        # Mock the get_alerts method to return empty list
        app.so_api.get_alerts = MagicMock(return_value=[])
        
        # Mock the lookup_pcap_by_event method to track calls
        app.so_api.lookup_pcap_by_event = MagicMock()
        
        # Call the route
        response = client.get('/alerts/nonexistent-id/pcap/direct')
        
        # Check response
        assert response.status_code == 404
        assert response.json['error'] == 'Alert not found'
        
        # Verify the lookup was not called
        assert not app.so_api.lookup_pcap_by_event.called

def test_direct_pcap_download_missing_timestamp(client, app):
    """Test direct PCAP download when alert is missing timestamp"""
    with app.app_context():
        # Mock the get_alerts method to return alert without timestamp
        app.so_api.get_alerts = MagicMock(return_value=[
            {
                "_id": "alert-no-timestamp",
                "payload": {}
            }
        ])
        
        # Call the route
        response = client.get('/alerts/alert-no-timestamp/pcap/direct')
        
        # Check response
        assert response.status_code == 400
        assert response.json['error'] == 'Alert missing timestamp'

def test_direct_pcap_download_api_error(client, app, mock_alert_data):
    """Test direct PCAP download when API returns an error"""
    with app.app_context():
        # Mock the get_alerts method
        app.so_api.get_alerts = MagicMock(return_value=mock_alert_data)
        
        # Mock the lookup_pcap_by_event method to raise an exception
        error_response = requests.Response()
        error_response.status_code = 404
        error = requests.exceptions.HTTPError("Not found", response=error_response)
        app.so_api.lookup_pcap_by_event = MagicMock(side_effect=error)
        
        # Call the route
        response = client.get('/alerts/test-alert-id/pcap/direct')
        
        # Check response
        assert response.status_code == 500
        assert 'error' in response.json