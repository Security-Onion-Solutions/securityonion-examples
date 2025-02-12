from abc import ABC, abstractmethod
from typing import Optional, Any
import logging
import json
import os
import mimetypes
import nio  # matrix-nio library for Matrix protocol

from ..models.chat_users import ChatService, ChatUser, ChatUserRole

logger = logging.getLogger(__name__)


class BaseChatService(ABC):
    """Base class for chat service implementations."""
    
    def __init__(self, service: ChatService):
        self.service = service

    @abstractmethod
    async def format_message(self, message: str) -> str:
        """Format a message for the specific chat service."""
        pass

    @abstractmethod
    async def validate_user_id(self, user_id: str) -> bool:
        """Validate a user ID for the specific chat service."""
        pass

    @abstractmethod
    async def get_display_name(self, user_id: str) -> Optional[str]:
        """Get the display name for a user if available."""
        pass

    @abstractmethod
    async def send_file(self, file_path: str, filename: str, channel_id: str = None) -> bool:
        """Send a file to the chat service.
        
        Args:
            file_path: Path to the file to send
            filename: Name to give the file when sending
            channel_id: Optional channel ID. If not provided, uses default channel
            
        Returns:
            bool: True if file was sent successfully, False otherwise
        """
        pass

    @abstractmethod
    async def send_message(self, message: str, channel_id: str = None) -> bool:
        """Send a message to the chat service.
        
        Args:
            message: The message to send
            channel_id: Optional channel ID. If not provided, uses default channel
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        pass

    @abstractmethod
    async def process_command(self, command: str, user_id: str, username: str = None, channel_id: str = None, display_name: str = None, platform: ChatService = None) -> Optional[str]:
        """Process a command from the chat service.
        
        Args:
            command: The command text to process
            user_id: The platform-specific user ID
            username: The raw username of the user
            channel_id: Optional channel ID where command was received
            display_name: Optional display name of the user (human-readable name)
            platform: Optional platform override, defaults to service's platform
            
        Returns:
            Optional[str]: Response message if any, None if no response needed
        """
        pass


class DiscordService(BaseChatService):
    """Discord-specific chat service implementation."""
    
    def __init__(self):
        super().__init__(ChatService.DISCORD)

    async def format_message(self, message: str) -> str:
        """Format a message for Discord."""
        return message  # Discord can handle plain text

    async def validate_user_id(self, user_id: str) -> bool:
        """Validate a Discord user ID."""
        return user_id.isdigit()  # Discord IDs are numeric

    async def get_display_name(self, user_id: str) -> Optional[str]:
        """Get Discord user's display name."""
        return None  # Implement Discord-specific logic here

    async def send_file(self, file_path: str, filename: str, channel_id: str = None) -> bool:
        """Send a file through Discord."""
        from .discord import client
        if not (client.client and client.client.is_ready()):
            return False
        
        try:
            from discord import File as DiscordFile
            channel = None
            if channel_id:
                channel = client.client.get_channel(int(channel_id))
            elif client._alert_channel_id:
                channel = client.client.get_channel(int(client._alert_channel_id))
                
            if not channel:
                return False
                
            await channel.send(file=DiscordFile(file_path, filename=filename))
            return True
        except Exception:
            return False

    async def send_message(self, message: str, channel_id: str = None) -> bool:
        """Send a message through Discord."""
        from .discord import client
        return await client.send_message(message, channel_id)

    async def process_command(self, command: str, user_id: str, username: str = None, channel_id: str = None, display_name: str = None, platform: ChatService = None) -> Optional[str]:
        """Process a command from Discord."""
        from ..api.commands import process_command
        response = await process_command(
            command=command,
            platform=platform or self.service,
            user_id=user_id,
            username=username,
            display_name=display_name
        )
        if response:
            formatted_response = await self.format_message(response)
            if await self.send_message(formatted_response, channel_id):
                return None  # Message sent successfully
            return "Failed to send response"
        return None


