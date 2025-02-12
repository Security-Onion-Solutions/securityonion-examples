"""Discord bot client implementation."""
import json
import asyncio
from typing import Optional, Dict, Any
import discord
from ..services.settings import get_setting
from ..database import AsyncSessionLocal

class DiscordClient:
    """Discord bot client implementation."""
    
    def __init__(self):
        """Initialize the Discord client."""
        self.client: Optional[discord.Client] = None
        self._status = "not initialized"
        self._enabled = False
        self._bot_token = None
        self._command_prefix = "!"  # Store prefix as instance variable
        self._alert_channel_id = None
        self._alert_notifications = False
        
    async def initialize(self) -> None:
        """Initialize the Discord client with settings from the database."""
        try:
            async with AsyncSessionLocal() as db:
                # Get Discord settings
                discord_setting = await get_setting(db, "DISCORD")
                if not discord_setting:
                    self._status = "no settings found"
                    return
                
                settings_dict = json.loads(discord_setting.value)
                self._enabled = settings_dict.get("enabled", False)
                self._bot_token = settings_dict.get("botToken", "")
                self._command_prefix = settings_dict.get("commandPrefix", "!")
                self._alert_notifications = settings_dict.get("alertNotifications", False)
                self._alert_channel_id = settings_dict.get("alertChannel", "")
                
                if not self._enabled:
                    self._status = "disabled"
                    return
                    
                if not self._bot_token:
                    self._status = "no bot token configured"
                    return
                
                # Initialize Discord client
                print("[DEBUG] Initializing Discord client...")
                intents = discord.Intents.default()
                intents.message_content = True
                self.client = discord.Client(intents=intents)
                print("[DEBUG] Client initialized with default intents")
                
                # Set up event handlers
                @self.client.event
                async def on_ready():
                    print(f"Discord bot logged in as {self.client.user}")
                    self._status = "connected"

                @self.client.event
                async def on_message(message):
                    """Handle incoming messages."""
                    print(f"\n[DEBUG] === New Message ===")
                    print(f"[DEBUG] Content: {message.content}")
                    print(f"[DEBUG] Author: {message.author} (ID: {message.author.id})")
                    print(f"[DEBUG] Bot User: {self.client.user} (ID: {self.client.user.id})")
                    print(f"[DEBUG] Channel: {message.channel}")
                    
                    # Ignore messages from the bot itself
                    if message.author == self.client.user:
                        print("[DEBUG] Ignoring message from self")
                        return

                    # Don't process !ping since it's handled by discord.py's built-in handler
                    if message.content.strip().lower() == "!ping":
                        print("[DEBUG] Ignoring !ping command - handled by discord.py")
                        return

                    # Process other commands that start with our command prefix
                    if message.content.startswith(self._command_prefix):
                        print(f"[DEBUG] Processing command: {message.content}")
                        try:
                            # Use ChatServiceManager for message handling
                            from .chat_manager import chat_manager
                            discord_service = chat_manager.get_service("DISCORD")
                            if not discord_service:
                                print("[DEBUG] Discord service not available")
                                return

                            # Process command through chat service
                            error = await discord_service.process_command(
                                command=message.content,
                                user_id=str(message.author.id),
                                username=str(message.author),
                                channel_id=str(message.channel.id)
                            )
                            if error:
                                print(f"[DEBUG] Error processing command: {error}")
                                await message.channel.send(error)
                                
                        except Exception as e:
                            error_msg = f"Error processing command: {str(e)}"
                            print(f"[DEBUG] {error_msg}")
                            print(f"[DEBUG] Exception type: {type(e)}")
                            await message.channel.send(error_msg)
                
                # Start the client in a separate task
                self._status = "connecting..."
                
                async def start_client():
                    try:
                        await self.client.start(self._bot_token)
                    except Exception as e:
                        self._status = f"error: {str(e)}"
                        print(f"Discord connection error: {str(e)}")
                
                asyncio.create_task(start_client())
                
        except Exception as e:
            self._status = f"error: {str(e)}"
            raise
    
    async def close(self) -> None:
        """Close the Discord client connection."""
        if self.client:
            await self.client.close()
            self._status = "closed"
    
    def _chunk_message(self, text: str, chunk_size: int = 1990) -> list[str]:
        """Split a message into chunks that fit within Discord's character limit.
        
        Args:
            text: The text to split into chunks
            chunk_size: Maximum size of each chunk (default 1990 to allow for code block markers)
            
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

    async def send_message(self, message: str, channel_id: str = None) -> bool:
        """Send a message to a Discord channel.
        
        Args:
            message: The message to send
            channel_id: Optional channel ID. If not provided, uses the alert channel
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if not (self.client and self.client.is_ready()):
            print("[DEBUG] Cannot send message - Discord not properly configured")
            return False
            
        try:
            # Use alert channel if no specific channel provided
            channel = None
            if channel_id:
                channel = self.client.get_channel(int(channel_id))
            elif self._alert_channel_id:
                channel = self.client.get_channel(int(self._alert_channel_id))
                
            if not channel:
                print("[DEBUG] Could not find channel to send message")
                return False
                
            await channel.send(message)
            return True
        except Exception as e:
            print(f"[DEBUG] Error sending message: {str(e)}")
            return False
            
    async def send_alert(self, alert_text: str) -> bool:
        """Send an alert to the configured Discord channel.
        
        Args:
            alert_text: The formatted alert text to send
            
        Returns:
            bool: True if alert was sent successfully, False otherwise
        """
        if not (self._enabled and self._alert_notifications and self._alert_channel_id and self.client and self.client.is_ready()):
            print("[DEBUG] Cannot send alert - Discord not properly configured")
            return False
            
        try:
            channel = self.client.get_channel(int(self._alert_channel_id))
            if not channel:
                print(f"[DEBUG] Could not find channel with ID {self._alert_channel_id}")
                return False
            
            # Split message into chunks
            chunks = self._chunk_message(alert_text)
            print(f"[DEBUG] Split alert into {len(chunks)} chunks")
            
            # Send each chunk
            for i, chunk in enumerate(chunks, 1):
                print(f"[DEBUG] Sending chunk {i} to Discord...")
                try:
                    # Wrap in code block for better formatting
                    formatted_chunk = f"```\n{chunk}\n```"
                    await channel.send(formatted_chunk)
                    print(f"[DEBUG] Successfully sent chunk {i}")
                except Exception as e:
                    print(f"[DEBUG] Error sending chunk {i} to Discord: {str(e)}")
                    print(f"[DEBUG] Failed to send chunk {i}")
                    return False
            
            return True
        except Exception as e:
            print(f"[DEBUG] Error sending alert: {str(e)}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the Discord client."""
        return {
            "status": self._status,
            "enabled": self._enabled,
            "connected": self.client is not None and self.client.is_ready() if self.client else False,
            "alert_notifications": self._alert_notifications,
            "alert_channel_configured": bool(self._alert_channel_id)
        }

# Create global client instance
client = DiscordClient()
