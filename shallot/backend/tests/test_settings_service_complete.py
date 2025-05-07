"""Comprehensive tests for settings service."""
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound
from sqlalchemy import select

from app.models.settings import Settings as SettingsModel
from app.schemas.settings import SettingCreate, SettingUpdate
from app.services.settings import (
    create_setting,
    get_setting,
    get_settings,
    is_chat_service_enabled,
    disable_other_chat_services,
    update_setting,
    delete_setting,
    ensure_required_settings,
    CHAT_SERVICES
)
from tests.utils import await_mock


@pytest.mark.asyncio
async def test_create_setting(db: AsyncSession):
    """Test creating a setting."""
    # Create test setting
    setting_data = SettingCreate(key="TEST_KEY", value="test_value", description="Test setting")
    created_setting = await create_setting(db, setting_data)
    
    # Verify setting was created
    assert created_setting.key == "TEST_KEY"
    assert created_setting.value == "test_value"  # Should be decrypted
    assert created_setting.description == "Test setting"
    
    # Verify setting exists in the database
    db_setting = await get_setting(db, "TEST_KEY")
    assert db_setting is not None
    assert db_setting.key == "TEST_KEY"


@pytest.mark.asyncio
async def test_create_setting_error_handling(db: AsyncSession):
    """Test error handling in create_setting."""
    # Create a setting that will trigger an error
    setting_data = SettingCreate(key="ERROR_KEY", value="test_value", description="Error test")
    
    # Mock a database error
    with patch.object(db, 'commit', side_effect=Exception("Test error")), \
         patch.object(db, 'rollback') as mock_rollback, \
         pytest.raises(Exception):
        await create_setting(db, setting_data)
        mock_rollback.assert_called_once()


@pytest.mark.asyncio
async def test_get_setting(db: AsyncSession):
    """Test getting a setting by key."""
    # Create a test setting
    setting_data = SettingCreate(key="GET_KEY", value="get_value", description="Get test")
    await create_setting(db, setting_data)
    
    # Test retrieving the setting
    setting = await get_setting(db, "GET_KEY")
    assert setting is not None
    assert setting.key == "GET_KEY"
    assert setting.value == "get_value"
    
    # Test retrieving non-existent setting
    non_existent = await get_setting(db, "NONEXISTENT_KEY")
    assert non_existent is None
    
    # Test with coroutine awaits in Python 3.13
    mock_result = MagicMock()
    mock_scalar = MagicMock()
    mock_result.scalar_one_or_none.return_value = await_mock(mock_scalar)
    
    with patch.object(db, 'execute', return_value=await_mock(mock_result)):
        setting = await get_setting(db, "COROUTINE_KEY")
        assert setting == mock_scalar


@pytest.mark.asyncio
async def test_get_setting_no_result_found(db: AsyncSession):
    """Test get_setting behavior with NoResultFound exception."""
    # Mock execute to raise NoResultFound
    with patch.object(db, 'execute', side_effect=NoResultFound("Test error")):
        result = await get_setting(db, "NONEXISTENT_KEY")
        assert result is None


@pytest.mark.asyncio
async def test_get_settings(db: AsyncSession):
    """Test getting multiple settings with pagination."""
    # Create multiple test settings
    for i in range(5):
        setting_data = SettingCreate(
            key=f"MULTI_KEY_{i}", 
            value=f"multi_value_{i}", 
            description=f"Multi test {i}"
        )
        await create_setting(db, setting_data)
    
    # Get all settings
    all_settings = await get_settings(db)
    assert len(all_settings) >= 5  # Could be more from other tests
    
    # Test pagination
    first_page = await get_settings(db, skip=0, limit=2)
    assert len(first_page) == 2
    
    second_page = await get_settings(db, skip=2, limit=2)
    assert len(second_page) == 2
    
    # Ensure different pages have different settings
    assert first_page[0].id != second_page[0].id
    
    # Test with coroutine awaits in Python 3.13
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_all = [MagicMock(), MagicMock()]
    mock_result.scalars.return_value = await_mock(mock_scalars)
    mock_scalars.all.return_value = mock_all
    
    with patch.object(db, 'execute', return_value=await_mock(mock_result)):
        settings = await get_settings(db)
        assert isinstance(settings, list)
        assert settings == mock_all