class SlackService(BaseChatService):
    """Slack-specific chat service implementation."""
    
    def __init__(self):
        super().__init__(ChatService.SLACK)

    async def format_message(self, message: str) -> str:
        """Format a message for Slack."""
        return message  # Slack can handle plain text

    async def validate_user_id(self, user_id: str) -> bool:
        """Validate a Slack user ID."""
        return user_id.startswith('U')  # Slack user IDs start with 'U'

    async def get_display_name(self, user_id: str) -> Optional[str]:
        """Get Slack user's display name using proper field priority."""
        from .slack import client
        if not client.client:
            return None
        user_info = await client.get_user_info(user_id)
        if user_info:
            return (
                user_info.get("real_name") or
                user_info["profile"].get("real_name") or
                user_info["profile"].get("display_name") or
                user_info.get("name")
            )
        return None

    async def send_file(self, file_path: str, filename: str, channel_id: str = None) -> bool:
        """Send a file through Slack."""
        from .slack import client
        channel = channel_id or client._alert_channel
        if not (client.client and channel):
            return False
            
        try:
            await client.upload_file(file_path, filename, channel)
            return True
        except Exception:
            return False

    async def send_message(self, message: str, channel_id: str = None) -> bool:
        """Send a message through Slack."""
        from .slack import client
        channel = channel_id or client._alert_channel
        if not (client.client and channel):
            return False
            
        try:
            await client.client.chat_postMessage(channel=channel, text=message)
            return True
        except Exception:
            return False

    async def process_command(self, command: str, user_id: str, username: str = None, channel_id: str = None, display_name: str = None, platform: ChatService = None) -> Optional[str]:
        """Process a command from Slack."""
        from ..api.commands import process_command
        print(f"[DEBUG] SlackService processing command with platform: {platform}, fallback: {self.service}")
        final_platform = platform or self.service
        print(f"[DEBUG] Using platform: {final_platform}, type: {type(final_platform)}")
        response = await process_command(
            command=command,
            platform=final_platform,
            user_id=user_id,
            username=username,
            display_name=display_name
        )
        if response:
            formatted_response = await self.format_message(response)
            if await self.send_message(formatted_response, channel_id):
                return None  # Message sent successfully
            return "Failed to send response"
        return None


