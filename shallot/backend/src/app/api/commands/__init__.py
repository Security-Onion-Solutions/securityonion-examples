# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

from .core import router
from typing import Optional, Union
import json
import logging
from ...services.settings import get_setting
from ...models.chat_users import ChatService
from ...services.chat_permissions import check_command_permission
from ...schemas.commands import Command, AVAILABLE_COMMANDS
from ...core.permissions import CommandPermission

logger = logging.getLogger(__name__)

async def process_command(
    command: str,
    platform: Union[str, ChatService],
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    user_type: Optional[str] = None,
    channel_id: Optional[str] = None,
    display_name: Optional[str] = None,
    **kwargs
) -> str:
    """
    Process a command and return the response.
    
    Args:
        command: The command string to process
        platform: The platform the command is coming from (discord, slack)
        user_id: The platform-specific user ID
        username: The user's raw username
        user_type: Optional user type
        channel_id: Optional channel ID
        display_name: Optional display name (human-readable name)
    """
    # Get platform settings
    from ...database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        # Get platform value for settings lookup
        platform_value = platform.value if isinstance(platform, ChatService) else platform.upper()
        platform_settings = await get_setting(db, platform_value)
        if not platform_settings:
            return f"Error: {platform} settings not found"
        
        try:
            settings = json.loads(platform_settings.value)
            command_prefix = settings.get("commandPrefix", "!")
        except (json.JSONDecodeError, KeyError):
            return f"Error: Invalid {platform} settings"

    try:
        # Clean and normalize command text
        command = command.strip()
        print(f"[DEBUG] Raw command: '{command}'")
        
        # Convert to lowercase for case-insensitive matching
        command_lower = command.lower()
        prefix_lower = command_prefix.lower()
        
        # Check prefix with detailed logging
        if not command_lower.startswith(prefix_lower):
            print(f"[DEBUG] Command '{command_lower}' doesn't start with prefix '{prefix_lower}'")
            print(f"[DEBUG] Command chars: {[ord(c) for c in command_lower[:len(prefix_lower)]]}")
            print(f"[DEBUG] Prefix chars: {[ord(c) for c in prefix_lower]}")
            return f"Commands must start with {command_prefix}"
            
        # Get command name preserving original case
        command_text = command[len(command_prefix):].strip()  # Remove prefix and trim
        if not command_text:
            print("[DEBUG] Empty command after prefix")
            return "Please provide a command. Try !help to see available commands."
            
        command_parts = command_text.split()
        command_name = command_parts[0].lower()  # Get first word as command name
        print(f"[DEBUG] Command name: '{command_name}', Args: {command_parts[1:] if len(command_parts) > 1 else []}")
    except Exception as e:
        print(f"[DEBUG] Error parsing command text: {str(e)}")
        return f"Error parsing command: {str(e)}"
    
    try:
        print(f"[DEBUG] Attempting to import command module: app.api.commands.{command_name}")
        
        # Import all command modules
        try:
            from . import help, register, status, alerts, ack, detections, hunt, escalate, whois, dig
            print("[DEBUG] Successfully imported all command modules")
        except ImportError as e:
            print(f"[DEBUG] Error importing command modules: {str(e)}")
            return f"Error loading commands: {str(e)}"
            
        # Get command definition from AVAILABLE_COMMANDS
        command_def = next((cmd for cmd in AVAILABLE_COMMANDS if cmd.name == command_name), None)
        if command_def:
            logger.debug(f"Found command definition for {command_name}")
            logger.debug(f"Command permission: {command_def.permission}")
        else:
            logger.error(f"No command definition found for {command_name}")
            return f"Unknown command: {command_name}. Try !help to see available commands."

        # Map command names to modules
        command_modules = {
            "help": help,
            "register": register,
            "status": status,
            "alerts": alerts,
            "ack": ack,
            "detections": detections,
            "hunt": hunt,
            "escalate": escalate,
            "whois": whois,
            "dig": dig
        }
        
        # Check if command exists and get module
        if command_name not in command_modules:
            logger.error(f"Command module not found for {command_name}")
            return f"Unknown command: {command_name}. Try !help to see available commands."
            
        command_module = command_modules[command_name]
        logger.debug(f"Found command module for: {command_name}")
        logger.debug(f"Command definition: {command_def}")
        
        # Execute the command
        try:
            print(f"[DEBUG] Executing command: {command} for platform: {platform}, user: {user_id}")
            # Convert platform string to ChatService enum if needed
            try:
                if isinstance(platform, str):
                    platform_enum = ChatService(platform.upper())
                else:
                    platform_enum = platform  # Already a ChatService enum
                print(f"[DEBUG] Platform enum: {platform_enum}, type: {type(platform_enum)}, value: {platform_enum!r}")
                print(f"[DEBUG] User type in process_command: {user_type}")
                print(f"[DEBUG] Username: {username}, Display name: {display_name}")
            except ValueError as e:
                print(f"[DEBUG] Error converting platform to enum: {str(e)}")
                return f"Error: Invalid platform {platform}"
            # Only pass display_name to register command
            if command_name == "register":
                response = await command_module.process(
                    command=command,
                    user_id=user_id,
                    platform=platform_enum,
                    username=username,
                    user_type=user_type,
                    channel_id=channel_id,
                    display_name=display_name
                )
            else:
                response = await command_module.process(
                    command=command,
                    user_id=user_id,
                    platform=platform_enum,
                    username=username,
                    user_type=user_type,
                    channel_id=channel_id
                )
            print(f"[DEBUG] Command executed successfully, response length: {len(response) if response else 0}")
            return response
        except Exception as e:
            print(f"[DEBUG] Error executing command: {str(e)}")
            return f"Error executing command: {str(e)}"
            
    except Exception as e:
        print(f"[DEBUG] Unexpected error in command processing: {str(e)}")
        return f"Internal error: {str(e)}"

__all__ = ["router", "process_command"]
