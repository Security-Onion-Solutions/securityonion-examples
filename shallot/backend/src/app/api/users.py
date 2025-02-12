from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.users import User, UserType
from ..schemas.users import User as UserSchema
from ..schemas.users import UserCreate, UserUpdate, UserType as SchemaUserType
from ..services.users import (
    create_user,
    get_user_by_username,
    get_user_by_id,
    update_user,
)
from .auth import get_current_active_superuser, get_current_user

router = APIRouter()


@router.post("/", response_model=UserSchema)
async def create_new_user(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
) -> User:
    """Create new user.

    Args:
        user_in: User creation data
        db: Database session
        current_user: Current superuser (for authorization)

    Returns:
        Created user

    Raises:
        HTTPException: If username already exists
    """
    user = await get_user_by_username(db, user_in.username)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )
    return await create_user(db, user_in)


@router.get("/", response_model=List[UserSchema])
async def read_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_superuser)],
    skip: int = 0,
    limit: int = 100,
    user_type: Optional[SchemaUserType] = Query(None, description="Filter users by type"),
) -> List[User]:
    """Get list of users.

    Args:
        db: Database session
        current_user: Current superuser (for authorization)
        skip: Number of users to skip
        limit: Maximum number of users to return
        user_type: Optional filter by user type

    Returns:
        List of users
    """
    query = select(User)
    
    if user_type:
        query = query.where(User.user_type == user_type)
    
    result = await db.execute(
        query.offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserSchema)
async def read_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get user by ID.

    Args:
        user_id: User ID
        db: Database session
        current_user: Current user (for authorization)

    Returns:
        User information

    Raises:
        HTTPException: If user not found or unauthorized
    """
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges",
        )
    return user


@router.put("/{user_id}", response_model=UserSchema)
async def update_user_endpoint(
    user_id: int,
    user_in: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Update user.

    Args:
        user_id: User ID to update
        user_in: Update data
        db: Database session
        current_user: Current user (for authorization)

    Returns:
        Updated user

    Raises:
        HTTPException: If user not found or unauthorized
    """
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges",
        )
    
    # Only superusers can change superuser status or user type
    if not current_user.is_superuser and (
        (user_in.is_superuser is not None and user_in.is_superuser != user.is_superuser) or
        (user_in.user_type is not None and user_in.user_type != user.user_type)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges to modify superuser status or user type",
        )

    return await update_user(db, user, user_in)
