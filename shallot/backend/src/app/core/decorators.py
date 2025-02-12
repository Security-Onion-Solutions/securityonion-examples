from functools import wraps
import logging
from typing import Callable, Optional
from ..core.permissions import CommandPermission, get_command_permission, has_permission
from ..services.chat_users import get_chat_user_by_platform_id
from ..database import AsyncSessionLocal
from ..models.chat_users import ChatService

logger = logging.getLogger(__name__)

def requires_permission(permission: Optional[CommandPermission] = None):
    """Decorator to check command permissions before execution.
    
    Args:
        permission: Optional explicit permission level for the command.
                  If not provided, will be looked up from COMMAND_PERMISSIONS.
    
    Usage:
        @requires_permission()  # Uses permission from COMMAND_PERMISSIONS
        async def process(command: str, user_id: str = None, platform: ChatService = None, username: str = None) -> str:
            # Command implementation
        
        @requires_permission(permission=CommandPermission.PUBLIC)  # Explicit permission
        async def process(command: str, user_id: str = None, platform: ChatService = None, username: str = None) -> str:
            # Command implementation
    
    The decorator will:
    1. Extract the command name from the module path
    2. Check if the user has permission to execute the command
    3. Only execute the command if permission is granted
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(command: str, user_id: Optional[str] = None, platform: Optional[ChatService] = None, username: Optional[str] = None, user_type: Optional[str] = None, *args, **kwargs) -> str:
            try:
                # Get command name from the command text
                command_parts = command.strip().split()
                if len(command_parts) > 0:
                    # Remove the command prefix (!) if present
                    command_name = command_parts[0].lstrip('!')
                else:
                    command_name = "help"  # Default to help if no command provided
                
                logger.info(f"Processing command: {command_name} from platform: {platform} user_id: {user_id}")
                
                # Get required permission level
                required_permission = permission if permission else get_command_permission(command_name)
                logger.info(f"Required permission level: {required_permission}")
                
                # Web users bypass permission checks
                logger.info(f"Checking user type: {user_type}")
                if user_type == "web":  # UserType.WEB.value is lowercase
                    logger.info("Web user detected - bypassing permission checks")
                    return await func(command=command, user_id=user_id, platform=platform, username=username, **kwargs)

                # Get user's role if they have one
                user_role = None
                if user_id and platform:
                    async with AsyncSessionLocal() as db:
                        chat_user = await get_chat_user_by_platform_id(db, user_id, platform)
                        if chat_user:
                            user_role = chat_user.role
                            logger.info(f"Found user with role: {user_role}")
                        else:
                            logger.warning(f"No chat user found for platform: {platform} user_id: {user_id}")
                else:
                    logger.warning("No user_id provided")
                
                # Check if user has permission
                has_perm = await has_permission(user_role, required_permission)
                logger.info(f"Permission check result: {has_perm} (user_role: {user_role}, required: {required_permission})")
                
                if not has_perm:
                    return f"Permission denied. This command requires {required_permission.value} access. Your role: {user_role.value if user_role else 'none'}"
                
                # Execute command if permitted
                return await func(command=command, user_id=user_id, platform=platform, username=username, **kwargs)
            except Exception as e:
                raise
        return wrapper
    return decorator
