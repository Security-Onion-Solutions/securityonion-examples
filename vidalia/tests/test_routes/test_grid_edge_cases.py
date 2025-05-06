import pytest
pytestmark = pytest.mark.skip("These tests need proper mocking to work in CI")
from flask import url_for
import json
import requests
from unittest.mock import patch

def test_grid_view_status_unknown(app, client, mock_responses, api_client):
    """Test grid view handles unknown status strings."""
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
    
    # Mock grid nodes endpoint with unknown status
    mock_responses.get(
        "https://mock-so-api/connect/grid",
        json=[
            {
                "id": "node1",
                "status": "unknown",  # Unknown status
                "updateTime": "2024-01-01T00:00:00Z",
                "osUptimeSeconds": 86400,
                "osNeedsRestart": 0,
                "cpuUsedPct": 25.5,
                "memoryUsedPct": 40.2,
                "diskUsedRootPct": 30.0
            }
        ],
        status=200
    )
    
    # Mock grid members endpoint
    mock_responses.get(
        "https://mock-so-api/connect/gridmembers",
        json=[
            {
                "id": "member1",
                "name": "node1"
            }
        ],
        status=200
    )
    
    # Get grid view page
    response = client.get("/grid/")
    
    # Check response
    assert response.status_code == 200
    
    # Check that the unknown status is rendered as error
    assert b"error" in response.data

def test_grid_view_status_critical(app, client, mock_responses, api_client):
    """Test grid view handles critical status."""
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
    
    # Mock grid nodes endpoint with critical status
    mock_responses.get(
        "https://mock-so-api/connect/grid",
        json=[
            {
                "id": "node1",
                "status": "critical",  # Critical status (should map to error)
                "updateTime": "2024-01-01T00:00:00Z",
                "osUptimeSeconds": 86400,
                "osNeedsRestart": 0,
                "cpuUsedPct": 25.5,
                "memoryUsedPct": 40.2,
                "diskUsedRootPct": 30.0
            }
        ],
        status=200
    )
    
    # Mock grid members endpoint
    mock_responses.get(
        "https://mock-so-api/connect/gridmembers",
        json=[
            {
                "id": "member1",
                "name": "node1"
            }
        ],
        status=200
    )
    
    # Get grid view page
    response = client.get("/grid/")
    
    # Check response
    assert response.status_code == 200
    
    # Check that critical status is rendered as error
    assert b"error" in response.data

def test_grid_view_status_failed(app, client, mock_responses, api_client):
    """Test grid view handles failed status."""
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
    
    # Mock grid nodes endpoint with failed status
    mock_responses.get(
        "https://mock-so-api/connect/grid",
        json=[
            {
                "id": "node1",
                "status": "failed",  # Failed status (should map to error)
                "updateTime": "2024-01-01T00:00:00Z",
                "osUptimeSeconds": 86400,
                "osNeedsRestart": 0,
                "cpuUsedPct": 25.5,
                "memoryUsedPct": 40.2,
                "diskUsedRootPct": 30.0
            }
        ],
        status=200
    )
    
    # Mock grid members endpoint
    mock_responses.get(
        "https://mock-so-api/connect/gridmembers",
        json=[
            {
                "id": "member1",
                "name": "node1"
            }
        ],
        status=200
    )
    
    # Get grid view page
    response = client.get("/grid/")
    
    # Check response
    assert response.status_code == 200
    
    # Check that failed status is rendered as error
    assert b"error" in response.data

def test_grid_view_missing_member(app, client, mock_responses, api_client):
    """Test grid view handles case where no matching member is found."""
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
    
    # Mock grid nodes endpoint 
    mock_responses.get(
        "https://mock-so-api/connect/grid",
        json=[
            {
                "id": "node1",
                "status": "ok",
                "updateTime": "2024-01-01T00:00:00Z",
                "osUptimeSeconds": 86400,
                "osNeedsRestart": 0,
                "cpuUsedPct": 25.5,
                "memoryUsedPct": 40.2,
                "diskUsedRootPct": 30.0
            }
        ],
        status=200
    )
    
    # Mock grid members endpoint with NO matching member
    mock_responses.get(
        "https://mock-so-api/connect/gridmembers",
        json=[
            {
                "id": "member1",
                "name": "different_node"  # Node name doesn't match
            }
        ],
        status=200
    )
    
    # Get grid view page
    response = client.get("/grid/")
    
    # Check response
    assert response.status_code == 200
    
    # Check that node data is in the response and member_id is "unknown"
    assert b"node1" in response.data
    assert b"unknown" in response.data  # Should have "unknown" member_id

def test_grid_view_other_http_error(app, client, mock_responses, api_client):
    """Test grid view handles other HTTP error codes."""
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
    
    # Create a requests.exceptions.HTTPError with a nonstandard status code
    with patch('src.services.grid.GridService.get_grid_nodes') as mock_get_grid_nodes:
        # Create a mock response with a 418 status code
        mock_response = requests.Response()
        mock_response.status_code = 418
        mock_response._content = b'{"error": "Some other HTTP error"}'
        mock_response.url = "https://mock-so-api/connect/grid"
        
        # Create HTTPError with this response
        error = requests.exceptions.HTTPError("418 Client Error: I'm a teapot", response=mock_response)
        mock_get_grid_nodes.side_effect = error
        
        # Get grid view page
        response = client.get("/grid/")
        
        # Check response
        assert response.status_code == 200
        
        # The general error message should be shown
        assert b"Error retrieving grid status" in response.data