"""Chat service manager implementation."""
from typing import Dict, Optional
import logging
from ..models.chat_users import ChatService
from .chat_services import BaseChatService, get_chat_service

logger = logging.getLogger(__name__)


class ChatServiceManager:
    """Manager class for handling all chat platform interactions."""
    
    def __init__(self):
        """Initialize the chat service manager."""
        self._services: Dict[str, BaseChatService] = {}
        
        # Initialize all available services
        for service in ChatService:
            try:
                self._services[service.value] = get_chat_service(service)
            except ValueError:
                # Skip unsupported services
                continue

    def get_service(self, platform: str) -> Optional[BaseChatService]:
        """Get the chat service for a specific platform.
        
        Args:
            platform: The platform identifier (e.g., 'DISCORD', 'SLACK')
            
        Returns:
            Optional[BaseChatService]: The chat service if available, None otherwise
        """
        try:
            # Convert string to enum if needed
            if isinstance(platform, str):
                platform = ChatService(platform.upper())
            return self._services.get(platform.value)
        except ValueError:
            logger.error(f"Invalid platform: {platform}")
            return None

    async def send_file(self, platform: str, file_path: str, filename: str, channel_id: str = None) -> bool:
        """Send a file through the specified chat platform.
        
        Args:
            platform: The platform to send through (e.g., 'DISCORD', 'SLACK')
            file_path: Path to the file to send
            filename: Name to give the file when sending
            channel_id: Optional channel ID. If not provided, uses default channel
            
        Returns:
            bool: True if file was sent successfully, False otherwise
        """
        service = self.get_service(platform)
        if not service:
            logger.error(f"No chat service found for platform: {platform}")
            return False
            
        logger.debug(f"Routing file send through {platform} service")
        return await service.send_file(file_path, filename, channel_id)

    async def send_message(self, platform: str, message: str, channel_id: str = None) -> bool:
        """Send a message through the specified chat platform.
        
        Args:
            platform: The platform to send through (e.g., 'DISCORD', 'SLACK')
            message: The message to send
            channel_id: Optional channel ID. If not provided, uses default channel
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        service = self.get_service(platform)
        if service:
            return await service.send_message(message, channel_id)
        return False

    async def format_message(self, platform: str, message: str) -> Optional[str]:
        """Format a message for the specified chat platform.
        
        Args:
            platform: The platform to format for (e.g., 'DISCORD', 'SLACK')
            message: The message to format
            
        Returns:
            Optional[str]: The formatted message if service available, None otherwise
        """
        service = self.get_service(platform)
        if service:
            return await service.format_message(message)
        return None

    async def validate_user_id(self, platform: str, user_id: str) -> bool:
        """Validate a user ID for the specified chat platform.
        
        Args:
            platform: The platform to validate for (e.g., 'DISCORD', 'SLACK')
            user_id: The user ID to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        service = self.get_service(platform)
        if service:
            return await service.validate_user_id(user_id)
        return False

    async def get_display_name(self, platform: str, user_id: str) -> Optional[str]:
        """Get a user's display name from the specified chat platform.
        
        Args:
            platform: The platform to get the name from (e.g., 'DISCORD', 'SLACK')
            user_id: The user ID to get the name for
            
        Returns:
            Optional[str]: The display name if available, None otherwise
        """
        service = self.get_service(platform)
        if service:
            return await service.get_display_name(user_id)
        return None


# Create global chat manager instance
chat_manager = ChatServiceManager()