class MatrixService(BaseChatService):
    """Matrix-specific chat service implementation."""
    
    def __init__(self):
        super().__init__(ChatService.MATRIX)

    async def format_message(self, message: str) -> str:
        """Format a message for Matrix."""
        return message  # Matrix can handle plain text

    async def validate_user_id(self, user_id: str) -> bool:
        """Validate a Matrix user ID."""
        return '@' in user_id and ':' in user_id  # Matrix IDs are in @user:domain format

    async def get_display_name(self, user_id: str) -> Optional[str]:
        """Get Matrix user's display name."""
        return None  # Implement Matrix-specific logic here

    async def send_file(self, file_path: str, filename: str, channel_id: str = None) -> bool:
        """Send a file through Matrix."""
        from .matrix import client
        if not (client._enabled and client.client and (channel_id or client._alert_room)):
            logger.debug("Cannot send file - Matrix not properly configured")
            return False
            
        try:
            # Check if file exists and verify content
            import os
            if not os.path.exists(file_path):
                logger.error(f"File does not exist: {file_path}")
                return False
                
            # Check file size (10MB limit is common for Matrix servers)
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                logger.error("File is empty")
                return False
            elif file_size > 10 * 1024 * 1024:  # 10MB in bytes
                logger.error(f"File too large ({file_size} bytes) - Matrix servers typically have a 10MB limit")
                return False
                
            # Verify file content for JSON files
            if file_path.endswith('.json'):
                try:
                    with open(file_path, 'r') as f:
                        json.load(f)  # Test parse the JSON
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON content: {e}")
                    return False
                
            # Verify and normalize room ID
            room_id = channel_id or client._alert_room
            if not room_id:
                logger.error("No room ID provided and no alert room configured")
                return False
                
            # Matrix room IDs must start with ! and contain :
            if not (room_id.startswith('!') and ':' in room_id):
                logger.error(f"Invalid Matrix room ID format: {room_id}")
                return False
                
            # First verify we have permission to send to this room
            if not await client.join_room(room_id):
                logger.error(f"Failed to verify room permissions for {room_id}")
                return False
                
            logger.debug(f"Attempting to upload file {filename} to Matrix")
            # Upload file to get content URI and encryption info
            upload_result = await client.upload_file(file_path, filename, room_id)
            if not upload_result:
                logger.error("Failed to get content URI from file upload")
                return False
                
            # Get mime type for file info
            if file_path.endswith('.txt'):
                # Force text/plain for txt files
                detected_mime_type = 'text/plain'
            else:
                detected_mime_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
            file_size = os.path.getsize(file_path)
            logger.debug(f"Using mime type {detected_mime_type} for file {filename}")
            
            # Unpack the upload result
            content_uri, encryption_info = upload_result
                
            if not content_uri:
                logger.error("Failed to extract content URI from upload result")
                return False
                
            logger.debug(f"Successfully got content URI: {content_uri}")
                
            # Send file message
            room_id = channel_id or client._alert_room
            logger.debug(f"Sending file message to room {room_id}")
            
            # Construct file message content
            content = {
                "msgtype": "m.file",
                "body": filename,
                "url": content_uri,
                "filename": filename,
                "info": {
                    "mimetype": detected_mime_type,
                    "size": file_size
                }
            }
            
            logger.debug(f"Sending unencrypted file message with content: {json.dumps(content)}")
            response = await client.client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content=content
            )
            
            if isinstance(response, nio.RoomSendError):
                logger.error(f"Failed to send file message: {type(response)} - {response.message}")
                return False
                
            logger.debug("Successfully sent file message")
            return True
            
        except Exception as e:
            logger.error(f"Error sending file through Matrix: {e}")
            return False

    async def send_message(self, message: str, channel_id: str = None) -> bool:
        """Send a message through Matrix."""
        from .matrix import client
        return await client.send_message(channel_id or client._alert_room, message)

    async def process_command(self, command: str, user_id: str, username: str = None, channel_id: str = None, display_name: str = None, platform: ChatService = None) -> Optional[str]:
        """Process a command from Matrix."""
        from ..api.commands import process_command
        response = await process_command(
            command=command,
            platform=platform or self.service,
            user_id=user_id,
            username=username,
            display_name=display_name
        )
        if response:
            formatted_response = await self.format_message(response)
            if await self.send_message(formatted_response, channel_id):
                return None  # Message sent successfully
            return "Failed to send response"
        return None


class TeamsService(BaseChatService):
    """Microsoft Teams-specific chat service implementation."""
    
    def __init__(self):
        super().__init__(ChatService.TEAMS)

    async def format_message(self, message: str) -> str:
        """Format a message for Teams."""
        return message  # Teams can handle plain text

    async def validate_user_id(self, user_id: str) -> bool:
        """Validate a Teams user ID."""
        return True  # Implement Teams-specific validation

    async def get_display_name(self, user_id: str) -> Optional[str]:
        """Get Teams user's display name."""
        return None  # Implement Teams-specific logic here

    async def send_file(self, file_path: str, filename: str, channel_id: str = None) -> bool:
        """Send a file through Teams."""
        # TODO: Implement Teams file sending
        return False

    async def send_message(self, message: str, channel_id: str = None) -> bool:
        """Send a message through Teams."""
        # TODO: Implement Teams message sending
        return False

    async def process_command(self, command: str, user_id: str, username: str = None, channel_id: str = None, display_name: str = None, platform: ChatService = None) -> Optional[str]:
        """Process a command from Teams."""
        from ..api.commands import process_command
        response = await process_command(
            command=command,
            platform=platform or self.service,
            user_id=user_id,
            username=username,
            display_name=display_name
        )
        if response:
            formatted_response = await self.format_message(response)
            if await self.send_message(formatted_response, channel_id):
                return None  # Message sent successfully
            return "Failed to send response"
        return None


def get_chat_service(service: ChatService) -> BaseChatService:
    """Factory function to get the appropriate chat service implementation."""
    service_map = {
        ChatService.DISCORD: DiscordService,
        ChatService.SLACK: SlackService,
        ChatService.MATRIX: MatrixService,
        ChatService.TEAMS: TeamsService,
    }
    
    service_class = service_map.get(service)
    if not service_class:
        raise ValueError(f"Unsupported chat service: {service}")
    
    return service_class()
