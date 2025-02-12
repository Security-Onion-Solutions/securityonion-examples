from enum import Enum
from typing import Dict, Optional
from ..models.chat_users import ChatUserRole

class CommandPermission(str, Enum):
    """Permission levels for commands."""
    PUBLIC = 'public'     # Anyone can use
    BASIC = 'basic'      # Basic users and above
    ADMIN = 'admin'      # Admin only

# Map commands to their required permission levels
COMMAND_PERMISSIONS: Dict[str, CommandPermission] = {
    "help": CommandPermission.PUBLIC,  # Help command should always be public
    "register": CommandPermission.PUBLIC,
    "status": CommandPermission.ADMIN,
    "alerts": CommandPermission.ADMIN,
    "ack": CommandPermission.ADMIN,
    "detections": CommandPermission.ADMIN,
    "hunt": CommandPermission.ADMIN,
    "escalate": CommandPermission.ADMIN,
    "whois": CommandPermission.ADMIN,
    "dig": CommandPermission.ADMIN
}

async def has_permission(user_role: Optional[ChatUserRole], required_permission: CommandPermission) -> bool:
    """Check if a user role has the required permission level.
    
    Args:
        user_role: The user's role (can be None for unauthenticated users)
        required_permission: The required permission level
        
    Returns:
        bool: True if the user has sufficient permissions, False otherwise
    """
    if user_role is None:
        return required_permission == CommandPermission.PUBLIC
        
    # Define permission hierarchy
    role_levels = {
        ChatUserRole.USER: 0,
        ChatUserRole.BASIC: 1,
        ChatUserRole.ADMIN: 2
    }
    
    permission_levels = {
        CommandPermission.PUBLIC: 0,
        CommandPermission.BASIC: 1,
        CommandPermission.ADMIN: 2
    }
    
    user_level = role_levels[user_role]
    required_level = permission_levels[required_permission]
    
    return user_level >= required_level

def get_command_permission(command: str) -> CommandPermission:
    """Get the required permission level for a command.
    
    Args:
        command: The command name
        
    Returns:
        CommandPermission: The required permission level, defaults to ADMIN if unknown
    """
    return COMMAND_PERMISSIONS.get(command, CommandPermission.ADMIN)
