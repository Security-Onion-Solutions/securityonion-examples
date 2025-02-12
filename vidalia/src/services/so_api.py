"""
Security Onion API Service

This module provides a unified interface to Security Onion API services.
It acts as a facade combining functionality from specialized service modules:
- Authentication and session management (base)
- User management and caching (users)
- Alert retrieval (alerts)
- PCAP job management (pcap)
- Grid node management (grid)
- Case management (cases)
"""
from typing import Dict, List, Optional, Any
from .base import BaseSecurityOnionClient
from .users import UserService
from .alerts import AlertsService
from .pcap import PcapService
from .grid import GridService
from .cases import CaseService

class SecurityOnionAPI(BaseSecurityOnionClient):
    """Unified service class for interacting with the Security Onion API"""
    
    def __init__(self, base_url: str, client_id: str, client_secret: str):
        """
        Initialize the Security Onion API client
        
        Args:
            base_url: Base URL of the Security Onion API
            client_id: OAuth client ID
            client_secret: OAuth client secret
        """
        super().__init__(base_url, client_id, client_secret)
        
        # Initialize specialized services
        self._user_service = UserService(self)
        self._alert_service = AlertsService(self)
        self._pcap_service = PcapService(self)
        self._grid_service = GridService(self)
        self._case_service = CaseService(self)  # Use dependency injection like other services

    # User operations
    def get_user_name(self, user_id: str) -> str:
        """Delegate to UserService"""
        return self._user_service.get_user_name(user_id)

    def get_users(self) -> List[Dict[str, Any]]:
        """Delegate to UserService"""
        return self._user_service.get_users()

    # Alert operations
    def get_alerts(self, hours: int = 24, limit: int = 5) -> List[Dict[str, Any]]:
        """Delegate to AlertService"""
        return self._alert_service.get_alerts(hours, limit)

    # PCAP operations
    def create_pcap_job(self, job_data: Dict[str, Any]) -> int:
        """Delegate to PcapService"""
        return self._pcap_service.create_pcap_job(job_data)

    def get_job_status(self, job_id: int) -> Dict[str, Any]:
        """Delegate to PcapService"""
        return self._pcap_service.get_job_status(job_id)

    def download_pcap(self, job_id: int) -> bytes:
        """Delegate to PcapService"""
        return self._pcap_service.download_pcap(job_id)

    # Grid operations
    def get_grid_nodes(self) -> List[Dict[str, Any]]:
        """Delegate to GridService"""
        return self._grid_service.get_grid_nodes()

    def get_grid_members(self) -> List[Dict[str, Any]]:
        """Delegate to GridService"""
        return self._grid_service.get_grid_members()

    def restart_node(self, node_id: str) -> None:
        """Delegate to GridService"""
        return self._grid_service.restart_node(node_id)

    def reboot_node(self, node_id: str) -> None:
        """
        Reboot a grid node (alias for restart_node)
        
        Args:
            node_id: ID of the node to reboot
        """
        return self.restart_node(node_id)

    # Case operations
    def get_cases(self) -> List[Dict[str, Any]]:
        """Delegate to CaseService"""
        return self._case_service.get_cases()

    def get_case(self, case_id: str) -> Dict[str, Any]:
        """Delegate to CaseService"""
        return self._case_service.get_case(case_id)

    def create_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate to CaseService"""
        return self._case_service.create_case(case_data)

    def update_case(self, case_id: str, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate to CaseService"""
        return self._case_service.update_case(case_id, case_data)

    def add_case_comment(self, case_id: str, comment: str, hours: float = 0.0) -> Dict[str, Any]:
        """
        Delegate to CaseService
        
        Args:
            case_id: ID of the case to comment on
            comment: Comment text
            hours: Number of hours spent (default: 0.0)
            
        Returns:
            Updated case object with new comment
        """
        return self._case_service.add_case_comment(case_id, comment, hours)

    def delete_case(self, case_id: str) -> None:
        """Delegate to CaseService"""
        return self._case_service.delete_case(case_id)
