# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

from ...models.chat_users import ChatService
import json
import httpx
import ipaddress
import asyncio
from ...core.securityonion import client
from ...core.chat_manager import chat_manager
from ...core.decorators import requires_permission
from .validation import command_validator

async def _apply_suppression(base_url: str, headers: dict, rule_id: str, detection: dict, track_type: str, ip_cidr: str) -> str:
    """Apply a suppression rule asynchronously.
    
    Args:
        base_url: The base URL for the Security Onion API
        headers: The headers to use for the API request
        rule_id: The rule ID to suppress
        detection: The detection rule data
        track_type: The type of tracking (by_src, by_dst, by_either)
        ip_cidr: The IP/CIDR to suppress
        
    Returns:
        str: A message indicating success or failure
    """
    try:
        # Create new override
        new_override = {
            "type": "suppress",
            "track": track_type,
            "ip": ip_cidr,
            "isEnabled": True,
            "note": f"Suppression added via !detections command for {ip_cidr}"
        }
        
        # Add to existing overrides or create new array
        overrides = detection.get("overrides") or []
        overrides.append(new_override)
        
        # Prepare update payload with all required fields
        update_payload = {
            **detection,
            "overrides": overrides
        }
        
        # Update the detection
        print("\n=== DETECTION UPDATE REQUEST ===")
        print(f"URL: {base_url}connect/detection/")
        print(f"Request Method: PUT")
        print(f"Headers: {json.dumps(headers, indent=2)}")
        print(f"Request Body: {json.dumps(update_payload, indent=2)}")
        
        # Use the same verify setting as the main client
        verify = getattr(client._client, 'verify', False)
        async with httpx.AsyncClient(verify=verify) as async_client:
            # Use the base detection endpoint for updates
            update_url = f"{base_url}connect/detection/"
            print(f"\n=== Using update URL: {update_url} ===")
            print(f"Rule internal ID: {detection.get('id')}")
            
            update_response = await async_client.put(
                update_url,
                headers=headers,
                json=update_payload,
                timeout=60.0
            )
            
            print("\n=== DETECTION UPDATE RESPONSE ===")
            print(f"Status Code: {update_response.status_code}")
            print(f"Response Headers: {dict(update_response.headers)}")
            print(f"Response Content: {update_response.text}")
            
            if update_response.status_code in [200, 205, 206]:
                return f"✅ Suppression has been successfully added for rule {rule_id} with {track_type} {ip_cidr}"
            else:
                error_data = update_response.json() if update_response.headers.get('content-type', '').startswith('application/json') else None
                error_msg = error_data.get('detail') if error_data else f"Status code: {update_response.status_code}"
                print(f"\n=== ERROR DETAILS ===")
                print(f"Error Data: {json.dumps(error_data, indent=2) if error_data else 'No error data'}")
                return f"❌ Failed to add suppression for rule {rule_id}. {error_msg}"
                
    except Exception as e:
        print(f"\n=== SUPPRESSION ERROR ===")
        print(f"Error: {str(e)}")
        return f"❌ Error while applying suppression: {str(e)}"

