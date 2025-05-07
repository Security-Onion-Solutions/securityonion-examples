from typing import Optional, List
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.chat_users import ChatUser, ChatUserRole, ChatService

logger = logging.getLogger(__name__)


async def get_chat_user_by_platform_id(
    db: AsyncSession, platform_id: str, platform: str
) -> Optional[ChatUser]:
    """Get a chat user by their platform-specific ID."""
    logger.info(f"Looking up chat user with platform_id: {platform_id}, platform: {platform}")
    
    # Handle both string and enum values for platform
    platform_value = platform
    if hasattr(platform, 'value'):
        platform_value = platform.value
    
    query = select(ChatUser).where(
        ChatUser.platform_id == str(platform_id),  # Ensure platform_id is a string
        ChatUser.platform == platform_value  # Use enum value or string for platform
    )
    logger.debug(f"Executing query: {query}")
    
    result = await db.execute(query)
    # In Python 3.13, result might be a coroutine
    if hasattr(result, "__await__"):
        result = await result
        
    user = result.scalar_one_or_none()

        
    # In Python 3.13, scalar_one might return a coroutine

        
    if hasattr(user, "__await__"):

        
        user = await user
    # In Python 3.13, scalar_one_or_none might return a coroutine
    if hasattr(user, "__await__"):
        user = await user
    
    if user:
        logger.info(f"Found user: {user.username} with role: {user.role}")
    else:
        logger.warning(f"No user found for platform_id: {platform_id}, platform: {platform}")
    
    return user


async def create_chat_user(
    db: AsyncSession,
    platform_id: str,
    username: str,
    platform: ChatService,
    role: ChatUserRole = ChatUserRole.USER,
    display_name: Optional[str] = None,
) -> ChatUser:
    """Create a new chat user."""
    chat_user = ChatUser(
        platform_id=platform_id,
        username=username,
        platform=platform,
        role=role,
        display_name=display_name
    )
    db.add(chat_user)
    await db.commit()
    await db.refresh(chat_user)
    return chat_user


async def is_command_allowed(
    db: AsyncSession, platform_id: str, platform: str, command: str
) -> bool:
    """Check if a user is allowed to use a command."""
    # Get the user
    user = await get_chat_user_by_platform_id(db, platform_id, platform)
    
    # If user doesn't exist, only allow !help and !register
    if not user:
        return command in ["!help", "!register"]
        
    # User role can only use help and status
    if user.role == ChatUserRole.USER:
        return command in ["!help", "!status"]
        
    # Basic role can use basic commands
    if user.role == ChatUserRole.BASIC:
        return command in ["!help", "!status", "!alerts"]
        
    # Admin role can use all commands
    if user.role == ChatUserRole.ADMIN:
        return True
        
    return False


async def get_chat_user_by_id(db: AsyncSession, user_id: int) -> Optional[ChatUser]:
    """Get a chat user by their ID."""
    result = await db.execute(
        select(ChatUser).where(ChatUser.id == user_id)
    )
    # In Python 3.13, result might be a coroutine
    if hasattr(result, "__await__"):
        result = await result
        
    user = result.scalar_one_or_none()
    # In Python 3.13, scalar_one_or_none might return a coroutine
    if hasattr(user, "__await__"):
        user = await user
        
    return user


async def get_all_chat_users(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> List[ChatUser]:
    """Get all chat users with pagination."""
    result = await db.execute(
        select(ChatUser)
        .offset(skip)
        .limit(limit)
    )
    # In Python 3.13, result might be a coroutine
    if hasattr(result, "__await__"):
        result = await result
        
    scalars_result = result.scalars()
    # In Python 3.13, scalars() might return a coroutine
    if hasattr(scalars_result, "__await__"):
        scalars_result = await scalars_result
        
    return scalars_result.all()


async def update_chat_user_role(
    db: AsyncSession, user_id: int, role: ChatUserRole
) -> Optional[ChatUser]:
    """Update a chat user's role."""
    user = await get_chat_user_by_id(db, user_id)
    if user:
        user.role = role
        await db.commit()
        await db.refresh(user)
    return user


async def delete_chat_user(
    db: AsyncSession, user_id: int
) -> bool:
    """Delete a chat user."""
    user = await get_chat_user_by_id(db, user_id)
    if user:
        await db.delete(user)
        await db.commit()
        return True
    return False