# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.users import User
from ..schemas.users import User as UserSchema
from ..schemas.chat_users import ChatUserUpdate
from ..services.chat_users import (
    get_all_chat_users,
    get_chat_user_by_id,
    update_chat_user_role,
    delete_chat_user,
)
from .auth import get_current_active_superuser

router = APIRouter()

@router.get("/", response_model=List[UserSchema])
async def read_chat_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
    skip: int = 0,
    limit: int = 100,
) -> List[UserSchema]:
    """Get list of chat users.

    Args:
        db: Database session
        current_user: Current superuser (for authorization)
        skip: Number of users to skip
        limit: Maximum number of users to return

    Returns:
        List of chat users converted to User schema
    """
    chat_users = await get_all_chat_users(db, skip=skip, limit=limit)
    
    # Convert ChatUser models to User schema format
    return [
        UserSchema(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            is_active=True,  # Chat users are always active
            is_superuser=user.role == "admin",
            created_at=user.created_at,
            updated_at=user.updated_at,
            user_type="chat",
            service=user.platform.upper()  # Convert platform to uppercase for frontend
        ) for user in chat_users
    ]

@router.get("/{user_id}", response_model=UserSchema)
async def read_chat_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
) -> UserSchema:
    """Get chat user by ID.

    Args:
        user_id: User ID
        db: Database session
        current_user: Current superuser (for authorization)

    Returns:
        Chat user information converted to User schema

    Raises:
        HTTPException: If user not found
    """
    chat_user = await get_chat_user_by_id(db, user_id)
    if chat_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat user not found",
        )
    
    return UserSchema(
        id=chat_user.id,
        username=chat_user.username,
        display_name=chat_user.display_name,
        is_active=True,  # Chat users are always active
        is_superuser=chat_user.role == "admin",
        created_at=chat_user.created_at,
        updated_at=chat_user.updated_at,
        user_type="chat",
        service=chat_user.platform.upper()  # Convert platform to uppercase for frontend
    )


@router.put("/{user_id}/role", response_model=UserSchema)
async def update_chat_user_role_endpoint(
    user_id: int,
    user_update: ChatUserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
) -> UserSchema:
    """Update a chat user's role.

    Args:
        user_id: User ID
        user_update: Role update data
        db: Database session
        current_user: Current superuser (for authorization)

    Returns:
        Updated chat user information

    Raises:
        HTTPException: If user not found
    """
    chat_user = await update_chat_user_role(db, user_id, user_update.role)
    if chat_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat user not found",
        )
    
    return UserSchema(
        id=chat_user.id,
        username=chat_user.username,
        display_name=chat_user.display_name,
        is_active=True,
        is_superuser=chat_user.role == "admin",
        created_at=chat_user.created_at,
        updated_at=chat_user.updated_at,
        user_type="chat",
        service=chat_user.platform.upper()  # Convert platform to uppercase for frontend
    )


@router.delete("/{user_id}")
async def delete_chat_user_endpoint(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
) -> dict:
    """Delete a chat user.

    Args:
        user_id: User ID to delete
        db: Database session
        current_user: Current superuser (for authorization)

    Returns:
        Success message

    Raises:
        HTTPException: If user not found
    """
    success = await delete_chat_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat user not found",
        )
    
    return {"message": "Chat user deleted successfully"}
