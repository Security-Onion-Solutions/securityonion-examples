import pytest
from flask import url_for
import json
import requests
from unittest.mock import patch

def test_grid_view_success(app, client, mock_responses, api_client, sample_grid_data):
    """Test grid view route displays grid info successfully."""
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
                "osUptimeSeconds": 86400 + 3600,  # 1 day, 1 hour
                "osNeedsRestart": 0,
                "cpuUsedPct": 25.5,
                "memoryUsedPct": 40.2,
                "diskUsedRootPct": 30.0
            },
            {
                "id": "node2",
                "status": "degraded",
                "updateTime": "2024-01-01T00:00:00Z",
                "osUptimeSeconds": 172800,  # 2 days
                "osNeedsRestart": 1,  # Needs reboot
                "cpuUsedPct": 75.5,
                "memoryUsedPct": 80.2,
                "diskUsedRootPct": 90.0
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
                "name": "node1",
                "role": "manager"
            },
            {
                "id": "member2", 
                "name": "node2",
                "role": "sensor"
            }
        ],
        status=200
    )
    
    # Get grid view page
    response = client.get("/grid/")
    
    # Check response
    assert response.status_code == 200
    
    # Check that node data is in the response
    assert b"node1" in response.data
    assert b"node2" in response.data
    assert b"1d 1h" in response.data  # First node uptime
    assert b"2d 0h" in response.data  # Second node uptime
    
    # Check status classes
    assert b"healthy" in response.data
    assert b"warning" in response.data

def test_grid_view_json(app, client, mock_responses, api_client):
    """Test grid view route returns JSON when requested."""
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
    
    # Get grid view as JSON
    response = client.get("/grid/", headers={"Accept": "application/json"})
    
    # Check response
    assert response.status_code == 200
    assert response.content_type == "application/json"
    
    # Parse and check JSON content
    data = json.loads(response.data)
    assert "nodes" in data
    assert len(data["nodes"]) == 1
    assert data["nodes"][0]["name"] == "node1"
    assert data["nodes"][0]["status"] == "healthy"

def test_grid_view_api_error(app, client, mock_responses, api_client):
    """Test grid view handles API errors."""
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
    
    # Mock grid nodes endpoint with error
    mock_responses.get(
        "https://mock-so-api/connect/grid",
        json={"error": "API Error"},
        status=500
    )
    
    # Get grid view page
    response = client.get("/grid/")
    
    # Check response
    assert response.status_code == 200
    assert b"Error retrieving grid status from server" in response.data
    assert b"No nodes found" in response.data

def test_grid_view_not_configured(app, client, mock_responses, api_client):
    """Test grid view when grid management is not configured."""
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
    
    # Mock grid nodes endpoint with method not allowed
    mock_responses.get(
        "https://mock-so-api/connect/grid",
        json={"error": "Method not allowed"},
        status=405
    )
    
    # Get grid view page
    response = client.get("/grid/")
    
    # Check response
    assert response.status_code == 200
    assert b"Grid management is not configured on the server" in response.data
    assert b"No nodes found" in response.data

def test_grid_view_unauthorized(app, client, mock_responses, api_client):
    """Test grid view with authentication errors."""
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
    
    # Mock grid nodes endpoint with unauthorized
    mock_responses.get(
        "https://mock-so-api/connect/grid",
        json={"error": "Unauthorized"},
        status=401
    )
    
    # Get grid view page
    response = client.get("/grid/")
    
    # Check response
    assert response.status_code == 200
    assert b"Authentication failed" in response.data
    assert b"No nodes found" in response.data

def test_grid_view_forbidden(app, client, mock_responses, api_client):
    """Test grid view with permission errors."""
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
    
    # Mock grid nodes endpoint with forbidden
    mock_responses.get(
        "https://mock-so-api/connect/grid",
        json={"error": "Forbidden"},
        status=403
    )
    
    # Get grid view page
    response = client.get("/grid/")
    
    # Check response
    assert response.status_code == 200
    assert b"Insufficient permissions" in response.data
    assert b"No nodes found" in response.data