@pytest.mark.asyncio
async def test_is_chat_service_enabled():
    """Test is_chat_service_enabled function with all branches."""
    # Test with enabled chat service
    enabled = await is_chat_service_enabled("SLACK", json.dumps({"enabled": True, "token": "test"}))
    assert enabled is True
    
    # Test with disabled chat service
    disabled = await is_chat_service_enabled("SLACK", json.dumps({"enabled": False, "token": "test"}))
    assert disabled is False
    
    # Test when enabled field is missing (defaults to False)
    missing = await is_chat_service_enabled("SLACK", json.dumps({"token": "test"}))
    assert missing is False
    
    # Test with non-chat service
    not_chat = await is_chat_service_enabled("OTHER_KEY", json.dumps({"enabled": True}))
    assert not_chat is False
    
    # Test with invalid JSON
    invalid_json = await is_chat_service_enabled("SLACK", "not json")
    assert invalid_json is False


@pytest.mark.asyncio
async def test_disable_other_chat_services(db: AsyncSession):
    """Test disabling other chat services with all branches."""
    # Create mock settings for chat services
    for service in CHAT_SERVICES:
        setting_data = SettingCreate(
            key=service,
            value=json.dumps({"enabled": True, "token": f"{service}_token"}),
            description=f"{service} configuration"
        )
        await create_setting(db, setting_data)
    
    # Disable all except DISCORD
    await disable_other_chat_services(db, "DISCORD")
    
    # Verify DISCORD is still enabled
    discord_setting = await get_setting(db, "DISCORD")
    discord_config = json.loads(discord_setting.value)
    assert discord_config["enabled"] is True
    
    # Verify others are disabled
    for service in [s for s in CHAT_SERVICES if s != "DISCORD"]:
        service_setting = await get_setting(db, service)
        service_config = json.loads(service_setting.value)
        assert service_config["enabled"] is False
    
    # Test with invalid JSON in a setting
    slack_setting = await get_setting(db, "SLACK")
    slack_setting.encrypted_value = "not json"  # Directly modify DB column to bypass encryption
    await db.commit()
    
    # This should not raise an exception even with invalid JSON
    await disable_other_chat_services(db, "MATRIX")
    
    # Test when a service doesn't exist in the database
    await disable_other_chat_services(db, "NONEXISTENT")  # Should not raise exceptions
    
    # Test when a setting doesn't have 'enabled' flag
    matrix_setting = await get_setting(db, "MATRIX")
    matrix_setting.value = json.dumps({"token": "matrix_token"})  # No enabled flag
    await db.commit()
    
    await disable_other_chat_services(db, "DISCORD")  # Should work without errors


@pytest.mark.asyncio
async def test_update_setting(db: AsyncSession):
    """Test updating a setting."""
    # Create a test setting
    setting_data = SettingCreate(key="UPDATE_KEY", value="original", description="Update test")
    await create_setting(db, setting_data)
    
    # Update the setting
    update_data = SettingUpdate(value="updated", description="Updated description")
    updated_setting = await update_setting(db, "UPDATE_KEY", update_data)
    
    # Verify update
    assert updated_setting is not None
    assert updated_setting.key == "UPDATE_KEY"
    assert updated_setting.value == "updated"
    assert updated_setting.description == "Updated description"
    
    # Test updating non-existent setting
    nonexistent_update = await update_setting(db, "NONEXISTENT_KEY", update_data)
    assert nonexistent_update is None


@pytest.mark.asyncio
async def test_update_setting_chat_service(db: AsyncSession):
    """Test updating a chat service setting."""
    # Create chat service settings
    for service in CHAT_SERVICES:
        setting_data = SettingCreate(
            key=service,
            value=json.dumps({"enabled": False, "token": f"{service}_token"}),
            description=f"{service} configuration"
        )
        await create_setting(db, setting_data)
    
    # Mock disable_other_chat_services to verify it's called
    with patch('app.services.settings.disable_other_chat_services') as mock_disable:
        # Enable SLACK
        update_data = SettingUpdate(value=json.dumps({"enabled": True, "token": "new_slack_token"}))
        updated_setting = await update_setting(db, "SLACK", update_data)
        
        # Verify SLACK is enabled
        assert updated_setting is not None
        slack_config = json.loads(updated_setting.value)
        assert slack_config["enabled"] is True
        
        # Verify disable_other_chat_services was called
        mock_disable.assert_called_once_with(db, "SLACK")


