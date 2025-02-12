"""
Security Onion Case Service

This module handles case-related operations including:
- Case querying and filtering
- Case viewing and retrieval

Provides a unified interface to the Security Onion case management API,
handling all case-related read operations through dedicated endpoints.
"""
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from .base import BaseSecurityOnionClient

logger = logging.getLogger(__name__)

class CaseService:
    """Service class for Security Onion case operations"""
    
    def __init__(self, api_client: BaseSecurityOnionClient):
        """
        Initialize the case service
        
        Args:
            api_client: An initialized Security Onion API client to use for requests
        """
        self.api_client = api_client
        from .users import UserService
        self._user_service = UserService(api_client)

    def get_cases(self) -> List[Dict[str, Any]]:
        """
        Get all cases from Security Onion using the case search endpoint
        
        Returns:
            List of case objects
        """
        self.api_client._ensure_authenticated()
        
        # Get 30 days of data by default
        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)
        
        # Format dates in required format
        date_format = "2006/01/02 3:04:05 PM"
        date_range = f"{thirty_days_ago.strftime('%Y/%m/%d %I:%M:%S %p')} - {now.strftime('%Y/%m/%d %I:%M:%S %p')}"
        
        # Simple query targeting only so-case index
        params = {
            "query": '_index:"*:so-case"',
            "size": 10000,  # Get all results
            "metricLimit": 10000,  # Required by events endpoint
            "eventLimit": 10000,  # Required by events endpoint
            "format": date_format,  # Required by events endpoint
            "zone": "UTC",  # Required by events endpoint
            "range": date_range  # Add date range
        }
        
        url = f"{self.api_client.base_url}/connect/events/"
        headers = {
            **self.api_client._get_bearer_header(),
            'Content-Type': 'application/json'
        }
        logger.debug(f"Getting cases with params: {json.dumps(params, indent=2)}")
        
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
            logger.debug("=== START DEBUG CASE DATA ===")
            logger.debug(f"Raw response: {response.text}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            logger.debug(f"Response status: {response.status_code}")
                
            # Extract cases from events response
            events = results.get("events", [])
            logger.debug(f"Number of events found: {len(events)}")
            if not events:
                logger.warning("No cases found")
                return []
            
            # Extract and transform case data from events
            transformed_cases = []
            for event in events:
                # Only process case events (skip comments etc)
                payload = event.get('payload', {})
                if payload.get('so_kind') != 'case':
                    continue
                
                logger.debug(f"\n=== Processing Case ===")
                logger.debug(f"Case ID: {event.get('id')}")
                logger.debug(f"\nCase data: {json.dumps(payload, indent=2)}")
                
                # Transform case into our format
                transformed_case = self._transform_case_payload(payload, event.get('id'))
                logger.debug(f"\nTransformed case: {json.dumps(transformed_case, indent=2)}")
                transformed_cases.append(transformed_case)
            
            return transformed_cases
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting cases: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise

    def get_case(self, case_id: str) -> Dict[str, Any]:
        """
        Get a single case by ID
        
        Args:
            case_id: ID of the case to retrieve
            
        Returns:
            Case object
        """
        self.api_client._ensure_authenticated()
        
        url = f"{self.api_client.base_url}/connect/case/{case_id}"
        logger.debug(f"Getting case with ID: {case_id}")
        
        logger.debug(f"Making GET request to: {url}")
        logger.debug(f"With headers: {self.api_client._get_bearer_header()}")
        
        try:
            response = self.api_client.session.get(
                url,
                headers=self.api_client._get_bearer_header(),
                timeout=10
            )
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            result = response.json()
            logger.debug(f"Response data: {json.dumps(result, indent=2)}")
            
            # Transform case data
            case = self._transform_case_payload(result)
            
            # Get comments for the case
            try:
                comments_url = f"{self.api_client.base_url}/connect/case/comments/{case_id}" # GET endpoint for retrieving comments
                comments_response = self.api_client.session.get(
                    comments_url,
                    headers=self.api_client._get_bearer_header(),
                    timeout=10
                )
                comments_response.raise_for_status()
                comments_data = comments_response.json()
                logger.debug(f"Comments response: {json.dumps(comments_data, indent=2)}")
                
                comments = []
                for comment in comments_data:
                    user_id = comment.get('userId', '')
                    try:
                        user_name = self._user_service.get_user_name(user_id) if user_id else ''
                    except Exception as e:
                        logger.warning(f"Failed to get user name for comment ID {user_id}: {str(e)}")
                        user_name = user_id
                        
                    comments.append({
                        'id': comment.get('id', ''),
                        'text': comment.get('description', ''),
                        'created': comment.get('createTime', ''),
                        'user': user_name,
                        'user_id': user_id
                    })
                
                case['comments'] = sorted(comments, key=lambda x: x['created'], reverse=True)
                logger.debug(f"Processed comments: {json.dumps(case['comments'], indent=2)}")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error getting comments for case {case_id}: {str(e)}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Response content: {e.response.text}")
                case['comments'] = []
            
            return case
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting case {case_id}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise

    def _transform_case_payload(self, data: Dict[str, Any], event_id: Optional[str] = None) -> Dict[str, Any]:
        """Transform API payload into case object format"""
        # Get user ID and name
        user_id = data.get('so_case.userId') or data.get('so_case.assigneeId', '')
        user_name = None
        if user_id:
            try:
                name = self._user_service.get_user_name(user_id)
                # Only set user_name if lookup succeeded (didn't return ID or Unknown User)
                if name != user_id and name != 'Unknown User':
                    user_name = name
            except Exception as e:
                logger.warning(f"Failed to get user name for ID {user_id}: {str(e)}")
        
        # Ensure we have a valid ID - try different possible locations
        case_id = data.get('so_case.id') or data.get('id') or event_id
        if not case_id:
            logger.warning("No case ID found in payload or event")
            
        return {
            'id': case_id,  # May be None, template will handle this case
            'title': data.get('so_case.title') or data.get('title', 'Untitled Case'),
            'description': data.get('so_case.description') or data.get('description', ''),
            'status': data.get('so_case.status') or data.get('status', 'open'),
            'severity': data.get('so_case.severity') or data.get('severity', 'medium'),
            'priority': int(data.get('so_case.priority') or data.get('priority', 0)),
            'tags': data.get('so_case.tags') or data.get('tags', []),
            'category': data.get('so_case.category') or data.get('category', 'general'),
            'created': data.get('so_case.createTime') or data.get('createTime') or data.get('@timestamp', ''),
            'updated': data.get('so_case.completeTime') or data.get('updateTime') or data.get('@timestamp', ''),
            'user': user_name,
            'user_id': user_id
        }
