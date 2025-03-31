# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

"""
Alert acknowledgment command implementation.

Required Permissions:
- events/write: For acknowledging alerts via POST /connect/events/ack

Note: Permissions are assigned to API clients through Security Onion's RBAC system,
not through OAuth 2.0 scopes.
"""

from ...models.chat_users import ChatService
from datetime import datetime, timedelta
import json
import httpx
from ...core.securityonion import client
from ...core.permissions import CommandPermission
from ...core.decorators import requires_permission
from .validation import command_validator

@requires_permission()  # Ack command permission is already defined in COMMAND_PERMISSIONS
@command_validator(required_args=1, optional_args=0)
async def process(command: str, user_id: str = None, platform: ChatService = None, username: str = None, channel_id: str = None) -> str:
    """Process the ack command.
    
    Args:
        command: The command string to process
        platform: The platform the command is coming from (discord/slack)
        user_id: The platform-specific user ID
        username: The user's display name
    """
    # Extract event ID from command
    event_id = command.split()[1]  # Safe to access since validator ensures argument exists
    
    try:
        # Ensure we have a valid connection
        if not client._connected:
            return "Error: Not connected to Security Onion"
            
        # Get current time for date range - use 6 months back from now
        now = datetime.utcnow()
        time_6months_ago = now - timedelta(days=180)
        
        # Prepare the ack request following Security Onion API format
        ack_data = {
            "acknowledge": True,
            "dateRange": f"{time_6months_ago.strftime('%Y/%m/%d %I:%M:%S %p')} - {now.strftime('%Y/%m/%d %I:%M:%S %p')}",
            "dateRangeFormat": "2006/01/02 3:04:05 PM",
            "escalate": False,
            "eventFilter": {
                "log.id.uid": event_id  # Filter by the specific event ID
            },
            "searchFilter": "tags:alert",  # Just ensure it's an alert
            "timezone": "UTC"
        }
        
        # Make POST request to acknowledge the alert
        base_url = client._base_url.rstrip('/') + '/'
        full_url = f"{base_url}connect/events/ack"
        headers = client._get_headers()
        
        print("\n=== ACK REQUEST DEBUG INFO ===")
        print(f"URL: {full_url}")
        print(f"Headers: {json.dumps(headers, indent=2)}")
        print(f"Request Body: {json.dumps(ack_data, indent=2)}")
        
        response = await client._client.post(
            full_url,
            headers=headers,
            json=ack_data
        )
        
        print("\n=== ACK RESPONSE DEBUG INFO ===")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Content: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Ack response data: {json.dumps(data, indent=2)}")
            if data.get("updatedCount", 0) > 0:
                return f"Successfully acknowledged alert with ID: {event_id}"
            else:
                return f"No alert found with ID: {event_id}"
        else:
            return f"Failed to acknowledge alert. Status code: {response.status_code}"
            
    except Exception as e:
        return f"Error acknowledging alert: {str(e)}"
