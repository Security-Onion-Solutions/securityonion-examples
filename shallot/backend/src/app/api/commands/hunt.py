# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

from ...models.chat_users import ChatService
from datetime import datetime, timedelta
import json
import httpx
import tempfile
import os
import logging

logger = logging.getLogger(__name__)
from ...core.securityonion import client
from ...core.chat_manager import chat_manager
from ...core.permissions import CommandPermission
from ...core.decorators import requires_permission
from .validation import command_validator

@requires_permission()  # Hunt command permission is already defined in COMMAND_PERMISSIONS
@command_validator(required_args=1, optional_args=0)  # Requires exactly one argument: eventid
async def process(command: str, user_id: str = None, platform: ChatService = None, username: str = None, channel_id: str = None) -> str:
    """Process the hunt command.
    
    Args:
        command: The command string to process
        platform: The platform the command is coming from (discord/slack)
        user_id: The platform-specific user ID
        username: The user's display name
    """
    try:
        # Ensure we have a valid connection
        if not client._connected:
            return "Error: Not connected to Security Onion"
        
        # Parse command arguments
        parts = command.strip().split()
        if len(parts) != 2:
            return "Usage: !hunt <eventid>"
        
        eventid = parts[1]
        
        # Query the specific event first
        base_url = client._base_url.rstrip('/') + '/'
        headers = client._get_headers()
        
        # First query to get the event and extract network.communityid
        query_params = {
            "query": f"log.id.uid:{eventid}",
            "fields": "*",
            "metricLimit": "10000",
            "eventLimit": "1"
        }
        
        try:
            response = await client._client.get(
                f"{base_url}connect/events",
                headers=headers,
                params=query_params
            )
            
            if response.status_code != 200:
                return f"Error querying event: HTTP {response.status_code}"
            
            data = response.json()
            events = data.get('events', [])
            
            if not events:
                return f"No event found with ID: {eventid}"
            
            # Extract network.communityid from the event
            event = events[0]
            payload = event.get('payload', {})
            message_str = payload.get('message', '{}')
            
            try:
                # Get community_id directly from payload
                community_id = payload.get('network.community_id')
                
                if not community_id:
                    return f"No network.community_id found for event: {eventid}"
                
                # Now query all events with this community_id
                now = datetime.utcnow()
                time_24h_ago = now - timedelta(hours=24)
                
                hunt_params = {
                    "query": f"network\\.community_id:\"{community_id}\"",
                    "range": f"{time_24h_ago.strftime('%Y/%m/%d %I:%M:%S %p')} - {now.strftime('%Y/%m/%d %I:%M:%S %p')}",
                    "zone": "UTC",
                    "format": "2006/01/02 3:04:05 PM",
                    "fields": "*",
                    "metricLimit": "10000",
                    "eventLimit": "10",
                    "sort": "@timestamp:desc"
                }
                
                hunt_response = await client._client.get(
                    f"{base_url}connect/events",
                    headers=headers,
                    params=hunt_params
                )
                
                if hunt_response.status_code != 200:
                    return f"Error searching related events: HTTP {hunt_response.status_code}"
                
                hunt_data = hunt_response.json()
                hunt_events = hunt_data.get('events', [])
                
                if not hunt_events:
                    return f"No related events found for community_id: {community_id}"
                
                # Format JSON response
                if hunt_events:
                    json_str = json.dumps({"events": hunt_events}, indent=2)
                    
                    # Verify JSON is valid
                    try:
                        json.loads(json_str)  # Test parse the JSON
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON content: {e}")
                        return "Error: Failed to generate valid JSON content"
                    
                    # Try sending as code block first
                    if len(json_str) <= 1990:  # Leave room for code block markers
                        return f"```json\n{json_str}\n```"
                    
                    # If too large, send as file
                    tmp_path = None
                    try:
                        # Create temp file with unique name
                        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tmp:
                            logger.debug(f"Creating temporary file: {tmp.name}")
                            tmp.write(json_str)
                            tmp.flush()  # Ensure content is written to disk
                            tmp_path = tmp.name
                        
                        # Verify file was written and check size
                        if not os.path.exists(tmp_path):
                            logger.error(f"Failed to create temporary file: {tmp_path}")
                            return "Error: Failed to create temporary file"
                            
                        file_size = os.path.getsize(tmp_path)
                        logger.debug(f"Temporary file size: {file_size} bytes")
                        if file_size == 0:
                            logger.error("Temporary file is empty")
                            return "Error: Generated file is empty"
                        elif file_size > 10 * 1024 * 1024:  # 10MB limit
                            logger.error(f"File too large ({file_size} bytes)")
                            return "Error: Generated file exceeds size limit (10MB)"
                            
                        # Verify platform is configured
                        if not platform:
                            logger.error("No platform specified for file send")
                            return "Error: No platform specified for file send"
                            
                        # Get service to verify it exists
                        service = chat_manager.get_service(platform)
                        if not service:
                            logger.error(f"Chat service not found for platform: {platform}")
                            return f"Error: Chat service not found for platform: {platform}"
                            
                        logger.debug(f"Sending file through {platform} service")
                        # Send file using chat manager
                        sent = await chat_manager.send_file(
                            platform,
                            tmp_path,
                            f'hunt_results_{eventid}.txt',
                            channel_id
                        )
                        
                        if sent:
                            return "Hunt results have been attached as a text file (response too large for message)."
                        return f"Error: Could not send file to {platform} channel"
                    except Exception as e:
                        logger.error(f"Error handling hunt results file: {e}")
                        return f"Error processing hunt results: {str(e)}"
                    finally:
                        # Always clean up temp file
                        if tmp_path and os.path.exists(tmp_path):
                            try:
                                os.unlink(tmp_path)
                                logger.debug(f"Cleaned up temporary file: {tmp_path}")
                            except Exception as e:
                                logger.error(f"Failed to clean up temporary file {tmp_path}: {e}")
                return "No events found"
                
            except json.JSONDecodeError:
                return f"Error parsing event data for ID: {eventid}"
                
        except httpx.HTTPError as e:
            return f"Error querying Security Onion: {str(e)}"
            
    except Exception as e:
        return f"Error processing hunt command: {str(e)}"
