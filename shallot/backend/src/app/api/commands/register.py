# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

from ...database import AsyncSessionLocal
from ...services.chat_users import get_chat_user_by_platform_id, create_chat_user
from ...models.chat_users import ChatService
from ...core.chat_services import get_chat_service
from ...core.permissions import CommandPermission
from ...core.decorators import requires_permission

@requires_permission()  # Register command permission is already defined in COMMAND_PERMISSIONS
async def process(
    command: str,
    user_id: str = None,
    platform: ChatService = None,
    username: str = None,
    channel_id: str = None,
    display_name: str = None
) -> str:
    """Process the register command."""
    print(f"[DEBUG] Register command received - user_id: {user_id}, username: {username}, platform: {platform}, display_name: {display_name}, platform type: {type(platform)}")
    if user_id is None or username is None:
        print(f"[DEBUG] Missing user information - user_id: {user_id}, username: {username}")
        return "Error: Missing user information"
    
    try:
        print(f"[DEBUG] Getting chat service for platform: {platform}, type: {type(platform)}, value: {platform!r}")
        # Platform should already be a ChatService enum from __init__.py
        chat_service = get_chat_service(platform)
        print(f"[DEBUG] Got chat service: {chat_service.service}")
    except ValueError as e:
        print(f"[DEBUG] Error getting chat service: {str(e)}")
        return f"Error: {str(e)}"
        
    # Validate user ID format
    if not await chat_service.validate_user_id(user_id):
        return f"Error: Invalid user ID format for {platform}"
        
    async with AsyncSessionLocal() as db:
        existing_user = await get_chat_user_by_platform_id(db, user_id, chat_service.service)
        if existing_user:
            return "You are already registered!"
            
        # Use provided display_name if available, otherwise try to get it from service
        final_display_name = display_name or await chat_service.get_display_name(user_id) or username
            
        await create_chat_user(
            db,
            platform_id=user_id,
            username=username,
            display_name=final_display_name,
            platform=chat_service.service
        )
        
        return "Registration successful! You now have access to public commands."
