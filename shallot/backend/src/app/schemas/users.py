from datetime import datetime
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field
from ..models.chat_users import ChatService

class UserType(str, Enum):
    """Enum for user types."""
    WEB = 'web'
    CHAT = 'chat'


class Token(BaseModel):
    """Schema for access tokens."""

    access_token: str
    token_type: str


class UserBase(BaseModel):
    """Base user schema with shared attributes."""

    username: str
    display_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    user_type: UserType = UserType.WEB
    service: Optional[ChatService] = None


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str


class UserUpdate(BaseModel):
    """Schema for updating a user.
    
    All fields are optional to allow partial updates.
    """

    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    user_type: Optional[UserType] = None


class User(UserBase):
    """Schema for user responses."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic model configuration."""

        from_attributes = True
