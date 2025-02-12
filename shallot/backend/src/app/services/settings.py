import json
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound

from ..models.settings import Settings as SettingsModel
from ..schemas.settings import SettingCreate, SettingUpdate

# List of chat service settings keys (must match ChatService enum values)
CHAT_SERVICES = ['SLACK', 'TEAMS', 'MATRIX', 'DISCORD']


async def create_setting(db: AsyncSession, setting: SettingCreate) -> SettingsModel:
    """Create a new setting.

    Args:
        db: Database session
        setting: Setting data

    Returns:
        Created setting
    """
    try:
        db_setting = SettingsModel(key=setting.key, description=setting.description)
        db_setting.value = setting.value  # Uses property setter for encryption
        print(f"Creating setting {setting.key} with value {setting.value}")

        db.add(db_setting)
        await db.commit()
        await db.refresh(db_setting)

        # Verify encryption worked
        decrypted = db_setting.value
        print(f"Successfully created and verified setting {setting.key}")
        return db_setting
    except Exception as e:
        print(f"Error creating setting {setting.key}: {str(e)}")
        await db.rollback()
        raise


async def get_setting(db: AsyncSession, key: str) -> Optional[SettingsModel]:
    """Get a setting by key.

    Args:
        db: Database session
        key: Setting key

    Returns:
        Setting if found, None otherwise
    """
    try:
        result = await db.execute(
            select(SettingsModel).where(SettingsModel.key == key)
        )
        return result.scalar_one_or_none()
    except NoResultFound:
        return None


async def get_settings(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> List[SettingsModel]:
    """Get multiple settings.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of settings
    """
    result = await db.execute(select(SettingsModel).offset(skip).limit(limit))
    return list(result.scalars().all())


async def is_chat_service_enabled(setting_key: str, setting_value: str) -> bool:
    """Check if a chat service setting is being enabled.

    Args:
        setting_key: The setting key
        setting_value: The setting value as a JSON string

    Returns:
        bool: True if the setting is a chat service being enabled
    """
    if setting_key not in CHAT_SERVICES:
        return False
    
    try:
        settings_dict = json.loads(setting_value)
        return settings_dict.get('enabled', False)
    except json.JSONDecodeError:
        return False

async def disable_other_chat_services(db: AsyncSession, current_service: str) -> None:
    """Disable all chat services except the specified one.

    Args:
        db: Database session
        current_service: The chat service to keep enabled
    """
    for service in CHAT_SERVICES:
        if service == current_service:
            continue
            
        service_setting = await get_setting(db, service)
        if service_setting:
            try:
                current_value = json.loads(service_setting.value)
                if current_value.get('enabled'):
                    current_value['enabled'] = False
                    service_setting.value = json.dumps(current_value)
            except json.JSONDecodeError:
                continue

async def update_setting(
    db: AsyncSession, key: str, setting: SettingUpdate
) -> Optional[SettingsModel]:
    """Update a setting.

    Args:
        db: Database session
        key: Setting key
        setting: New setting data

    Returns:
        Updated setting if found, None otherwise
    """
    try:
        db_setting = await get_setting(db, key)
        if not db_setting:
            return None

        print(f"Updating setting {key} with value {setting.value}")
        
        # Check if this is a chat service being enabled
        if await is_chat_service_enabled(key, setting.value):
            print(f"Chat service {key} is being enabled, disabling others")
            await disable_other_chat_services(db, key)
        
        if setting.value is not None:
            db_setting.value = setting.value  # Uses property setter for encryption
        if setting.description is not None:
            setattr(db_setting, "description", setting.description)

        await db.commit()
        await db.refresh(db_setting)

        # Verify encryption worked
        decrypted = db_setting.value
        print(f"Successfully updated and verified setting {key}")
        return db_setting
    except Exception as e:
        print(f"Error updating setting {key}: {str(e)}")
        await db.rollback()
        raise


async def delete_setting(db: AsyncSession, key: str) -> bool:
    """Delete a setting.

    Args:
        db: Database session
        key: Setting key

    Returns:
        True if setting was deleted, False if not found
    """
    db_setting = await get_setting(db, key)
    if not db_setting:
        return False

    await db.delete(db_setting)
    await db.commit()
    return True


async def ensure_required_settings(
    db: AsyncSession, required_settings: List[SettingCreate]
) -> None:
    """Ensure required settings exist.

    Creates settings if they don't exist, doesn't modify existing ones.

    Args:
        db: Database session
        required_settings: List of required settings
    """
    try:
        print("Starting to ensure required settings...")
        for setting in required_settings:
            try:
                print(f"Checking setting: {setting.key}")
                existing = await get_setting(db, setting.key)
                if not existing:
                    print(f"Creating missing setting: {setting.key}")
                    await create_setting(db, setting)
                else:
                    print(f"Setting already exists: {setting.key}")
            except Exception as e:
                print(f"Error processing setting {setting.key}: {str(e)}")
                raise
        print("Finished ensuring required settings")
    except Exception as e:
        print(f"Error in ensure_required_settings: {str(e)}")
        raise