def test_grid_view_unexpected_error(app, client, mock_responses, api_client):
    """Test grid view with unexpected errors."""
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
    
    # Mock grid nodes endpoint but throw exception
    with patch('src.services.grid.GridService.get_grid_nodes') as mock_get_grid_nodes:
        mock_get_grid_nodes.side_effect = Exception("Unexpected error")
        
        # Get grid view page
        response = client.get("/grid/")
        
        # Check response
        assert response.status_code == 200
        assert b"Error retrieving grid status" in response.data
        assert b"No nodes found" in response.data

def test_reboot_node_success(app, client, mock_responses, api_client):
    """Test successful node reboot."""
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
    
    # Mock grid member restart endpoint
    mock_responses.post(
        "https://mock-so-api/connect/gridmembers/member1/restart",
        json={"success": True},
        status=200
    )
    
    # Reboot node
    response = client.post("/grid/member1/reboot")
    
    # Check response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert "Reboot initiated" in data["message"]

def test_reboot_node_not_found(app, client, mock_responses, api_client):
    """Test reboot node when node not found."""
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
    
    # Mock grid member restart endpoint with not found
    mock_responses.post(
        "https://mock-so-api/connect/gridmembers/nonexistent/restart",
        json={"error": "Node not found"},
        status=404
    )
    
    # Reboot nonexistent node
    response = client.post("/grid/nonexistent/reboot")
    
    # Check response
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert "not found" in data["message"]

def test_reboot_node_not_configured(app, client, mock_responses, api_client):
    """Test reboot node when grid is not configured."""
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
    
    # Mock grid member restart endpoint with method not allowed
    mock_responses.post(
        "https://mock-so-api/connect/gridmembers/member1/restart",
        json={"error": "Method not allowed"},
        status=405
    )
    
    # Reboot node
    response = client.post("/grid/member1/reboot")
    
    # Check response
    assert response.status_code == 405
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert "Grid management is not configured" in data["message"]

def test_reboot_node_unauthorized(app, client, mock_responses, api_client):
    """Test reboot node with authentication errors."""
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
    
    # Mock grid member restart endpoint with unauthorized
    mock_responses.post(
        "https://mock-so-api/connect/gridmembers/member1/restart",
        json={"error": "Unauthorized"},
        status=401
    )
    
    # Reboot node
    response = client.post("/grid/member1/reboot")
    
    # Check response
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert "Authentication failed" in data["message"]

def test_reboot_node_forbidden(app, client, mock_responses, api_client):
    """Test reboot node with permission errors."""
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
    
    # Mock grid member restart endpoint with forbidden
    mock_responses.post(
        "https://mock-so-api/connect/gridmembers/member1/restart",
        json={"error": "Forbidden"},
        status=403
    )
    
    # Reboot node
    response = client.post("/grid/member1/reboot")
    
    # Check response
    assert response.status_code == 403
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert "Insufficient permissions" in data["message"]

def test_reboot_node_server_error(app, client, mock_responses, api_client):
    """Test reboot node with server errors."""
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
    
    # Mock grid member restart endpoint with server error
    mock_responses.post(
        "https://mock-so-api/connect/gridmembers/member1/restart",
        json={"error": "Server error"},
        status=500
    )
    
    # Reboot node
    response = client.post("/grid/member1/reboot")
    
    # Check response
    assert response.status_code == 500
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert "Server error" in data["message"]

def test_reboot_node_unexpected_error(app, client, mock_responses, api_client):
    """Test reboot node with unexpected errors."""
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
    
    # Use patch to simulate unexpected exception
    with patch('src.services.grid.GridService.restart_node') as mock_restart_node:
        mock_restart_node.side_effect = Exception("Unexpected error")
        
        # Reboot node
        response = client.post("/grid/member1/reboot")
        
        # Check response
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "Error rebooting node" in data["message"]