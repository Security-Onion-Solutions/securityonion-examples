"""
Security Onion PCAP Service

This module handles PCAP-related operations including:
- PCAP job creation
- Job status monitoring
- PCAP data download
"""
import json
import logging
import requests
from typing import Dict, Any
from .base import BaseSecurityOnionClient

logger = logging.getLogger(__name__)

class PcapService:
    """Service class for Security Onion PCAP operations"""
    
    def __init__(self, api_client: BaseSecurityOnionClient):
        """
        Initialize the PCAP service
        
        Args:
            api_client: An initialized Security Onion API client to use for requests
        """
        self.api_client = api_client

    def create_pcap_job(self, job_data: Dict[str, Any]) -> int:
        """
        Create a PCAP job with the provided configuration
        
        Args:
            job_data: Job configuration containing node and filter parameters
            
        Returns:
            Job ID for the created PCAP job
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        self.api_client._ensure_authenticated()
        
        # Format job data to match API expectations
        formatted_job_data = {
            "type": job_data.get("type", "pcap"),
            "nodeId": job_data.get("nodeId"),  # No default - must be provided
            "sensorId": job_data.get("sensorId"),  # No default - must be provided
            "filter": {
                "importId": job_data.get("filter", {}).get("importId", ""),
                "beginTime": job_data.get("filter", {}).get("beginTime"),  # Use existing beginTime
                "endTime": job_data.get("filter", {}).get("endTime"),
                "srcIp": job_data.get("filter", {}).get("srcIp", ""),
                "dstIp": job_data.get("filter", {}).get("dstIp", ""),
                "srcPort": job_data.get("filter", {}).get("srcPort"),
                "dstPort": job_data.get("filter", {}).get("dstPort"),
                "protocol": job_data.get("filter", {}).get("protocol", ""),
                "parameters": job_data.get("filter", {}).get("parameters", {})
            }
        }

        logger.debug(f"Creating PCAP job with formatted data: {json.dumps(formatted_job_data, indent=2)}")
        
        try:
            job_url = f"{self.api_client.base_url}/connect/job"
            logger.debug(f"Using job creation URL: {job_url}")
            
            response = self.api_client.session.post(
                job_url,
                headers=self.api_client._get_bearer_header(),
                json=formatted_job_data,
                timeout=10
            )
            logger.debug(f"PCAP job creation response status: {response.status_code}")
            logger.debug(f"PCAP job creation response headers: {dict(response.headers)}")
            logger.debug(f"PCAP job creation response content: {response.text}")
            
            response.raise_for_status()
            
            job = response.json()
            logger.debug(f"Created PCAP job: {json.dumps(job, indent=2)}")
            return job["id"]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create PCAP job: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Error response content: {e.response.text}")
            raise

    def get_job_status(self, job_id: int) -> Dict[str, Any]:
        """
        Get the status of a PCAP job
        
        Args:
            job_id: ID of the job to check
            
        Returns:
            Job status information
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        self.api_client._ensure_authenticated()
        
        try:
            response = self.api_client.session.get(
                f"{self.api_client.base_url}/connect/job/{job_id}",
                headers=self.api_client._get_bearer_header(),
                timeout=10
            )
            logger.debug(f"Job status response status: {response.status_code}")
            logger.debug(f"Job status response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            status = response.json()
            logger.debug(f"Job status: {json.dumps(status, indent=2)}")
            return status
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get job status for job {job_id}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Error response content: {e.response.text}")
            raise

    def download_pcap(self, job_id: int) -> bytes:
        """
        Download PCAP data for a completed job
        
        Args:
            job_id: ID of the completed PCAP job
            
        Returns:
            PCAP file data as bytes
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        self.api_client._ensure_authenticated()
        
        try:
            # Add pcap extension and unwrap parameters
            params = {
                'ext': 'pcap',
                'unwrap': 'true'
            }
            response = self.api_client.session.get(
                f"{self.api_client.base_url}/connect/stream/{job_id}",
                headers=self.api_client._get_bearer_header(),
                params=params,
                timeout=10
            )
            logger.debug(f"PCAP download response status: {response.status_code}")
            logger.debug(f"PCAP download response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            return response.content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download PCAP for job {job_id}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Error response content: {e.response.text}")
            raise
