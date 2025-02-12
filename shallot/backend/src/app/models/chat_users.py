from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Integer, String, Enum, BigInteger
import enum
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ChatService(str, enum.Enum):
    """Enum for chat service types."""
    DISCORD = 'DISCORD'
    SLACK = 'SLACK'
    MATRIX = 'MATRIX'
    TEAMS = 'TEAMS'


class ChatUserRole(str, enum.Enum):
    """Enum for chat user roles."""
    USER = 'user'    # Default role with minimal access
    BASIC = 'basic'  # Access to basic commands
    ADMIN = 'admin'  # Full access to all commands


class ChatUser(Base):
    """Chat user model.

    Attributes:
        id: Unique identifier
        discord_id: Chat service user's unique ID
        username: Chat username
        service: Chat service (discord/slack)
        role: User's role (public/admin)
        created_at: When user was created
        updated_at: When user was last updated
    """

    __tablename__ = "chat_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    platform_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    username: Mapped[str] = mapped_column(String)
    display_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    platform: Mapped[ChatService] = mapped_column(
        Enum(ChatService), nullable=False
    )
    role: Mapped[ChatUserRole] = mapped_column(
        Enum(ChatUserRole), default=ChatUserRole.USER, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
