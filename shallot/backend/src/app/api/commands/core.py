import logging
from ...models.chat_users import ChatService
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

logger = logging.getLogger(__name__)
from ...schemas.commands import (
    CommandTestRequest, 
    CommandTestResponse, 
    CommandListResponse,
    AVAILABLE_COMMANDS,
    Command,
    PlatformType
)
from ..auth import get_current_user
from ...models.users import User, UserType
from ...database import AsyncSessionLocal
from ...services.chat_users import get_chat_user_by_platform_id, create_chat_user
from ...models.chat_users import ChatUserRole, ChatService
from ...core.permissions import CommandPermission, get_command_permission, has_permission

router = APIRouter(prefix="/commands", tags=["commands"])

# Add auth requirement for all endpoints
router.dependencies.append(Depends(get_current_user))

async def validate_command_access(command_def: Command, platform: PlatformType, user_id: str = None) -> bool:
    """
    Validate if a user has access to execute a command.
    
    Args:
        command_def: The command definition to check
        platform: The platform the user is on
        user_id: The platform-specific user ID
        
    Returns:
        bool: True if user has access, False otherwise
    """
    # Get required permission level
    required_permission = get_command_permission(command_def.name)
    
    # If no user_id provided, only allow public commands
    if user_id is None:
        return required_permission == CommandPermission.PUBLIC
        
    # Check user's role
    async with AsyncSessionLocal() as db:
        chat_user = await get_chat_user_by_platform_id(db, user_id, ChatService(platform))
        if not chat_user:
            return False
            
        return await has_permission(chat_user.role, required_permission)

@router.get("/", response_model=CommandListResponse)
async def list_commands(
    current_user: User = Depends(get_current_user),
    platform: Optional[PlatformType] = None
) -> CommandListResponse:
    """
    List all available commands. The response will be filtered based on the user's role and platform.
    This endpoint requires authentication.
    
    Args:
        current_user: The authenticated user
        platform: Optional platform to filter commands for
    """
    # Web users have access to all commands
    if current_user.user_type == UserType.WEB:
        available_commands = AVAILABLE_COMMANDS
    else:
        # For chat users, check their role
        async with AsyncSessionLocal() as db:
            chat_user = await get_chat_user_by_platform_id(db, str(current_user.id), ChatService(platform or "DISCORD"))
            user_role = chat_user.role if chat_user else None
            
            # Filter commands based on user's role
            available_commands = [
                cmd for cmd in AVAILABLE_COMMANDS
                if ((user_role and await has_permission(user_role, get_command_permission(cmd.name))) or  # Commands the user has access to
                    get_command_permission(cmd.name) == CommandPermission.PUBLIC) and  # Public commands
                   (not platform or not cmd.platforms or platform in cmd.platforms)  # Commands available on the platform
            ]
        
    return CommandListResponse(commands=available_commands)

@router.post("/test-command", response_model=CommandTestResponse)
async def test_command(
    request: CommandTestRequest,
    current_user: User = Depends(get_current_user)
) -> CommandTestResponse:
    """
    Test a chat bot command and return the response.
    This endpoint requires authentication and proper role access.
    """
    if not request.command:
        raise HTTPException(status_code=400, detail="Command cannot be empty")
    
    # Extract command name without the ! prefix
    command_name = request.command.lstrip('!').split()[0].lower()
    
    # Find the command definition
    command_def = next(
        (cmd for cmd in AVAILABLE_COMMANDS if cmd.name == command_name),
        None
    )
    
    if not command_def:
        return CommandTestResponse(
            command=request.command,
            response=f"Unknown command: {command_name}",
            success=False
        )
        
    # Check if command is available on the requested platform
    if command_def.platforms and request.platform not in command_def.platforms:
        return CommandTestResponse(
            command=request.command,
            response=f"Command {command_name} is not available on {request.platform}",
            success=False
        )
    
    # For chat users, check their role
    if current_user.user_type != UserType.WEB:
        async with AsyncSessionLocal() as db:
            chat_user = await get_chat_user_by_platform_id(db, str(current_user.id), ChatService(request.platform))
            user_role = chat_user.role if chat_user else None
            
            if not user_role or not await has_permission(user_role, get_command_permission(command_def.name)):
                return CommandTestResponse(
                    command=request.command,
                    response="You don't have permission to use this command",
                    success=False
                )
    
    try:
        # Use the centralized process_command function
        from . import process_command
        logger.debug(f"User type before process_command: {current_user.user_type.value}")
        response = await process_command(
            command=request.command,
            platform=request.platform,  # Use platform from request
            user_id=current_user.id if current_user.user_type == UserType.CHAT else None,
            username=current_user.username,
            user_type=current_user.user_type.value  # Pass user type to decorator
        )
        return CommandTestResponse(
            command=request.command,
            response=response,
            success=True
        )
    except Exception as e:
        return CommandTestResponse(
            command=request.command,
            response=str(e),
            success=False
        )
