"""Database integration tests."""
import pytest
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base, engine
from app.models.users import User
from app.models.settings import Settings as SettingsModel
from app.models.chat_users import ChatUser, ChatUserRole, ChatService
from app.schemas.users import UserType


@pytest.mark.asyncio
async def test_db_user_operations(db: AsyncSession):
    """Test database operations with User model."""
    # Create a test user
    test_user = User(
        username="db_test_user",
        hashed_password="hashed_pw_for_test",
        is_active=True,
        is_superuser=False,
        user_type=UserType.WEB
    )
    
    # Add and commit
    db.add(test_user)
    await db.commit()
    await db.refresh(test_user)
    
    # Verify user has ID
    assert test_user.id is not None
    
    # Query the user
    result = await db.execute(
        select(User).where(User.username == "db_test_user")
    )
    user = result.scalar_one_or_none()
    
    # Verify user was stored correctly
    assert user is not None
    assert user.username == "db_test_user"
    assert user.hashed_password == "hashed_pw_for_test"
    assert user.is_active is True
    assert user.is_superuser is False
    assert user.user_type == UserType.WEB
    
    # Update the user
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    
    # Verify update worked
    assert user.is_active is False
    
    # Delete the user
    await db.delete(user)
    await db.commit()
    
    # Verify user was deleted
    result = await db.execute(
        select(User).where(User.username == "db_test_user")
    )
    deleted_check = result.scalar_one_or_none()
    assert deleted_check is None


@pytest.mark.asyncio
async def test_db_settings_operations(db: AsyncSession):
    """Test database operations with Settings model."""
    # Create a test setting
    test_setting = SettingsModel(
        key="TEST_SETTING",
        value="test_value",
        description="Test setting for testing"
    )
    
    # Add and commit
    db.add(test_setting)
    await db.commit()
    await db.refresh(test_setting)
    
    # Query the setting
    result = await db.execute(
        select(SettingsModel).where(SettingsModel.key == "TEST_SETTING")
    )
    setting = result.scalar_one_or_none()
    
    # Verify setting was stored correctly
    assert setting is not None
    assert setting.key == "TEST_SETTING"
    assert setting.value == "test_value"
    
    # Test decryption works
    decrypted_value = setting.value
    assert decrypted_value == "test_value"
    
    # Delete the setting
    await db.delete(setting)
    await db.commit()


@pytest.mark.asyncio
async def test_db_chat_user_operations(db: AsyncSession):
    """Test database operations with ChatUser model."""
    # Create a test chat user
    test_chat_user = ChatUser(
        platform_id="test123",
        username="test_chat_user",
        platform=ChatService.DISCORD,
        role=ChatUserRole.ADMIN,
        display_name="Test Chat User"
    )
    
    # Add and commit
    db.add(test_chat_user)
    await db.commit()
    await db.refresh(test_chat_user)
    
    # Verify chat user has ID
    assert test_chat_user.id is not None
    
    # Query the chat user
    result = await db.execute(
        select(ChatUser).where(
            (ChatUser.platform_id == "test123") & 
            (ChatUser.platform == ChatService.DISCORD)
        )
    )
    chat_user = result.scalar_one_or_none()
    
    # Verify chat user was stored correctly
    assert chat_user is not None
    assert chat_user.platform_id == "test123"
    assert chat_user.username == "test_chat_user"
    assert chat_user.platform == ChatService.DISCORD
    assert chat_user.role == ChatUserRole.ADMIN
    assert chat_user.display_name == "Test Chat User"
    
    # Update the chat user
    chat_user.role = ChatUserRole.USER
    await db.commit()
    await db.refresh(chat_user)
    
    # Verify update worked
    assert chat_user.role == ChatUserRole.USER
    
    # Delete the chat user
    await db.delete(chat_user)
    await db.commit()
    
    # Verify chat user was deleted
    result = await db.execute(
        select(ChatUser).where(
            (ChatUser.platform_id == "test123") & 
            (ChatUser.platform == ChatService.DISCORD)
        )
    )
    deleted_check = result.scalar_one_or_none()
    assert deleted_check is None