@requires_permission()  # Detections command permission is already defined in COMMAND_PERMISSIONS
@command_validator(required_args=2, optional_args=2)  # Minimum: action + ruleid, Optional: track_type + ip/cidr
async def process(command: str, platform: str, user_id: str = None, username: str = None, channel_id: str = None) -> str:
    """Process the detections command.
    
    Args:
        command: The command string to process
        platform: The platform the command is coming from (discord/slack)
        user_id: The platform-specific user ID
        username: The user's display name
    """
    # Parse command arguments
    parts = command.split()
    if len(parts) < 2:
        return "Usage: !detections <enable|disable|summary|suppress> <publicid> [by_src|by_dst|by_either] [ip|cidr]"
        
    action = parts[1].lower()
    
    # Validate action and parameters
    if action == "suppress":
        if len(parts) != 5:
            return "Usage: !detections suppress <ruleid> <by_src|by_dst|by_either> <ip|cidr>"
        
        rule_id = parts[2]
        track_type = parts[3].lower()
        ip_cidr = parts[4]
        
        if track_type not in ["by_src", "by_dst", "by_either"]:
            return "Invalid track type. Use 'by_src', 'by_dst', or 'by_either'"
            
        try:
            # If no CIDR notation provided, append /32
            if '/' not in ip_cidr:
                ip_cidr = f"{ip_cidr}/32"
            
            # Validate IP/CIDR format
            network = ipaddress.ip_network(ip_cidr)
            # Convert to proper CIDR format
            ip_cidr = str(network)
        except ValueError:
            return "Invalid IP/CIDR format. Use x.x.x.x/y format (e.g. 192.168.1.1/32)"
    else:
        if len(parts) != 3:
            return "Usage: !detections <enable|disable|summary> <publicid>"
            
        rule_id = parts[2]
        
        if action not in ["enable", "disable", "summary"]:
            return "Invalid action. Use 'enable', 'disable', 'summary', or 'suppress'"
            
    
    try:
        # Ensure we have a valid connection
        if not client._connected:
            return "Error: Not connected to Security Onion"
            
        # Get the detection first
        base_url = client._base_url.rstrip('/') + '/'
        headers = client._get_headers()
        
        try:
            # Get the detection using public ID
            get_response = await client._client.get(
                f"{base_url}connect/detection/public/{rule_id}",
                headers=headers,
                timeout=60.0  # Increase timeout to 60 seconds
            )
            
            if get_response.status_code != 200:
                error_data = get_response.json() if get_response.headers.get('content-type', '').startswith('application/json') else None
                error_msg = error_data.get('detail') if error_data else f"Status code: {get_response.status_code}"
                return f"Error: Detection rule with public ID {rule_id} not found. {error_msg}"
                
            detection = get_response.json()
            
            # If this is a summary request, return the title and aiSummary
            if action == "summary":
                title = detection.get("title", "No title available")
                ai_summary = detection.get("aiSummary", "No AI summary available")
                return f"Detection Rule {rule_id}:\nTitle: {title}\nSummary: {ai_summary}"
            
            # For suppress action, start async task and return immediately
            if action == "suppress":
                print("\n=== SUPPRESSION REQUEST ===")
                print(f"Starting async suppression for rule {rule_id} with {track_type} {ip_cidr}")
                
                # Create task for async suppression
                task = asyncio.create_task(_apply_suppression(
                    base_url=base_url,
                    headers=headers,
                    rule_id=rule_id,
                    detection=detection,
                    track_type=track_type,
                    ip_cidr=ip_cidr
                ))
                
                # Add callback to handle the result
                async def handle_result(task):
                    try:
                        result = await task
                        # Send notification through chat manager
                        await chat_manager.send_message(platform, result, channel_id)
                    except Exception as e:
                        print(f"Error in suppression callback: {str(e)}")
                        error_msg = f"❌ Error in suppression: {str(e)}"
                        await chat_manager.send_message(platform, error_msg, channel_id)
                
                task.add_done_callback(lambda t: asyncio.create_task(handle_result(t)))
                
                return f"⏳ Adding suppression for rule {rule_id} with {track_type} {ip_cidr}..."
                
            # Start with the original detection data
            update_payload = detection.copy()
            
            # Update only the necessary fields
            update_payload.update({
                "operation": "update",
                "isEnabled": action == "enable"  # Set based on action
            })
            
            # Debug logging
            print("\n=== ORIGINAL DETECTION ===")
            print(f"Original isEnabled: {detection.get('isEnabled')}")
            print(f"Original fields: {sorted(detection.keys())}")
            print("\n=== UPDATE PAYLOAD ===")
            print(f"New isEnabled: {update_payload['isEnabled']}")
            print(f"Updated fields: {sorted(update_payload.keys())}")
            
            # Update the detection
            print("\n=== DETECTION UPDATE REQUEST ===")
            print(f"URL: {base_url}connect/detection/")
            print(f"Request Method: PUT")
            print(f"Headers: {json.dumps(headers, indent=2)}")
            print(f"Request Body: {json.dumps(update_payload, indent=2)}")
            
            # Use the base detection endpoint for updates
            update_url = f"{base_url}connect/detection/"
            print(f"\n=== Using update URL: {update_url} ===")
            print(f"Rule internal ID: {detection.get('id')}")
            
            update_response = await client._client.put(
                update_url,
                headers=headers,
                json=update_payload,
                timeout=60.0  # Increase timeout to 60 seconds
            )
            
            print("\n=== DETECTION UPDATE RESPONSE ===")
            print(f"Status Code: {update_response.status_code}")
            print(f"Response Headers: {dict(update_response.headers)}")
            print(f"Response Content: {update_response.text}")
            
            if update_response.status_code in [200, 205, 206]:
                if action == "suppress":
                    return f"✅ Successfully added suppression for rule {rule_id} with {track_type} {ip_cidr}"
                return f"✅ Successfully {action}d detection rule {rule_id}"
            else:
                error_data = None
                try:
                    if update_response.headers.get('content-type', '').startswith('application/json'):
                        error_data = update_response.json()
                    else:
                        error_data = {"detail": update_response.text}
                except json.JSONDecodeError:
                    error_data = {"detail": update_response.text}
                
                error_msg = error_data.get('detail') if error_data else f"Status code: {update_response.status_code}"
                print(f"\n=== ERROR DETAILS ===")
                print(f"Error Data: {json.dumps(error_data, indent=2) if error_data else 'No error data'}")
                print(f"Response Content: {update_response.text}")
                print(f"Content Type: {update_response.headers.get('content-type')}")
                
                if action == "suppress":
                    return f"❌ Failed to add suppression for rule {rule_id}. Error: {error_msg}"
                return f"❌ Failed to {action} detection rule {rule_id}. Error: {error_msg}"
                
        except httpx.HTTPError as e:
            # Get the response if available
            response = getattr(e, 'response', None)
            if response:
                try:
                    print("\n=== HTTP ERROR DETAILS ===")
                    print(f"Status Code: {response.status_code}")
                    print(f"Response Headers: {dict(response.headers)}")
                    print(f"Response Content: {response.text}")
                    
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else None
                    error_msg = error_data.get('detail') if error_data else response.text
                    return f"HTTP error while updating detection (Status {response.status_code}): {error_msg}"
                except json.JSONDecodeError:
                    return f"HTTP error while updating detection (Status {response.status_code}): {response.text}"
                except Exception as inner_e:
                    return f"HTTP error while updating detection (Status {response.status_code}): {str(inner_e)}"
            
            print(f"\n=== HTTP ERROR FULL DETAILS ===")
            print(f"Error type: {type(e)}")
            print(f"Error message: {str(e)}")
            print(f"Error attributes: {dir(e)}")
            return f"HTTP error while updating detection: {str(e)}"
            
        except json.JSONDecodeError as e:
            return f"Invalid JSON response while updating detection: {str(e)}"
            
    except Exception as e:
        return f"Unexpected error: {str(e)}"
