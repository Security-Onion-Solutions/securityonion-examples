"""Matrix integration for Security Onion Chat Bot."""
from typing import Optional, Dict, Any
import json
import logging
import asyncio
import nio  # matrix-nio library for Matrix protocol

from ..models.settings import Settings
from ..services.settings import get_setting
from ..database import AsyncSessionLocal
from .chat_services import MatrixService
from ..api.commands import process_command

logger = logging.getLogger(__name__)


class MatrixClient:
    """Matrix client for handling bot interactions."""

    def __init__(self):
        """Initialize Matrix client."""
        self.client: Optional[nio.AsyncClient] = None
        self._status = "not initialized"
        self._enabled = False
        self._homeserver_url = None
        self._user_id = None
        self._access_token = None
        self._device_id = None
        self._alert_room = None
        self._alert_notifications = False
        self._command_prefix = "!"  # Default prefix
        self._background_tasks: set[asyncio.Task] = set()

    async def initialize(self) -> None:
        """Initialize the Matrix client with settings from the database."""
        try:
            async with AsyncSessionLocal() as db:
                # Get Matrix settings
                matrix_setting = await get_setting(db, "MATRIX")
                if not matrix_setting:
                    self._status = "no settings found"
                    return
                
                settings_dict = json.loads(matrix_setting.value)
                logger.debug(f"Loaded Matrix settings: {json.dumps(settings_dict, indent=2)}")
                
                self._enabled = settings_dict.get("enabled", False)
                self._homeserver_url = settings_dict.get("homeserverUrl", "")
                self._user_id = settings_dict.get("userId", "")
                self._access_token = settings_dict.get("accessToken", "")
                self._device_id = settings_dict.get("deviceId", "")
                self._alert_room = settings_dict.get("alertRoom", "")
                self._alert_notifications = settings_dict.get("alertNotifications", False)
                self._command_prefix = settings_dict.get("commandPrefix", "!")
                
                if not self._enabled:
                    self._status = "disabled"
                    return
                    
                if not all([self._homeserver_url, self._user_id, self._access_token]):
                    self._status = "missing credentials"
                    return

                # Initialize client
                config = nio.AsyncClientConfig(
                    store_sync_tokens=True
                )

                # Create client
                self.client = nio.AsyncClient(
                    self._homeserver_url,
                    self._user_id,
                    device_id=self._device_id,
                    config=config
                )
                
                # Set up access token
                self.client.access_token = self._access_token
                self.client.user_id = self._user_id

                # Do initial sync first to get server state
                logger.info("[ENCRYPTION] Performing initial sync")
                sync_response = await self.client.sync(timeout=3000)
                if isinstance(sync_response, nio.SyncError):
                    raise Exception(f"Initial sync failed: {sync_response.message}")
                logger.info("[ENCRYPTION] Initial sync successful")

                # Join alert room if configured
                if self._alert_room:
                    join_success = await self.join_room(self._alert_room)
                    if join_success:
                        logger.info(f"Successfully joined alert room: {self._alert_room}")
                    else:
                        logger.error(f"Failed to join alert room: {self._alert_room}")

                # Start sync loop
                self._create_background_task(self._sync_loop())

                self._status = "initialized"
                logger.info("Matrix client initialized successfully")
                
        except Exception as e:
            self._status = f"error: {str(e)}"
            logger.error(f"Failed to initialize Matrix client: {e}")
            raise

    async def close(self) -> None:
        """Close the Matrix client connection."""
        if self.client:
            await self.client.close()
            self.client = None
        
        # Cancel any background tasks
        for task in self._background_tasks:
            task.cancel()
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()
        
        self._status = "closed"
        logger.info("Matrix client closed")

    async def _verify_sync_state(self) -> bool:
        """Verify the client's sync state is valid."""
        try:
            sync_response = await self.client.sync(timeout=3000, full_state=False)
            if isinstance(sync_response, nio.SyncError):
                logger.error(f"Failed to verify Matrix sync state: {sync_response.message}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error verifying Matrix sync state: {e}")
            return False

    async def upload_file(self, file_path: str, filename: str = None, room_id: str = None) -> Optional[tuple[str, Optional[dict]]]:
        """Upload a file to the Matrix server.
        
        Args:
            file_path: Path to the file to upload
            filename: Optional name to give the file
            room_id: Optional room ID to check encryption status
            
        Returns:
            Optional[tuple[str, Optional[dict]]]: Tuple of (content_uri, encryption_info) if successful,
                                                or None if upload failed. encryption_info may be None
                                                for unencrypted uploads.
        """
        if not self._enabled:
            logger.error("Matrix service is not enabled")
            return None
            
        if not self.client:
            logger.error("Matrix client is not initialized")
            return None
            
        if self._status != "initialized":
            logger.error(f"Matrix client is in invalid state: {self._status}")
            return None
            
        # Verify sync state before proceeding
        if not await self._verify_sync_state():
            logger.error("Matrix client sync state verification failed")
            return None
            
        # Verify client is still connected by checking last sync
        try:
            sync_response = await self.client.sync(timeout=3000, full_state=False)
            if isinstance(sync_response, nio.SyncError):
                logger.error(f"Failed to verify Matrix connection: {sync_response.message}")
                return None
        except Exception as e:
            logger.error(f"Error verifying Matrix connection: {e}")
            return None
            
        try:
            import mimetypes
            # Force text/plain for .txt files
            if file_path.endswith('.txt'):
                mime_type = 'text/plain'
            else:
                mime_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
            logger.debug(f"Using mime type {mime_type} for file {file_path}")
            
            with open(file_path, 'rb') as f:
                logger.debug(f"Opening file {file_path} for upload")
                # Force unencrypted upload
                response = await self.client.upload(
                    f,
                    content_type=mime_type,
                    filename=filename or file_path.split('/')[-1],
                    encrypt=False
                )
                logger.debug("Successfully uploaded file without encryption")
                
            # Handle both encrypted and unencrypted responses
            if isinstance(response, tuple):
                # Encrypted upload returns (UploadResponse, encryption_dict)
                upload_response, encryption_dict = response
                if isinstance(upload_response, nio.UploadResponse):
                    logger.debug(f"File uploaded with encryption: {encryption_dict}")
                    return (upload_response.content_uri, encryption_dict)
            elif isinstance(response, nio.UploadResponse):
                # Unencrypted upload returns just UploadResponse
                return (response.content_uri, None)
                
            logger.error(f"Failed to upload file: {type(response)} - {response}")
            return None
                
        except Exception as e:
            logger.error(f"Error uploading file: {type(e)} - {str(e)}")
            return None

    async def send_message(self, room_id: str, content: str) -> bool:
        """Send a message to a Matrix room."""
        if not (self._enabled and self.client and room_id):
            logger.debug("Cannot send message - Matrix not properly configured")
            return False

        try:
            response = await self.client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": content,
                    "format": "org.matrix.custom.html",
                    "formatted_body": f"<pre><code>{content}</code></pre>"
                }
            )
            
            if isinstance(response, nio.RoomSendError):
                logger.error(f"Failed to send message: {response.message}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Matrix message: {e}")
            return False

    async def send_alert(self, alert_text: str) -> bool:
        """Send an alert to the configured Matrix room."""
        if not (self._enabled and self._alert_notifications and self._alert_room):
            logger.debug("Cannot send alert - Matrix not properly configured")
            return False
            
        try:
            formatted_text = f"```\n{alert_text}\n```"
            return await self.send_message(self._alert_room, formatted_text)
            
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return False

    async def join_room(self, room_id: str) -> bool:
        """Join a Matrix room and verify permissions."""
        if not (self._enabled and self.client):
            logger.debug("Cannot join room - Matrix not properly configured")
            return False
            
        try:
            # First try to join the room
            response = await self.client.join(room_id)
            if isinstance(response, nio.JoinError):
                logger.error(f"Failed to join room: {response.message}")
                return False
                
            logger.debug(f"Successfully joined room {room_id}")
            
            # Get room state to verify permissions
            try:
                state = await self.client.room_get_state(room_id)
                if isinstance(state, nio.RoomGetStateError):
                    logger.error(f"Failed to get room state: {state.message}")
                    return False
                    
                # Check if we have permission to send messages and files
                power_levels = next((event for event in state.events if event.type == "m.room.power_levels"), None)
                if power_levels:
                    events = power_levels.content.get("events", {})
                    send_messages = events.get("m.room.message", 0)
                    logger.debug(f"Required power level for sending messages: {send_messages}")
                    if send_messages > 0:
                        logger.error(f"Insufficient power level for sending messages in room {room_id}")
                        return False
                
                return True
                
            except Exception as e:
                logger.error(f"Error checking room permissions: {e}")
                # If we can't check permissions, assume we can send
                return True
            
        except Exception as e:
            logger.error(f"Error joining room: {e}")
            return False

    async def _sync_loop(self) -> None:
        """Background task to sync with Matrix server."""
        while self._enabled and self.client:
            try:
                sync_response = await self.client.sync(timeout=30000)
                if isinstance(sync_response, nio.SyncError):
                    logger.error(f"Sync failed: {sync_response.message}")
                    continue

                # Handle room invites
                for room_id in sync_response.rooms.invite:
                    logger.info(f"Received invite to room {room_id}")
                    await self.join_room(room_id)
                
                # Handle messages in joined rooms
                for room_id, room in sync_response.rooms.join.items():
                    for event in room.timeline.events:
                        # Handle unencrypted text messages
                        if isinstance(event, nio.RoomMessageText):
                            await self._handle_message(room_id, event)
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                await asyncio.sleep(5)

    async def _handle_message(self, room_id: str, event: nio.RoomMessageText) -> None:
        """Process an incoming Matrix message."""
        try:
            if not event.body.startswith(self._command_prefix):
                return

            # Use ChatServiceManager for message handling
            from .chat_manager import chat_manager
            matrix_service = chat_manager.get_service("MATRIX")
            if not matrix_service:
                logger.error("Matrix service not available")
                return

            # Validate Matrix user ID format
            if not await matrix_service.validate_user_id(event.sender):
                logger.warning(f"Invalid Matrix user ID format: {event.sender}")
                return

            # Get display name if available
            display_name = await matrix_service.get_display_name(event.sender)
            username = display_name or event.sender.split(":")[0][1:]

            # Process command through chat service
            response = await process_command(
                command=event.body,
                platform="MATRIX",
                user_id=event.sender,
                username=username,
                channel_id=room_id
            )
            if response:
                await self.send_message(room_id, response)

        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            logger.error(error_msg)
            await self.send_message(room_id, error_msg)

    def get_status(self) -> Dict[str, Any]:
        """Get current connection status."""
        encryption_info = {}
        if self.client:
            encryption_info = {
                "device_id": self.client.device_id if hasattr(self.client, 'device_id') else None
            }
            logger.debug(f"Matrix encryption status: {encryption_info}")
            
        return {
            "status": self._status,
            "enabled": self._enabled,
            "connected": self.client is not None,
            "alert_notifications": self._alert_notifications,
            "alert_room_configured": bool(self._alert_room),
            "command_prefix": self._command_prefix,
            "encryption": encryption_info
        }

    def _create_background_task(self, coro) -> None:
        """Create a tracked background task."""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)


# Create global client instance
client = MatrixClient()
