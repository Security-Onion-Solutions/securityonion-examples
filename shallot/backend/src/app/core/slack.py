"""Slack client implementation."""
import json
import asyncio
from typing import Optional, Dict, Any
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.errors import SlackApiError

from ..services.settings import get_setting
from ..database import AsyncSessionLocal

class SlackClient:
    """Slack client implementation."""
    
    def __init__(self):
        """Initialize the Slack client."""
        self.client: Optional[AsyncWebClient] = None
        self._status = "not initialized"
        self._enabled = False
        self._bot_token = None
        self._alert_channel = None
        self._alert_notifications = False
        self._command_prefix = "!"  # Default prefix
        self._app_token = None
        self._socket_client: Optional[SocketModeClient] = None
        self._web_client_connected = False
        self._socket_mode_connected = False
        
    async def initialize(self) -> None:
        """Initialize the Slack client with settings from the database."""
        try:
            async with AsyncSessionLocal() as db:
                # Get Slack settings
                slack_setting = await get_setting(db, "SLACK")
                if not slack_setting:
                    self._status = "no settings found"
                    return
                
                settings_dict = json.loads(slack_setting.value)
                print(f"[DEBUG] Loaded Slack settings: {json.dumps(settings_dict, indent=2)}")
                self._enabled = settings_dict.get("enabled", False)
                self._bot_token = settings_dict.get("botToken", "")
                self._alert_channel = settings_dict.get("alertChannel", "")
                self._alert_notifications = settings_dict.get("alertNotifications", False)
                self._command_prefix = settings_dict.get("commandPrefix", "!")
                self._app_token = settings_dict.get("appToken", "")
                print(f"[DEBUG] Using command prefix: '{self._command_prefix}'")
                
                if not self._enabled:
                    self._status = "disabled"
                    return
                    
                if not self._bot_token:
                    self._status = "no bot token configured"
                    return

                if not self._app_token:
                    self._status = "no app token configured"
                    return

                # Initialize Slack clients
                print(f"[DEBUG] Initializing Slack clients with bot token: {self._bot_token[:5]}... and app token: {self._app_token[:5]}...")
                self.client = AsyncWebClient(token=self._bot_token)
                
                # Verify bot has required scopes
                try:
                    auth_test = await self.client.auth_test()
                    print(f"[DEBUG] Connected as: {auth_test['user_id']} to workspace: {auth_test['team']}")
                    self._web_client_connected = True
                except SlackApiError as e:
                    self._status = "error: invalid bot token or missing scopes"
                    print(f"[DEBUG] Auth test failed: {str(e)}")
                    raise
                
                self._socket_client = SocketModeClient(
                    app_token=self._app_token,
                    web_client=self.client
                )
                
                # Setup socket mode handler
                self._socket_client.socket_mode_request_listeners.append(
                    self._handle_socket_request
                )
                
                # Start socket mode client
                await self._socket_client.connect()
                self._socket_mode_connected = True
                self._status = "initialized"
                print("[DEBUG] Slack clients initialized and connected")
                
        except Exception as e:
            self._status = f"error: {str(e)}"
            raise
    
    async def close(self) -> None:
        """Close the Slack client connections."""
        if self._socket_client:
            await self._socket_client.disconnect()
            self._socket_client = None
        if self.client:
            self.client = None
        self._status = "closed"
    
    def _chunk_message(self, text: str, chunk_size: int = 35000) -> list[str]:
        """Split a message into chunks that fit within Slack's message size limit.
        
        Args:
            text: The text to split into chunks
            chunk_size: Maximum size of each chunk (default 35000 to stay under 40KB limit)
            
        Returns:
            list[str]: List of message chunks
        """
        chunks = []
        lines = text.split('\n')
        current_chunk = []
        current_length = 0
        
        for line in lines:
            # Add newline to line length except for the first line
            line_length = len(line) + (1 if current_length > 0 else 0)
            
            if current_length + line_length > chunk_size:
                # Join current chunk and add to chunks list
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_length = len(line)
            else:
                current_chunk.append(line)
                current_length += line_length
        
        # Add the last chunk if there is one
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks

    async def upload_file(self, file_path: str, filename: str, channel: str) -> bool:
        """Upload a file to a Slack channel using files_upload_v2.
        
        Args:
            file_path: Path to the file to upload
            filename: Name to give the file in Slack
            channel: Channel ID to upload the file to
            
        Returns:
            bool: True if upload was successful, False otherwise
        """
        if not (self._enabled and self.client and channel):
            print("[DEBUG] Cannot upload file - Slack not properly configured")
            return False
            
        try:
            # Read file content
            with open(file_path, 'r') as file:
                content = file.read()

            # Extract base filename without extension
            base_filename = filename.rsplit('.', 1)[0]

            # Upload using files_upload_v2
            response = await self.client.files_upload_v2(
                channel=channel,
                file_uploads=[{
                    "content": content,
                    "filename": filename,
                    "title": f"Hunt results for {base_filename}",
                    "initial_comment": f"Hunt results for {base_filename}"
                }]
            )
            
            if not response["ok"]:
                print(f"[DEBUG] Failed to upload file: {response.get('error', 'Unknown error')}")
                return False
                
            return True
        except Exception as e:
            print(f"[DEBUG] Error uploading file to Slack: {str(e)}")
            return False

    async def send_message(self, message: str, channel: str = None) -> bool:
        """Send a message to a Slack channel.
        
        Args:
            message: The message to send
            channel: Optional channel ID. If not provided, uses the alert channel
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if not (self._enabled and self.client):
            print("[DEBUG] Cannot send message - Slack not properly configured")
            return False
            
        try:
            # Use alert channel if no specific channel provided
            target_channel = channel or self._alert_channel
            if not target_channel:
                print("[DEBUG] No channel available to send message")
                return False
                
            response = await self.client.chat_postMessage(
                channel=target_channel,
                text=message
            )
            return response["ok"]
        except Exception as e:
            print(f"[DEBUG] Error sending message: {str(e)}")
            return False
            
    async def send_alert(self, alert_text: str) -> bool:
        """Send an alert to the configured Slack channel.
        
        Args:
            alert_text: The formatted alert text to send
            
        Returns:
            bool: True if alert was sent successfully, False otherwise
        """
        if not (self._enabled and self._alert_notifications and self._alert_channel and self.client):
            print("[DEBUG] Cannot send alert - Slack not properly configured")
            return False
            
        try:
            # Split message into chunks
            chunks = self._chunk_message(alert_text)
            print(f"[DEBUG] Split alert into {len(chunks)} chunks")
            
            # Send each chunk
            for i, chunk in enumerate(chunks, 1):
                print(f"[DEBUG] Sending chunk {i} to Slack...")
                try:
                    # Format as code block for better readability
                    formatted_chunk = f"```\n{chunk}\n```"
                    response = await self.client.chat_postMessage(
                        channel=self._alert_channel,
                        text=formatted_chunk
                    )
                    if not response["ok"]:
                        print(f"[DEBUG] Failed to send chunk {i}")
                        return False
                    print(f"[DEBUG] Successfully sent chunk {i}")
                except SlackApiError as e:
                    print(f"[DEBUG] Error sending chunk {i} to Slack: {str(e)}")
                    return False
            
            return True
        except Exception as e:
            print(f"[DEBUG] Error sending alert: {str(e)}")
            return False

    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information from Slack API.
        
        Args:
            user_id: The Slack user ID to look up
            
        Returns:
            Dict containing user information if successful, None otherwise
        """
        if not (self._enabled and self.client):
            print("[DEBUG] Cannot get user info - Slack not properly configured")
            return None
            
        try:
            response = await self.client.users_info(user=user_id)
            if response["ok"]:
                return response["user"]
            return None
        except Exception as e:
            print(f"[DEBUG] Error getting user info: {str(e)}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the Slack client."""
        return {
            "status": self._status,
            "enabled": self._enabled,
            "web_client_connected": self._web_client_connected,
            "socket_mode_connected": self._socket_mode_connected,
            "alert_notifications": self._alert_notifications,
            "alert_channel_configured": bool(self._alert_channel),
            "command_prefix": self._command_prefix
        }

    async def _handle_socket_request(self, client: SocketModeClient, req) -> None:
        """Handle incoming socket mode requests."""
        try:
            print(f"[DEBUG] Received socket request: type={req.type}")
            print(f"[DEBUG] Full request: {req}")
            print(f"[DEBUG] Payload: {json.dumps(req.payload, indent=2)}")
            
            # Handle URL verification challenge
            if req.type == "url_verification":
                print("[DEBUG] Handling URL verification challenge")
                response = SocketModeResponse(envelope_id=req.envelope_id)
                response.payload = {"challenge": req.payload.get("challenge")}
                await client.send_socket_mode_response(response)
                return
                
            # Acknowledge other requests
            response = SocketModeResponse(envelope_id=req.envelope_id)
            await client.send_socket_mode_response(response)
            
            # Process the event if it's a message (handle both 'events' and 'events_api' types)
            if (req.type in ["events", "events_api"]) and req.payload.get("event"):
                event = req.payload["event"]
                print(f"[DEBUG] Processing event type: {event.get('type')}")
                
                # Check if this is a bot message
                if event.get("bot_id"):
                    print("[DEBUG] Ignoring bot message")
                    return
                    
                # Handle different event types
                event_type = event.get("type")
                if event_type == "app_mention":
                    print("[DEBUG] Handling app mention event")
                    # For app mentions, we need to strip the bot mention from the text
                    text = event.get("text", "")
                    print(f"[DEBUG] Raw app mention text: '{text}'")
                    
                    # Extract bot ID for better mention handling
                    auth_test = await self.client.auth_test()
                    bot_id = auth_test["user_id"]
                    print(f"[DEBUG] Bot ID: {bot_id}")
                    
                    # Remove the bot mention (e.g., <@U1234>)
                    mention_pattern = f"<@{bot_id}>"
                    if mention_pattern in text:
                        text = text.replace(mention_pattern, "").strip()
                    else:
                        # Try generic split if exact mention not found
                        text = text.split(">", 1)[-1].strip()
                    print(f"[DEBUG] Cleaned app mention text: '{text}'")
                    
                    event["text"] = text
                elif event_type == "message":
                    if event.get("subtype") == "message_changed":
                        print("[DEBUG] Handling message_changed event")
                        # Get the new message text
                        if "message" in event and "text" in event["message"]:
                            event["text"] = event["message"]["text"]
                        else:
                            print("[DEBUG] No message text in message_changed event")
                            return
                
                await self._handle_message(event)
            else:
                print(f"[DEBUG] Ignoring non-event request of type: {req.type}")
        except Exception as e:
            print(f"[DEBUG] Error in socket request handler: {str(e)}")
            raise

    async def _handle_message(self, event: Dict) -> None:
        """Process incoming Slack messages."""
        print(f"\n[DEBUG] === New Slack Message ===")
        print(f"[DEBUG] Event: {json.dumps(event, indent=2)}")
        
        try:
            # Verify message is valid
            event_type = event.get("type")
            if event_type not in ["message", "app_mention"]:
                print(f"[DEBUG] Ignoring event of type: {event_type}")
                return
                
            if "subtype" in event:
                print(f"[DEBUG] Ignoring message with subtype: {event.get('subtype')}")
                return
                
            if not event.get("text"):
                print("[DEBUG] Ignoring message with no text")
                return
            
            text = event.get("text", "")
            channel = event.get("channel")
            user_id = event.get("user")
            
            print(f"[DEBUG] Message text: '{text}'")
            print(f"[DEBUG] Command prefix: '{self._command_prefix}'")
            
            # For app mentions, treat the mention itself as the prefix
            if event_type == "app_mention":
                if not text:
                    print("[DEBUG] Empty text in app mention")
                    return
            # For regular messages, check command prefix
            elif not text.startswith(self._command_prefix):
                print("[DEBUG] Message does not start with command prefix")
                return
                
            # For app mentions, add the command prefix if it's not there
            if event_type == "app_mention" and not text.startswith(self._command_prefix):
                text = f"{self._command_prefix}{text}"
                # Update the event text so command processing sees the modified version
                event["text"] = text
                
            print(f"[DEBUG] Processing Slack command: {text}")
            
            # Get user info
            user_info = await self.get_user_info(user_id)
            # Default to user_id for username if we can't get user info
            username = user_id
            display_name = None
            
            if user_info:
                # Get username and display name from user info
                username = user_info.get("name", user_id)  # Basic username
                # Get display name with proper priority of fields
                display_name = (
                    user_info.get("real_name") or  # Try user's real_name first
                    user_info["profile"].get("real_name") or  # Then profile real_name
                    user_info["profile"].get("display_name") or  # Then display name
                    user_info.get("name") or  # Then username
                    user_id  # Finally fall back to user ID
                )
                print(f"[DEBUG] Using username: {username}, display_name: {display_name}")
                print(f"[DEBUG] Full user info: {user_info}")

            # Use ChatServiceManager for message handling
            from .chat_manager import chat_manager
            from ..models.chat_users import ChatService
            slack_service = chat_manager.get_service("SLACK")
            if not slack_service:
                print("[DEBUG] Slack service not available")
                return

            # Process command through chat service with both username and display_name
            try:
                print(f"[DEBUG] Sending command to service with username: {username}")
                print(f"[DEBUG] Sending command to service with platform: {ChatService.SLACK}")
                error = await slack_service.process_command(
                    command=text,
                    user_id=user_id,
                    username=username,
                    channel_id=channel,
                    display_name=display_name,
                    platform=ChatService.SLACK  # Explicitly pass the enum
                )
                if error:
                    print(f"[DEBUG] Error processing command: {error}")
                    await self.client.chat_postMessage(
                        channel=channel,
                        text=error
                    )
            except Exception as e:
                print(f"[DEBUG] Error in process_command: {str(e)}")
                raise
                
        except Exception as e:
            error_msg = f"Error processing command: {str(e)}"
            print(f"[DEBUG] {error_msg}")
            if channel:
                await self.client.chat_postMessage(
                    channel=channel,
                    text=error_msg
                )

# Create global client instance
client = SlackClient()