@pytest.mark.asyncio
async def test_update_setting_partial(db: AsyncSession):
    """Test partial update of a setting."""
    # Create a test setting
    setting_data = SettingCreate(
        key="PARTIAL_KEY", 
        value="original", 
        description="Original description"
    )
    await create_setting(db, setting_data)
    
    # Update only the value
    value_update = SettingUpdate(value="updated", description=None)
    value_updated = await update_setting(db, "PARTIAL_KEY", value_update)
    assert value_updated.value == "updated"
    assert value_updated.description == "Original description"
    
    # Update only the description
    desc_update = SettingUpdate(value=None, description="Updated description")
    desc_updated = await update_setting(db, "PARTIAL_KEY", desc_update)
    assert desc_updated.value == "updated"  # Unchanged from previous update
    assert desc_updated.description == "Updated description"


@pytest.mark.asyncio
async def test_update_setting_error_handling(db: AsyncSession):
    """Test error handling in update_setting."""
    # Create a test setting
    setting_data = SettingCreate(key="ERROR_UPDATE", value="original", description="Error test")
    await create_setting(db, setting_data)
    
    # Mock a database error
    with patch.object(db, 'commit', side_effect=Exception("Test error")), \
         patch.object(db, 'rollback') as mock_rollback, \
         pytest.raises(Exception):
        update_data = SettingUpdate(value="updated")
        await update_setting(db, "ERROR_UPDATE", update_data)
        mock_rollback.assert_called_once()


@pytest.mark.asyncio
async def test_delete_setting(db: AsyncSession):
    """Test deleting a setting."""
    # Create a test setting
    setting_data = SettingCreate(key="DELETE_KEY", value="delete_value", description="Delete test")
    await create_setting(db, setting_data)
    
    # Delete the setting
    result = await delete_setting(db, "DELETE_KEY")
    assert result is True
    
    # Verify setting is deleted
    deleted_check = await get_setting(db, "DELETE_KEY")
    assert deleted_check is None
    
    # Test deleting non-existent setting
    nonexistent_delete = await delete_setting(db, "NONEXISTENT_KEY")
    assert nonexistent_delete is False


@pytest.mark.asyncio
async def test_ensure_required_settings(db: AsyncSession):
    """Test ensuring required settings exist."""
    # Define required settings
    required_settings = [
        SettingCreate(key="REQUIRED_1", value="value1", description="Required 1"),
        SettingCreate(key="REQUIRED_2", value="value2", description="Required 2"),
    ]
    
    # Ensure settings exist
    await ensure_required_settings(db, required_settings)
    
    # Verify settings were created
    setting1 = await get_setting(db, "REQUIRED_1")
    assert setting1 is not None
    assert setting1.value == "value1"
    
    setting2 = await get_setting(db, "REQUIRED_2")
    assert setting2 is not None
    assert setting2.value == "value2"
    
    # Call again with same settings - should not change existing settings
    modified_settings = [
        SettingCreate(key="REQUIRED_1", value="changed", description="Changed"),
        SettingCreate(key="REQUIRED_2", value="changed", description="Changed"),
    ]
    await ensure_required_settings(db, modified_settings)
    
    # Verify settings were NOT modified
    setting1_after = await get_setting(db, "REQUIRED_1")
    assert setting1_after.value == "value1"  # Not changed


@pytest.mark.asyncio
async def test_ensure_required_settings_error_handling(db: AsyncSession):
    """Test error handling in ensure_required_settings."""
    # Define a required setting
    required_setting = SettingCreate(key="ERROR_REQUIRED", value="value", description="Required")
    
    # Test with an exception during setting processing
    with patch('app.services.settings.get_setting', side_effect=Exception("Test error")), \
         pytest.raises(Exception):
        await ensure_required_settings(db, [required_setting])
    
    # Test with an exception during creation
    with patch('app.services.settings.get_setting', return_value=await_mock(None)), \
         patch('app.services.settings.create_setting', side_effect=Exception("Creation error")), \
         pytest.raises(Exception):
        await ensure_required_settings(db, [required_setting])