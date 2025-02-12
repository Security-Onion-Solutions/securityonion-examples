from typing import Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import get_password_hash, verify_password
from ..models.users import User
from ..schemas.users import UserCreate, UserUpdate, UserType


async def get_user_count(db: AsyncSession) -> int:
    """Get total number of users.

    Args:
        db: Database session

    Returns:
        Number of users in database
    """
    result = await db.execute(select(func.count()).select_from(User))
    return result.scalar_one()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get a user by username.

    Args:
        db: Database session
        username: User's username

    Returns:
        User if found, None otherwise
    """
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get a user by ID.

    Args:
        db: Database session
        user_id: User's ID

    Returns:
        User if found, None otherwise
    """
    return await db.get(User, user_id)


async def authenticate_user(
    db: AsyncSession, username: str, password: str
) -> Optional[User]:
    """Authenticate a user.

    Args:
        db: Database session
        username: User's username
        password: User's password

    Returns:
        User if authentication successful, None otherwise
    """
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    """Create a new user.

    Args:
        db: Database session
        user_in: User creation data

    Returns:
        Created user
    """
    # Ensure web users are always superusers
    is_superuser = True if user_in.user_type == UserType.WEB else user_in.is_superuser
    
    user = User(
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        is_active=user_in.is_active,
        is_superuser=is_superuser,
        user_type=user_in.user_type
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(
    db: AsyncSession, user: User, user_in: UserUpdate
) -> User:
    """Update a user.

    Args:
        db: Database session
        user: Existing user to update
        user_in: Update data

    Returns:
        Updated user
    """
    update_data = user_in.model_dump(exclude_unset=True)
    if update_data.get("password"):
        hashed_password = get_password_hash(update_data["password"])
        del update_data["password"]
        update_data["hashed_password"] = hashed_password

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user
