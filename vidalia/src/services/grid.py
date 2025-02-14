"""
Security Onion Grid Service

This module handles grid-related operations including:
- Grid node status monitoring
- Grid member management
- Node restart functionality
"""
import json
import logging
import requests
from typing import Dict, List, Any
from .base import BaseSecurityOnionClient

logger = logging.getLogger(__name__)

class GridService:
    """Service class for Security Onion grid operations"""
    
    def __init__(self, api_client: BaseSecurityOnionClient):
        """
        Initialize the grid service
        
        Args:
            api_client: An initialized Security Onion API client to use for requests
        """
        self.api_client = api_client

    def get_grid_nodes(self) -> List[Dict[str, Any]]:
        """
        Get list of grid nodes and their status
        
        Returns:
            List of node objects containing status information
        """
        self.api_client._ensure_authenticated()
        
        try:
            response = self.api_client.session.get(
                f"{self.api_client.base_url}/connect/grid",
                headers=self.api_client._get_bearer_header(),
                timeout=10
            )
            logger.debug(f"Grid nodes response status: {response.status_code}")
            
            response.raise_for_status()
            nodes = response.json()
            logger.debug(f"Grid nodes: {json.dumps(nodes, indent=2)}")
            return nodes
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get grid nodes: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Error response content: {e.response.text}")
            return []

    def get_grid_members(self) -> List[Dict[str, Any]]:
        """
        Get list of all grid members
        
        Returns:
            List of grid member objects
        """
        self.api_client._ensure_authenticated()
        
        try:
            response = self.api_client.session.get(
                f"{self.api_client.base_url}/connect/gridmembers",
                headers=self.api_client._get_bearer_header(),
                timeout=10
            )
            logger.debug(f"Grid members response status: {response.status_code}")
            
            response.raise_for_status()
            members = response.json()
            logger.debug(f"Grid members: {json.dumps(members, indent=2)}")
            return members
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get grid members: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Error response content: {e.response.text}")
            return []

    def restart_node(self, node_id: str) -> None:
        """
        Restart a specific grid node
        
        Args:
            node_id: ID of the node to restart
            
        Raises:
            ValueError: If the node is not found
        """
        self.api_client._ensure_authenticated()
        
        # First verify the node exists
        members = self.get_grid_members()
        node = next((m for m in members if m.get("id") == node_id), None)
        if not node:
            logger.error(f"Node {node_id} not found in grid nodes")
            raise ValueError(f"Node {node_id} not found")
        
        url = f"{self.api_client.base_url}/connect/gridmembers/{node_id}/restart"
        headers = self.api_client._get_bearer_header()
        
        logger.debug(f"Attempting to restart node {node_id}")
        logger.debug(f"Using URL: {url}")
        logger.debug(f"Using headers: {json.dumps(headers, indent=2)}")
        
        try:
            response = self.api_client.session.post(
                url,
                headers=headers,
                timeout=10
            )
            logger.debug(f"Restart response status: {response.status_code}")
            logger.debug(f"Restart response headers: {dict(response.headers)}")
            logger.debug(f"Restart response content: {response.text}")
            
            response.raise_for_status()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to restart node: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Error response content: {e.response.text}")
            raise
