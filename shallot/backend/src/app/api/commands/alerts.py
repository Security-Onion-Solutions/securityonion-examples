from ...models.chat_users import ChatService
from datetime import datetime, timedelta
import json
import httpx
from ...core.securityonion import client
from ...core.chat_manager import chat_manager
from .validation import command_validator
from ...core.permissions import CommandPermission
from ...core.decorators import requires_permission

@requires_permission()  # Alerts command permission is already defined in COMMAND_PERMISSIONS
@command_validator(required_args=0, optional_args=0)
async def process(command: str, user_id: str = None, platform: ChatService = None, username: str = None, channel_id: str = None) -> str:
    """Process the alerts command.
    
    Args:
        command: The command string to process
        platform: The platform the command is coming from (discord/slack)
        user_id: The platform-specific user ID
        username: The user's display name
        
    Usage: !alerts
    """
    try:
        # Ensure we have a valid connection
        if not client._connected:
            return "Error: Not connected to Security Onion"
        
        # Query alerts from Security Onion
        base_url = client._base_url.rstrip('/') + '/'
        
        # Use the correct Security Onion events endpoint
        alert_endpoints = [
            'connect/events'  # Security Onion events endpoint
        ]
        response = None
        
        for endpoint in alert_endpoints:
            try:
                print(f"\nTrying endpoint: {base_url}{endpoint}")
                headers = client._get_headers()
                print(f"Request headers: {headers}")
                
                # Get current time for date range in UTC
                now = datetime.utcnow()
                time_24h_ago = now - timedelta(hours=24)
                
                # Format parameters for Security Onion API
                query_params = {
                    "query": "tags:alert AND NOT event.acknowledged:true",  # Only unacknowledged alerts
                    "range": f"{time_24h_ago.strftime('%Y/%m/%d %I:%M:%S %p')} - {now.strftime('%Y/%m/%d %I:%M:%S %p')}",
                    "zone": "UTC",  # Timezone for the range
                    "format": "2006/01/02 3:04:05 PM",  # Time format specification
                    "fields": "*",  # Request all fields to ensure we get everything we need
                    "metricLimit": "10000",
                    "eventLimit": "5",  # Limit to 5 alerts for !alerts command
                    "sort": "@timestamp:desc"  # Newest first
                }
                
                # Print the actual query parameters for debugging
                print(f"\nQuery parameters: {query_params}")
                
                # Make GET request with URL parameters
                response = await client._client.get(
                    f"{base_url}{endpoint}",
                    headers=headers,
                    params=query_params
                )
                print(f"\nResponse status: {response.status_code}")
                print(f"Response headers: {dict(response.headers)}")
                print(f"Response content: {response.text}")  # Show full response for debugging
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print("Available fields in response:", list(data.keys()))
                        
                        events = data.get('events', [])
                        if not events:
                            print("No events found in response. Response structure:", json.dumps(data, indent=2))
                            continue

                        if not isinstance(events, list):
                            print(f"Events data is not a list. Got {type(events)}")
                            continue

                        # Process each alert individually
                        alerts = []
                        for event in events:
                            try:
                                if not isinstance(event, dict):
                                    print(f"Event is not a dict: {event}")
                                    continue

                                # Debug log the event structure
                                print(f"\nProcessing event: {json.dumps(event, indent=2)}")
                                
                                # Get the payload data
                                payload = event.get('payload', {})
                                print(f"\nPayload fields: {list(payload.keys())}")
                                print(f"\nFull payload data: {json.dumps(payload, indent=2)}")
                                print(f"\nFull event data: {json.dumps(event, indent=2)}")
                                print(f"\nTimestamp fields in payload: {[k for k in payload.keys() if 'timestamp' in k.lower()]}")
                                print(f"\nTimestamp fields in event: {[k for k in event.keys() if 'timestamp' in k.lower()]}")
                                
                                # Parse the message field which contains the alert data
                                message_str = payload.get('message', '{}')
                                try:
                                    message = json.loads(message_str)
                                    print(f"\nParsed message fields: {list(message.keys())}")
                                    print(f"\nFull message data: {json.dumps(message, indent=2)}")
                                    print(f"\nLog data if exists: {json.dumps(message.get('log', {}), indent=2)}")
                                    
                                    # Get alert data from the message
                                    alert_data = message.get('alert', {})
                                    if alert_data:
                                        severity_label = payload.get('event.severity_label', 'UNKNOWN')  # Get severity_label directly from payload
                                        alerts.append({
                                            'name': alert_data.get('signature', 'Untitled Alert'),
                                            'severity_label': severity_label,
                                            'ruleid': alert_data.get('signature_id', 'Unknown'),
                                            'eventid': payload.get('log.id.uid', 'Unknown'),
                                            'source_ip': message.get('src_ip', 'Unknown'),
                                            'source_port': str(message.get('src_port', 'Unknown')),
                                            'destination_ip': message.get('dest_ip', 'Unknown'),
                                            'destination_port': str(message.get('dest_port', 'Unknown')),
                                            'observer_name': payload['observer.name'] if 'observer.name' in payload else 'Unknown',
                                            'timestamp': event.get('@timestamp') or
                                                        event.get('timestamp') or
                                                        payload.get('@timestamp') or
                                                        payload.get('timestamp') or
                                                        'Unknown'
                                        })
                                except json.JSONDecodeError:
                                    print("Failed to parse message as JSON:", message_str)
                            except Exception as e:
                                print(f"Error processing event: {str(e)}\nEvent data: {json.dumps(event, indent=2)}")
                                continue
                        
                        if len(alerts) > 0:
                            # Format alerts for display
                            alert_lines = ["Here are the newest 5 alerts:"]
                            
                            for alert in alerts:
                                # Add a blank line before each alert except the first one
                                if len(alert_lines) > 1:
                                    alert_lines.append("")
                                alert_lines.extend([
                                    f"[{alert['severity_label']}] - {alert['name']}",
                                    f"  ruleid: {alert['ruleid']}",
                                    f"  eventid: {alert['eventid']}",
                                    f"  source: {alert['source_ip']}:{alert['source_port']}",
                                    f"  destination: {alert['destination_ip']}:{alert['destination_port']}",
                                    f"  observer.name: {alert['observer_name']}",
                                    f"  timestamp: {alert['timestamp']}"
                                ])
                            
                            alert_text = "\n".join(alert_lines)
                            print(f"\nFormatted alert text:\n{alert_text}")
                            
                            # Just return the formatted alerts - don't send separately
                            return alert_text
                        
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse JSON from {endpoint}: {str(e)}")
                        print(f"Raw response content: {response.text}")
                        continue
            except Exception as e:
                print(f"Error with endpoint {endpoint}: {str(e)}")
                continue
        
        # If we tried all endpoints and none worked
        if response:
            try:
                data = response.json()
                print("Final response data:", json.dumps(data, indent=2))
                return f"No alerts found in the last 24 hours. Total events: {data.get('totalEvents', 0)}"
            except Exception as e:
                print(f"Failed to parse final response: {str(e)}")
                print(f"Response content: {response.text}")
                error_msg = f"Error: Failed to parse response from Security Onion. Status: {response.status_code}. Error: {str(e)}"
                return error_msg
        return "Error: Could not establish connection with Security Onion API"
    except httpx.HTTPError as e:
        return f"Error: Failed to connect to Security Onion API: {str(e)}"
