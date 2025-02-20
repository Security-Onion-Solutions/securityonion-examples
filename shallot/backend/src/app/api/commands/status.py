# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

from ...core.securityonion import client
from ...core.permissions import CommandPermission
from ...core.decorators import requires_permission
from ...models.chat_users import ChatService

@requires_permission()  # Status command permission is already defined in COMMAND_PERMISSIONS
async def process(command: str, user_id: str = None, platform: ChatService = None, username: str = None, user_type: str = None, channel_id: str = None) -> str:
    """Process the status command.
    
    Args:
        command: The command string to process
        user_id: The platform-specific user ID
        platform: The platform the command is coming from (discord/slack/matrix)
        username: The user's display name
    """
    if client._connected:
        return "All systems operational. Security Onion connection active."
    return "Warning: Security Onion connection not available."
