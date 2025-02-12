import logging
from ...database import AsyncSessionLocal
from ...services.chat_users import get_chat_user_by_platform_id
from ...schemas.commands import AVAILABLE_COMMANDS
from ...models.chat_users import ChatService, ChatUserRole
from ...core.permissions import CommandPermission, get_command_permission
from ...core.decorators import requires_permission

logger = logging.getLogger(__name__)

def get_role_display_name(role: ChatUserRole) -> str:
    """Get a friendly display name for a role."""
    return {
        ChatUserRole.USER: "User",
        ChatUserRole.BASIC: "Basic",
        ChatUserRole.ADMIN: "Admin"
    }.get(role, str(role))

def get_allowed_roles(permission: CommandPermission) -> list[ChatUserRole]:
    """Get list of roles that can execute a command based on permission level."""
    if permission == CommandPermission.PUBLIC:
        return [ChatUserRole.USER, ChatUserRole.BASIC, ChatUserRole.ADMIN]
    elif permission == CommandPermission.BASIC:
        return [ChatUserRole.BASIC, ChatUserRole.ADMIN]
    else:  # ADMIN
        return [ChatUserRole.ADMIN]

async def format_command_help(cmd, user_role: ChatUserRole = None) -> list[str]:
    """Format help text for a command.
    
    Args:
        cmd: Command object
        user_role: User's role if available
        
    Returns:
        List of formatted help text lines
    """
    logger.debug(f"Formatting help for command: {cmd.name}")
    logger.debug(f"User role: {user_role}")
    
    # Get required permission level
    required_permission = get_command_permission(cmd.name)
    logger.debug(f"Required permission: {required_permission}")
    
    # Format role requirements based on permission level
    if required_permission == CommandPermission.PUBLIC:
        role_text = "Available to: Everyone"
        has_access = True
    else:
        # Get allowed roles for this permission level
        allowed_roles = get_allowed_roles(required_permission)
        roles = [get_role_display_name(role) for role in allowed_roles]
        role_text = f"Available to: {', '.join(roles)}"
        has_access = user_role and user_role in allowed_roles
    
    access_indicator = "✅" if has_access else "❌"
    
    return [
        f"\n{access_indicator} !{cmd.name}",
        f"  Description: {cmd.description}",
        f"  {role_text}",
        f"  Example: {cmd.example}"
    ]

@requires_permission()  # Help command permission is already defined in COMMAND_PERMISSIONS
async def process(command: str, user_id: str = None, platform: ChatService = None, username: str = None, channel_id: str = None) -> str:
    """Process the help command."""
    print(f"[DEBUG] Processing help command for platform: {platform}, user_id: {user_id}")
    print(f"[DEBUG] Full command text: '{command}'")
    print(f"[DEBUG] Platform type: {type(platform)}, value: {platform!r}")
    
    try:
        user_role = None
        if user_id is not None and platform is not None:
            print(f"[DEBUG] Looking up user {user_id} for platform {platform}")
            async with AsyncSessionLocal() as db:
                try:
                    user = await get_chat_user_by_platform_id(db, user_id, platform)
                    if user:
                        user_role = user.role
                        print(f"[DEBUG] User found with role: {user_role}")
                    else:
                        print(f"[DEBUG] No user found for {user_id} on {platform}")
                except ValueError as e:
                    print(f"[DEBUG] Invalid platform type: {platform}")
                    print(f"[DEBUG] ValueError details: {str(e)}")
                    return f"Error: Invalid platform type '{platform}'"
                except Exception as e:
                    print(f"[DEBUG] Unexpected error in user lookup: {str(e)}")
                    raise
        
        # Start with header
        help_lines = ["Available commands:"]
        
        if user_role:
            # Show role-specific header
            role_name = get_role_display_name(user_role)
            help_lines.append(f"\nYour role: {role_name}")
            
            # Add all commands with permission indicators
            for cmd in sorted(AVAILABLE_COMMANDS, key=lambda x: x.name):
                help_lines.extend(await format_command_help(cmd, user_role))
        else:
            print("[DEBUG] No user role found, showing public commands only")
            # For unauthenticated users, show commands with PUBLIC permission
            public_commands = []
            for cmd in AVAILABLE_COMMANDS:
                permission = get_command_permission(cmd.name)
                if permission == CommandPermission.PUBLIC:
                    public_commands.append(cmd)
                    
            logger.debug(f"Found {len(public_commands)} public commands")
            if public_commands:
                for cmd in sorted(public_commands, key=lambda x: x.name):
                    logger.debug(f"Adding public command to help: {cmd.name}")
                    help_lines.extend(await format_command_help(cmd, None))
                help_lines.append("\nRegister with !register to access more commands")
            else:
                logger.debug("No public commands found")
                help_lines.append("\nPlease register with !register to access commands")
        
        response = "\n".join(help_lines)
        print(f"[DEBUG] Generated help text ({len(response)} chars)")
        return response
        
    except Exception as e:
        print(f"[DEBUG] Error processing help command: {str(e)}")
        print(f"[DEBUG] Exception type: {type(e)}")
        raise
