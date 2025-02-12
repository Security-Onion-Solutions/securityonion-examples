from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.chat_users import ChatUser, ChatUserRole
from ..core.permissions import CommandPermission, has_permission, get_command_permission

async def get_chat_user_role(db: AsyncSession, platform: str, platform_id: str) -> Optional[ChatUserRole]:
    """Get a chat user's role from the database.
    
    Args:
        db: Database session
        platform: The chat platform (discord/slack)
        platform_id: The platform-specific user ID
        
    Returns:
        Optional[ChatUserRole]: The user's role if found, None otherwise
    """
    result = await db.execute(
        select(ChatUser)
        .where(ChatUser.platform == platform)
        .where(ChatUser.platform_id == platform_id)
    )
    user = result.scalar_one_or_none()
    return user.role if user else None

async def check_command_permission(
    db: AsyncSession,
    command_name: str,
    platform: str,
    platform_id: Optional[str],
    override_permission: Optional[CommandPermission] = None
) -> tuple[bool, str]:
    """Check if a user has permission to execute a command.
    
    Args:
        db: Database session
        command_name: The name of the command being executed
        platform: The chat platform (discord/slack)
        platform_id: The platform-specific user ID
        override_permission: Optional override for command permission level
        
    Returns:
        tuple[bool, str]: (has_permission, error_message)
        - has_permission: True if allowed, False if denied
        - error_message: Empty string if allowed, explanation if denied
    """
    try:
        # Get required permission level for command
        required_permission = override_permission if override_permission is not None else get_command_permission(command_name)
        
        # Get user's role
        user_role = None
        if platform_id:
            user_role = await get_chat_user_role(db, platform, platform_id)
        
        # Check permission
        permission_granted = await has_permission(user_role, required_permission)
        
        if permission_granted:
            return True, ""
        
        # Generate helpful error message
        role_name = user_role.value if user_role else "unauthenticated"
        required_role = "admin" if required_permission == CommandPermission.ADMIN else "basic"
        error_msg = f"❌ Permission denied: The {command_name} command requires {required_role} role (your role: {role_name})"
        return False, error_msg
        
    except Exception as e:
        raise
