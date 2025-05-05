import pytest
from unittest.mock import MagicMock, patch
import json
import requests
import responses
from src.services.grid import GridService
from src.services.base import BaseSecurityOnionClient

@pytest.fixture
def grid_service(app, mock_responses):
    """Fixture to create a GridService with mocked client."""
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
        return GridService(client)

def test_get_grid_nodes_success(grid_service, mock_responses):
    """Test successful retrieval of grid nodes."""
    # Mock grid nodes endpoint
    mock_responses.get(
        "https://mock-so-api/connect/grid",
        json=[
            {
                "id": "node1",
                "name": "Manager Node",
                "type": "manager",
                "status": "online"
            },
            {
                "id": "node2",
                "name": "Search Node",
                "type": "search",
                "status": "online"
            }
        ],
        status=200
    )
    
    # Get grid nodes
    nodes = grid_service.get_grid_nodes()
    
    # Verify response
    assert len(nodes) == 2
    assert nodes[0]["id"] == "node1"
    assert nodes[0]["name"] == "Manager Node"
    assert nodes[1]["id"] == "node2"
    assert nodes[1]["type"] == "search"

def test_get_grid_nodes_error(grid_service, mock_responses):
    """Test error handling when getting grid nodes."""
    # Mock error response
    mock_responses.get(
        "https://mock-so-api/connect/grid",
        json={"error": "API Error"},
        status=500
    )
    
    # Get grid nodes
    nodes = grid_service.get_grid_nodes()
    
    # Should return empty list on error
    assert nodes == []

def test_get_grid_nodes_connection_error(app):
    """Test handling of connection errors when getting grid nodes."""
    with app.app_context():
        # Create client manually without using the fixture
        client = BaseSecurityOnionClient(
            base_url="https://test-so-api",
            client_id="test-client",
            client_secret="test-secret"
        )
        
        grid_service = GridService(client)
        
        # Patch the session and authentication
        with patch.object(client.session, 'get') as mock_get, \
             patch.object(client, '_ensure_authenticated') as mock_auth:
            # Skip authentication check
            mock_auth.return_value = None
            # Make get request fail
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
            
            # Get grid nodes
            nodes = grid_service.get_grid_nodes()
            
            # Should return empty list on error
            assert nodes == []

def test_get_grid_members_success(grid_service, mock_responses):
    """Test successful retrieval of grid members."""
    # Mock grid members endpoint
    mock_responses.get(
        "https://mock-so-api/connect/gridmembers",
        json=[
            {
                "id": "member1",
                "name": "Manager Member",
                "role": "manager"
            },
            {
                "id": "member2",
                "name": "Sensor Member",
                "role": "sensor"
            }
        ],
        status=200
    )
    
    # Get grid members
    members = grid_service.get_grid_members()
    
    # Verify response
    assert len(members) == 2
    assert members[0]["id"] == "member1"
    assert members[0]["name"] == "Manager Member"
    assert members[1]["id"] == "member2"
    assert members[1]["role"] == "sensor"

def test_get_grid_members_error(grid_service, mock_responses):
    """Test error handling when getting grid members."""
    # Mock error response
    mock_responses.get(
        "https://mock-so-api/connect/gridmembers",
        json={"error": "API Error"},
        status=500
    )
    
    # Get grid members
    members = grid_service.get_grid_members()
    
    # Should return empty list on error
    assert members == []

def test_get_grid_members_connection_error(app):
    """Test handling of connection errors when getting grid members."""
    with app.app_context():
        # Create client manually without using the fixture
        client = BaseSecurityOnionClient(
            base_url="https://test-so-api",
            client_id="test-client",
            client_secret="test-secret"
        )
        
        grid_service = GridService(client)
        
        # Patch the session and authentication
        with patch.object(client.session, 'get') as mock_get, \
             patch.object(client, '_ensure_authenticated') as mock_auth:
            # Skip authentication check
            mock_auth.return_value = None
            # Make get request fail
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
            
            # Get grid members
            members = grid_service.get_grid_members()
            
            # Should return empty list on error
            assert members == []

def test_restart_node_success(grid_service, mock_responses):
    """Test successful node restart."""
    # Mock restart endpoint
    mock_responses.post(
        "https://mock-so-api/connect/gridmembers/node1/restart",
        json={"status": "success", "message": "Node restarted successfully"},
        status=200
    )
    
    # Restart node
    grid_service.restart_node("node1")
    
    # If no exception is raised, the test passes

def test_restart_node_error(grid_service, mock_responses):
    """Test error handling when restarting a node."""
    # Mock error response
    mock_responses.post(
        "https://mock-so-api/connect/gridmembers/node1/restart",
        json={"error": "Node not found"},
        status=404
    )
    
    # Restart node should raise an exception
    with pytest.raises(requests.exceptions.HTTPError):
        grid_service.restart_node("node1")

def test_restart_node_connection_error(app):
    """Test handling of connection errors when restarting a node."""
    with app.app_context():
        # Create client manually without using the fixture
        client = BaseSecurityOnionClient(
            base_url="https://test-so-api",
            client_id="test-client",
            client_secret="test-secret"
        )
        
        grid_service = GridService(client)
        
        # Patch the session and authentication
        with patch.object(client.session, 'post') as mock_post, \
             patch.object(client, '_ensure_authenticated') as mock_auth:
            # Skip authentication check
            mock_auth.return_value = None
            # Make post request fail
            mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
            
            # Restart node should raise the connection error
            with pytest.raises(requests.exceptions.ConnectionError):
                grid_service.restart_node("node1")