from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Integer, String, Enum
import enum
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class UserType(str, enum.Enum):
    """Enum for user types."""
    WEB = 'web'
    CHAT = 'chat'

class User(Base):
    """User model for web admin users.

    Attributes:
        id: Unique identifier
        username: User's username (used for login)
        hashed_password: Bcrypt hashed password
        is_active: Whether user account is active
        is_superuser: Whether user has superuser privileges
        created_at: When user was created
        updated_at: When user was last updated
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    user_type: Mapped[UserType] = mapped_column(
        Enum(UserType), default=UserType.WEB, nullable=False
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
