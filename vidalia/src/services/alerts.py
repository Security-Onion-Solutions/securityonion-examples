"""
Security Onion Alert Service

This module handles alert-related operations including:
- Alert data retrieval
- Alert filtering and sorting
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import requests
from .base import BaseSecurityOnionClient

logger = logging.getLogger(__name__)

class AlertsService:
    """Service class for Security Onion alert operations"""
    
    def __init__(self, api_client: BaseSecurityOnionClient):
        """
        Initialize the alert service
        
        Args:
            api_client: An initialized Security Onion API client to use for requests
        """
        self.api_client = api_client

    def get_alerts(self, hours: int = 24, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get alerts from Security Onion
        
        Args:
            hours: Number of hours of alerts to retrieve (default: 24)
            limit: Maximum number of alerts to return (default: 5)
            
        Returns:
            List of alert events
        """
        self.api_client._ensure_authenticated()
        
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Format for Security Onion API
        date_format = "2006/01/02 3:04:05 PM"
        date_range = f"{start_time.strftime('%Y/%m/%d %I:%M:%S %p')} - {end_time.strftime('%Y/%m/%d %I:%M:%S %p')}"
        
        params = {
            "query": "tags:alert",
            "range": date_range,
            "zone": "UTC",
            "format": date_format,
            "metricLimit": 10000,
            "eventLimit": limit,
            "sort": "@timestamp:desc"  # Sort by timestamp descending (newest first)
        }
        
        url = f"{self.api_client.base_url}/connect/events/?"
        headers = self.api_client._get_bearer_header()
        logger.debug(f"Making request to: {url}")
        logger.debug(f"With params: {json.dumps(params, indent=2)}")
        logger.debug(f"With headers: {json.dumps(headers, indent=2)}")
        
        try:
            response = self.api_client.session.get(
                url,
                headers=headers,
                params=params,
                timeout=10
            )
            logger.debug(f"Response status: {response.status_code}")
            
            response.raise_for_status()
            results = response.json()
            logger.debug(f"API Response: {json.dumps(results, indent=2)}")
            
            events = results.get("events", [])
            if not events:
                logger.warning("No events returned from API")
                return []
                
            # Enhanced debug logging for raw event structure
            if events:
                logger.debug("Raw event structure before transformation:")
                logger.debug(f"Complete first event: {json.dumps(events[0], indent=2)}")
                
                # Log each top-level field separately for clarity
                event = events[0]
                for field in event:
                    logger.debug(f"Field '{field}': {json.dumps(event[field], indent=2)}")
                
                # Specifically check for observer in all possible locations
                source = event.get('_source', {})
                logger.debug(f"Observer in _source: {json.dumps(source.get('observer', {}), indent=2)}")
                
                payload = event.get('payload', {})
                logger.debug(f"Raw payload: {json.dumps(payload, indent=2)}")
                
                # Try to parse message if it exists
                message = payload.get('message', '{}')
                try:
                    message_data = json.loads(message)
                    logger.debug(f"Parsed message: {json.dumps(message_data, indent=2)}")
                    if 'observer' in message_data:
                        logger.debug(f"Observer in message: {json.dumps(message_data['observer'], indent=2)}")
                except json.JSONDecodeError:
                    logger.debug("Could not parse message as JSON")
            
            # Sort by timestamp if available
            sorted_events = sorted(events, 
                                key=lambda x: x.get('_source', {}).get('@timestamp', ''), 
                                reverse=True)
            return sorted_events[:limit]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get alerts: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Error response content: {e.response.text}")
            return []
