from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import (
    create_access_token,
    verify_password,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from ..database import get_db
from ..models.users import User
from ..schemas.users import Token, UserCreate
from ..services.users import create_user, get_user_by_username

router = APIRouter(tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get current user from token.

    Args:
        token: JWT token
        db: Database session

    Returns:
        Current user

    Raises:
        HTTPException: If credentials invalid
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Verify and decode JWT token
        from jose import jwt
        from ..core.security import ALGORITHM
        from ..config import settings

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    user = await get_user_by_username(db, username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get current active user.

    Args:
        current_user: Current authenticated user

    Returns:
        Current active user

    Raises:
        HTTPException: If user inactive
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_active_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """Get current active superuser.

    Args:
        current_user: Current active user

    Returns:
        Current active superuser

    Raises:
        HTTPException: If user not superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges",
        )
    return current_user


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Login to get access token.

    Args:
        form_data: Login form data
        db: Database session

    Returns:
        Access token

    Raises:
        HTTPException: If credentials invalid
    """
    user = await get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.username,
        expires_delta=access_token_expires,
        is_superuser=user.is_superuser
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/setup-required")
async def check_setup_required(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    """Check if initial setup is required.

    Args:
        db: Database session

    Returns:
        Dict indicating if setup is required
    """
    result = await db.execute(select(User))
    first_user = result.scalar_one_or_none()
    return {"setup_required": first_user is None}


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Refresh access token.

    Args:
        current_user: Current authenticated user

    Returns:
        New access token
    """
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=current_user.username,
        expires_delta=access_token_expires,
        is_superuser=current_user.is_superuser
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/first-user", response_model=Token)
async def initial_setup(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Create first admin user and return access token.

    Args:
        user_in: User creation data
        db: Database session

    Returns:
        Access token for created admin

    Raises:
        HTTPException: If users already exist
    """
    # Check if any users exist
    result = await db.execute(select(User))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setup already completed",
        )

    # Create first admin user
    user_in.is_superuser = True
    user = await create_user(db, user_in)

    # Generate access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.username,
        expires_delta=access_token_expires,
        is_superuser=user.is_superuser
    )
    return {"access_token": access_token, "token_type": "bearer"}
