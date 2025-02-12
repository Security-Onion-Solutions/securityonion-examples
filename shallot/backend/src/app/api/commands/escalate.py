from datetime import datetime, timedelta
from typing import List, Optional
from ...models.chat_users import ChatService
from ...schemas.commands import Command, CommandType
from . import process_command
from app.models.chat_users import ChatUserRole
from app.core.securityonion import client as so_client
from ...core.permissions import CommandPermission
from ...core.decorators import requires_permission
from .validation import command_validator

COMMAND = Command(
    name="escalate",
    description="Create a case from an event and include related events from the last 24 hours (max 100 events)",
    example="!escalate <eventid> [case title]"
)

@requires_permission()  # Escalate command permission is already defined in COMMAND_PERMISSIONS
@command_validator(
    required_args=1,  # eventid
    optional_args=1,  # title
    multi_word_arg_index=1  # Everything after eventid is the title
)
async def process(command: str, platform: str, user_id: str, username: str, channel_id: str = None) -> str:
    """Process the escalate command to create a case from an event."""
    try:
        # Parse command arguments
        args = command.split()[1:]  # Skip the command name
        if not args:
            return "Error: Event ID is required. Usage: !escalate <eventid> [case title]"
        
        eventid = args[0]
        print(f"[DEBUG] Processing escalate command for event ID: {eventid}")
        title = " ".join(args[1:]) if len(args) > 1 else None
        print(f"[DEBUG] Using title: {title}")

        # Initialize and check connection
        print("[DEBUG] Ensuring Security Onion client is initialized...")
        await so_client.initialize()
        print("[DEBUG] Client initialization complete")
        
        if not so_client._connected:
            return f"Error: Not connected to Security Onion - {so_client._last_error}"
        
        try:
            # Format base URL consistently
            base_url = so_client._base_url.rstrip('/') + '/'
            print(f"[DEBUG] Using base URL: {base_url}")
            
            # Get original event details
            query_params = {
                "query": f"log.id.uid:{eventid}",
                "fields": "*",
                "metricLimit": "10000",
                "eventLimit": "1"
            }
            print(f"[DEBUG] Querying event with params: {query_params}")
            
            event_url = f"{base_url}connect/events"
            print(f"[DEBUG] Event query URL: {event_url}")
            
            response = await so_client._client.get(
                event_url,
                headers=so_client._get_headers(),
                params=query_params
            )
            
            if response.status_code != 200:
                error_msg = f"Error querying event: HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    print(f"[DEBUG] Event query error response: {error_data}")
                    if isinstance(error_data, dict) and 'message' in error_data:
                        error_msg += f" - {error_data['message']}"
                except Exception as e:
                    print(f"[DEBUG] Failed to parse error response: {str(e)}")
                return error_msg
            
            data = response.json()
            events = data.get('events', [])
            
            if not events:
                return f"No event found with ID: {eventid}"
                
            event = events[0]
            if not event:
                return f"Error: Event {eventid} not found"

            # Use rule name as title if none provided
            if not title:
                title = event.get("rule.name", "Escalated Event")

            # Ensure token is valid before creating case
            if not await so_client._ensure_token():
                return f"Error creating case: Failed to obtain valid token - {so_client._last_error}"

            # Create case
            case_payload = {
                "title": title,
                "status": "new",
                "severity": "medium",
                "owner": username or "Unknown",
                "description": f"Case created from event {eventid}"
            }
            print(f"[DEBUG] Creating case with payload: {case_payload}")
            
            case_url = f"{base_url}connect/case"
            print(f"[DEBUG] Creating case with URL: {case_url}")
            
            # Get fresh headers with valid token
            headers = so_client._get_headers()
            print(f"[DEBUG] Request headers: {headers}")
            
            case_response = await so_client._client.post(
                case_url,
                headers=headers,
                json=case_payload
            )
            
            print(f"[DEBUG] Case creation response status: {case_response.status_code}")
            print(f"[DEBUG] Case creation response headers: {dict(case_response.headers)}")
            
            if case_response.status_code != 200:
                error_msg = f"Error creating case: HTTP {case_response.status_code}"
                
                # Get raw response content first
                raw_response = case_response.text
                print(f"[DEBUG] Case creation raw response: '{raw_response}'")
                
                # Only try JSON parsing if we have content
                if raw_response.strip():
                    try:
                        error_data = case_response.json()
                        print(f"[DEBUG] Case creation error response (parsed): {error_data}")
                        if isinstance(error_data, dict) and 'message' in error_data:
                            error_msg += f" - {error_data['message']}"
                    except Exception as e:
                        print(f"[DEBUG] Failed to parse error response: {str(e)}")
                        error_msg += f" - Raw response: {raw_response[:200]}"  # Include truncated raw response
                else:
                    print("[DEBUG] Case creation response was empty")
                    error_msg += " - Empty response from server"
                
                return error_msg
                
            case = case_response.json()
            if not case or 'id' not in case:
                return "Error: Invalid case response from server"

            # Initialize current time
            now = datetime.utcnow()

            # Extract network.communityid from the event
            payload = event.get('payload', {})
            print(f"[DEBUG] Event payload: {payload}")
            
            # Get community_id directly from payload
            community_id = payload.get('network.community_id')
            print(f"[DEBUG] Found community_id: {community_id}")
            if not community_id:
                # Add just the original event if no community ID
                payload = event.get('payload', {})
                if not isinstance(payload, dict):
                    return f"Error: Invalid event payload format for event {eventid}"
                
                # Extract fields from payload
                fields = {}
                if isinstance(payload, dict):
                    for key, value in payload.items():
                        # Convert nested fields to dot notation
                        if isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                fields[f"{key}.{subkey}"] = subvalue
                        else:
                            fields[key] = value
                
                print(f"[DEBUG] Adding original event with fields: {fields}")
                
                # Get event timestamp for date range
                event_time = datetime.strptime(event.get('timestamp', now.isoformat()), "%Y-%m-%dT%H:%M:%S.%fZ")
                time_range_start = event_time - timedelta(hours=24)
                time_range_end = event_time + timedelta(hours=24)
                
                event_payload = {
                    "caseId": case["id"],
                    "fields": fields,
                    "dateRange": f"{time_range_start.strftime('%Y/%m/%d %I:%M:%S %p')} - {time_range_end.strftime('%Y/%m/%d %I:%M:%S %p')}",
                    "dateRangeFormat": "2006/01/02 3:04:05 PM",
                    "timezone": "UTC"
                }
                print(f"[DEBUG] Adding event with payload: {event_payload}")
                
                # Ensure token is valid before adding event
                if not await so_client._ensure_token():
                    return f"Error adding event to case: Failed to obtain valid token - {so_client._last_error}"

                events_url = f"{base_url}connect/case/events"
                print(f"[DEBUG] Adding event to case with URL: {events_url}")
                
                # Get fresh headers with valid token
                headers = so_client._get_headers()
                print(f"[DEBUG] Request headers: {headers}")
                
                add_event_response = await so_client._client.post(
                    events_url,
                    headers=headers,
                    json=event_payload
                )
                
                print(f"[DEBUG] Add event response status: {add_event_response.status_code}")
                print(f"[DEBUG] Add event response headers: {dict(add_event_response.headers)}")
                
                if add_event_response.status_code != 200:
                    error_msg = f"Error adding event to case: HTTP {add_event_response.status_code}"
                    
                    # Get raw response content first
                    raw_response = add_event_response.text
                    print(f"[DEBUG] Add event raw response: '{raw_response}'")
                    
                    # Only try JSON parsing if we have content
                    if raw_response.strip():
                        try:
                            error_data = add_event_response.json()
                            print(f"[DEBUG] Event attachment error response (parsed): {error_data}")
                            if isinstance(error_data, dict) and 'message' in error_data:
                                error_msg += f" - {error_data['message']}"
                        except Exception as e:
                            print(f"[DEBUG] Failed to parse error response: {str(e)}")
                            error_msg += f" - Raw response: {raw_response[:200]}"  # Include truncated raw response
                    else:
                        print("[DEBUG] Add event response was empty")
                        error_msg += " - Empty response from server"
                    
                    return error_msg
                return f"Created case {case['id']} with original event (no community ID found for related events)"

            # Search for related events
            time_24h_ago = now - timedelta(hours=24)
            
            hunt_params = {
                "query": f"network\\.community_id:\"{community_id}\"",
                "range": f"{time_24h_ago.strftime('%Y/%m/%d %I:%M:%S %p')} - {now.strftime('%Y/%m/%d %I:%M:%S %p')}",
                "zone": "UTC",
                "format": "2006/01/02 3:04:05 PM",
                "fields": "*",
                "metricLimit": "10000",
                "eventLimit": "100",
                "sort": "@timestamp:desc",
                "aggregations": "false"
            }
            print(f"[DEBUG] Searching for related events with params: {hunt_params}")
            
            hunt_response = await so_client._client.get(
                f"{base_url}connect/events",
                headers=so_client._get_headers(),
                params=hunt_params
            )
            
            if hunt_response.status_code != 200:
                return f"Error searching related events: HTTP {hunt_response.status_code}"
            
            hunt_data = hunt_response.json()
            related_events = hunt_data.get('events', [])
            
            if not related_events:
                return f"No related events found for community_id: {community_id}"

            # Add all events to case
            event_count = 0
            for event in related_events:
                # Get fields from payload only
                payload = event.get('payload', {})
                if not isinstance(payload, dict):
                    print(f"[DEBUG] Skipping event - payload is not a dict")
                    continue
                
                # Extract fields from payload
                fields = {}
                if isinstance(payload, dict):
                    for key, value in payload.items():
                        # Convert nested fields to dot notation
                        if isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                fields[f"{key}.{subkey}"] = subvalue
                        else:
                            fields[key] = value
                
                print(f"[DEBUG] Adding event {event_count + 1} with fields: {fields}")
                # Get event timestamp for date range
                event_time = datetime.strptime(event.get('timestamp', now.isoformat()), "%Y-%m-%dT%H:%M:%S.%fZ")
                time_range_start = event_time - timedelta(hours=24)
                time_range_end = event_time + timedelta(hours=24)
                
                event_payload = {
                    "caseId": case["id"],
                    "fields": fields,
                    "dateRange": f"{time_range_start.strftime('%Y/%m/%d %I:%M:%S %p')} - {time_range_end.strftime('%Y/%m/%d %I:%M:%S %p')}",
                    "dateRangeFormat": "2006/01/02 3:04:05 PM",
                    "timezone": "UTC"
                }
                print(f"[DEBUG] Adding related event {event_count + 1} with payload: {event_payload}")
                
                # Ensure token is valid before adding related event
                if not await so_client._ensure_token():
                    return f"Error adding related event to case: Failed to obtain valid token - {so_client._last_error}"

                events_url = f"{base_url}connect/case/events"
                print(f"[DEBUG] Adding related event to case with URL: {events_url}")
                
                # Get fresh headers with valid token
                headers = so_client._get_headers()
                print(f"[DEBUG] Request headers: {headers}")
                
                add_event_response = await so_client._client.post(
                    events_url,
                    headers=headers,
                    json=event_payload
                )
                
                print(f"[DEBUG] Add related event response status: {add_event_response.status_code}")
                print(f"[DEBUG] Add related event response headers: {dict(add_event_response.headers)}")
                
                if add_event_response.status_code not in [200, 202]:
                    error_msg = f"Error adding related event to case: HTTP {add_event_response.status_code}"
                    
                    # Get raw response content first
                    raw_response = add_event_response.text
                    print(f"[DEBUG] Add related event raw response: '{raw_response}'")
                    
                    # Only try JSON parsing if we have content
                    if raw_response.strip():
                        try:
                            error_data = add_event_response.json()
                            print(f"[DEBUG] Related event attachment error response (parsed): {error_data}")
                            if isinstance(error_data, dict) and 'message' in error_data:
                                error_msg += f" - {error_data['message']}"
                        except Exception as e:
                            print(f"[DEBUG] Failed to parse error response: {str(e)}")
                            error_msg += f" - Raw response: {raw_response[:200]}"  # Include truncated raw response
                    else:
                        print("[DEBUG] Add related event response was empty")
                        error_msg += " - Empty response from server"
                    
                    return error_msg
                event_count += 1

            return f"Created case {case['id']} with {event_count} related events"

        except Exception as e:
            return f"Error creating case: {str(e)}"

    except Exception as e:
        return f"Error creating case: {str(e)}"
