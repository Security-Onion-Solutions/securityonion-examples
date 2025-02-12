from typing import List, Dict, Sequence, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..database import get_db
from ..schemas.settings import Setting, SettingCreate, SettingUpdate
from ..core.default_settings import DEFAULT_SETTINGS
from .auth import get_current_active_user
from ..services.settings import (
    create_setting,
    get_setting,
    get_settings,
    update_setting,
    delete_setting,
    ensure_required_settings,
)
from ..core.securityonion import client as so_client
from ..core.discord import client as discord_client
from ..core.slack import client as slack_client
from ..core.matrix import client as matrix_client

router = APIRouter(
    tags=["settings"],
)

async def init_default_settings(db: AsyncSession):
    """Initialize default settings."""
    try:
        print("\n=== Starting to initialize default settings ===")
        # First verify database connection
        result = await db.execute(text("SELECT 1"))
        print("Database connection verified")

        # List existing settings
        result = await db.execute(text("SELECT key FROM settings"))
        existing_settings = {row[0] for row in result.fetchall()}
        print(f"Current settings in database: {existing_settings}")

        for setting in DEFAULT_SETTINGS:
            try:
                print(f"\nProcessing setting: {setting.key}")
                
                if setting.key in existing_settings:
                    print(f"Found existing setting: {setting.key}")
                    existing = await get_setting(db, setting.key)
                    if not existing.value:  # If value is empty, update with default
                        print(f"Updating empty setting: {setting.key}")
                        updated = await update_setting(
                            db, 
                            setting.key, 
                            SettingUpdate(value=setting.value, description=setting.description)
                        )
                        print(f"Update successful: {setting.key}")
                else:
                    print(f"Creating new setting: {setting.key}")
                    created = await create_setting(db, setting)
                    print(f"Creation successful: {setting.key}")

                # Verify the setting exists
                saved = await get_setting(db, setting.key)
                if saved:
                    print(f"Verified setting exists: {setting.key}")
                else:
                    print(f"Warning: Failed to verify setting: {setting.key}")
                
            except Exception as e:
                print(f"Error processing setting {setting.key}: {str(e)}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
                raise

        # List final settings
        result = await db.execute(text("SELECT key FROM settings"))
        final_settings = {row[0] for row in result.fetchall()}
        print(f"\nFinal settings in database: {final_settings}")
        print("=== Finished initializing default settings ===\n")
    except Exception as e:
        print(f"Error in init_default_settings: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise

# Add authentication requirement for all endpoints except initialization and basic settings fetch
@router.get("/", response_model=List[Setting])
async def read_settings(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> Sequence[Setting]:
    """Get all settings."""
    return await get_settings(db, skip=skip, limit=limit)


# Add auth requirement for all other endpoints
router.dependencies.append(Depends(get_current_active_user))


@router.get("/authenticated", response_model=List[Setting])
async def read_settings(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> Sequence[Setting]:
    """Get all settings."""
    return await get_settings(db, skip=skip, limit=limit)


@router.get("/{key}", response_model=Setting)
async def read_setting(key: str, db: AsyncSession = Depends(get_db)) -> Setting:
    """Get a setting by key."""
    setting = await get_setting(db, key)
    if not setting:
        raise HTTPException(
            status_code=404, detail=f"Setting with key '{key}' not found"
        )
    return setting


@router.post("/", response_model=Setting)
async def create_setting_endpoint(
    setting: SettingCreate, db: AsyncSession = Depends(get_db)
) -> Setting:
    """Create a new setting."""
    # Check if setting already exists
    existing = await get_setting(db, setting.key)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Setting with key '{setting.key}' already exists",
        )
    return await create_setting(db, setting)


@router.put("/{key}", response_model=Setting)
async def update_setting_endpoint(
    key: str, setting: SettingUpdate, db: AsyncSession = Depends(get_db)
) -> Setting:
    """Update a setting."""
    updated = await update_setting(db, key, setting)
    if not updated:
        raise HTTPException(
            status_code=404, detail=f"Setting with key '{key}' not found"
        )
    
    # Reinitialize clients if their settings were updated
    if key == "securityOnion":
        print("Security Onion settings updated, reinitializing client...")
        await so_client.initialize()
        # Test connection after initialization
        await so_client.test_connection()
    elif key == "DISCORD":
        print("Discord settings updated, reinitializing client...")
        await discord_client.initialize()
    elif key == "SLACK":
        print("Slack settings updated, reinitializing client...")
        await slack_client.initialize()
    elif key == "MATRIX":
        print("Matrix settings updated, reinitializing client...")
        await matrix_client.initialize()
    
    return updated


@router.delete("/{key}")
async def delete_setting_endpoint(
    key: str, db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Delete a setting."""
    success = await delete_setting(db, key)
    if not success:
        raise HTTPException(
            status_code=404, detail=f"Setting with key '{key}' not found"
        )
    return {"message": f"Setting '{key}' deleted"}


@router.get("/security-onion/status", response_model=Dict[str, Any])
async def get_so_status() -> Dict[str, Any]:
    """Get Security Onion connection status."""
    try:
        return so_client.get_status()
    except Exception as e:
        print(f"Error getting SO status: {str(e)}")
        return {
            "connected": False,
            "error": f"Failed to get status: {str(e)}"
        }


@router.post("/security-onion/test-connection", response_model=Dict[str, Any])
async def test_so_connection() -> Dict[str, Any]:
    """Test Security Onion connection."""
    try:
        # Re-initialize with current settings
        await so_client.initialize()
        success = await so_client.test_connection()
        status = so_client.get_status()
        print(f"Test connection result - success: {success}, status: {status}")
        return {
            "success": success,
            "status": status
        }
    except Exception as e:
        print(f"Test connection error: {str(e)}")
        return {
            "success": False,
            "status": {
                "connected": False,
                "error": str(e)
            }
        }
