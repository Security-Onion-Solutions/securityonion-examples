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
from tests.utils import await_mock, create_mock_db_session, setup_mock_db


@pytest.mark.asyncio
async def test_settings_service_mock():
    """Test settings service with mocked DB."""
    # Create a mock database session for Python 3.13 compatibility
    db = setup_mock_db()
    
    # Test create_setting with mocked database
    mock_setting = MagicMock(spec=SettingsModel)
    mock_setting.key = "TEST_KEY"
    mock_setting.value = "test_value"  # Testing the property getter
    mock_setting.description = "Test setting"
    
    # Setup mock behavior for db.add, commit, and refresh
    db.add = MagicMock()
    
    # Test the create_setting function with the mocked dependencies
    with patch.object(db, 'commit', new_callable=AsyncMock) as mock_commit, \
         patch.object(db, 'refresh', new_callable=AsyncMock) as mock_refresh, \
         patch('app.services.settings.SettingsModel', return_value=mock_setting):
        
        setting_data = SettingCreate(key="TEST_KEY", value="test_value", description="Test setting")
        result = await create_setting(db, setting_data)
        
        # Verify interactions with the database
        db.add.assert_called_once()
        mock_commit.assert_called_once()
        mock_refresh.assert_called_once_with(mock_setting)
        
        # Verify the result
        assert result.key == "TEST_KEY"
        assert result.value == "test_value"
        assert result.description == "Test setting"
        
    # Test get_setting with mocked database
    db_setting = MagicMock(spec=SettingsModel)
    db_setting.key = "MOCK_KEY"
    db_setting.value = "mock_value"
    
    # Setup mock behavior for db.execute
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = db_setting
    
    # Make it awaitable for Python 3.13
    mock_result_awaitable = await_mock(mock_result)
    
    with patch.object(db, 'execute', return_value=mock_result_awaitable):
        # Test the get_setting function
        setting = await get_setting(db, "MOCK_KEY")
        
        # Verify the result
        assert setting is db_setting
        assert setting.key == "MOCK_KEY"
        assert setting.value == "mock_value"
    
    # Test get_settings with mocked database
    mock_settings = [MagicMock(spec=SettingsModel) for _ in range(3)]
    for i, setting in enumerate(mock_settings):
        setting.key = f"KEY_{i}"
        setting.value = f"value_{i}"
    
    # Setup mock for scalars result
    mock_scalars_result = MagicMock()
    mock_scalars_result.all.return_value = mock_settings
    
    # Setup mock for first result with scalars method
    mock_result = MagicMock()
    mock_result.scalars.return_value = await_mock(mock_scalars_result)
    
    # Make the result awaitable
    mock_execute_result = await_mock(mock_result)
    
    with patch.object(db, 'execute', return_value=mock_execute_result):
        # Test the get_settings function
        settings = await get_settings(db)
        
        # Verify we get a list with our mock settings
        assert isinstance(settings, list)
        assert len(settings) == 3
        assert settings == mock_settings
    
    # Test update_setting with mocked database
    # First create a proper mock for get_setting that returns the existing setting immediately
    existing_setting = MagicMock(spec=SettingsModel)
    existing_setting.key = "UPDATE_KEY"
    existing_setting.value = "original_value"
    existing_setting.description = "Original description"
    
    # Define a custom side effect function for get_setting
    async def get_setting_mock(db, key):
        return existing_setting
    
    with patch('app.services.settings.get_setting', side_effect=get_setting_mock), \
         patch('app.services.settings.is_chat_service_enabled', return_value=await_mock(False)), \
         patch('app.services.settings.disable_other_chat_services', new_callable=AsyncMock), \
         patch.object(db, 'commit', new_callable=AsyncMock) as mock_commit, \
         patch.object(db, 'refresh', new_callable=AsyncMock) as mock_refresh:
        
        # Test updating the setting
        update_data = SettingUpdate(value="updated_value", description="Updated description")
        updated_setting = await update_setting(db, "UPDATE_KEY", update_data)
        
        # Verify interactions with the database
        mock_commit.assert_called_once()
        mock_refresh.assert_called_once_with(existing_setting)
        
        # Verify the setting was updated
        assert updated_setting is existing_setting
    
    # Test delete_setting with mocked database
    # Use the same side_effect approach for proper Python 3.13 compatibility
    with patch('app.services.settings.get_setting', side_effect=get_setting_mock), \
         patch.object(db, 'delete', new_callable=AsyncMock) as mock_delete, \
         patch.object(db, 'commit', new_callable=AsyncMock) as mock_commit:
        
        # Test deleting the setting
        result = await delete_setting(db, "DELETE_KEY")
        
        # Verify interactions with the database
        mock_delete.assert_called_once_with(existing_setting)
        mock_commit.assert_called_once()
        
        # Verify the result
        assert result is True
    
    # Test ensure_required_settings with mocked database
    required_settings = [
        SettingCreate(key="REQUIRED_1", value="value1", description="Required 1"),
        SettingCreate(key="REQUIRED_2", value="value2", description="Required 2"),
    ]
    
    # Create a mock to test ensuring required settings
    mock_existing_setting = MagicMock(spec=SettingsModel)
    mock_new_setting = MagicMock(spec=SettingsModel)
    
    # Use side_effect function for get_setting to return different results based on key
    settings_responses = {
        "REQUIRED_1": mock_existing_setting,
        "REQUIRED_2": None
    }
    
    async def get_setting_for_ensure(db, key):
        return settings_responses.get(key)
    
    # Mock create_setting function with proper async behavior
    async def create_setting_mock(db, setting):
        return mock_new_setting
    
    with patch('app.services.settings.get_setting', side_effect=get_setting_for_ensure), \
         patch('app.services.settings.create_setting', side_effect=create_setting_mock) as mock_create:
        
        # Test ensuring required settings
        await ensure_required_settings(db, required_settings)
        
        # Verify create_setting was called once for the missing setting
        assert mock_create.call_count == 1
        mock_create.assert_called_with(db, required_settings[1])


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
    mock_db = setup_mock_db()
    mock_scalar = MagicMock(spec=SettingsModel)
    mock_scalar.key = "COROUTINE_KEY"
    mock_scalar.value = "coroutine_value"
    
    # Setup the execution chain with proper awaits for Python 3.13
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_scalar
    
    with patch.object(mock_db, 'execute', return_value=await_mock(mock_result)):
        setting = await get_setting(mock_db, "COROUTINE_KEY")
        assert setting is mock_scalar
        assert setting.key == "COROUTINE_KEY"
        assert setting.value == "coroutine_value"


@pytest.mark.asyncio
async def test_get_setting_no_result_found(db: AsyncSession):
    """Test get_setting behavior with NoResultFound exception."""
    # Mock execute to raise NoResultFound
    with patch.object(db, 'execute', side_effect=NoResultFound("Test error")):
        result = await get_setting(db, "NONEXISTENT_KEY")
        assert result is None


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
    assert first_page[0].key != second_page[0].key
    
    # Test with coroutine awaits in Python 3.13
    mock_db = setup_mock_db()
    
    # Setup mock objects with proper awaits
    mock_all = [MagicMock(spec=SettingsModel) for _ in range(3)]
    for i, setting in enumerate(mock_all):
        setting.key = f"KEY_{i}"
        setting.value = f"value_{i}"
    
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = mock_all
    
    mock_result = MagicMock()
    mock_result.scalars.return_value = await_mock(mock_scalars)
    
    with patch.object(mock_db, 'execute', return_value=await_mock(mock_result)):
        settings = await get_settings(mock_db)
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
async def test_disable_other_chat_services():
    """Test disabling other chat services with all branches using mocks."""
    # Create a mock db and settings
    mock_db = setup_mock_db()
    mock_settings = {}
    
    # Create mock settings for each service
    for service in CHAT_SERVICES:
        setting = MagicMock(spec=SettingsModel)
        setting.key = service
        if service == "DISCORD":
            # This is the one we'll keep enabled
            setting.value = json.dumps({"enabled": True, "token": f"{service}_token"})
        else:
            # These will be disabled
            setting.value = json.dumps({"enabled": True, "token": f"{service}_token"})
        mock_settings[service] = setting
    
    # Create a mock function for get_setting that returns our mock settings
    async def mock_get_setting(db, key):
        return mock_settings.get(key)
    
    # Test the main functionality of disabling all services except DISCORD
    with patch('app.services.settings.get_setting', side_effect=mock_get_setting):
        await disable_other_chat_services(mock_db, "DISCORD")
        
        # Verify DISCORD is still enabled
        discord_config = json.loads(mock_settings["DISCORD"].value)
        assert discord_config["enabled"] is True
        
        # Verify others are disabled
        for service in [s for s in CHAT_SERVICES if s != "DISCORD"]:
            service_config = json.loads(mock_settings[service].value)
            assert service_config["enabled"] is False
    
    # Test error handling branches
    
    # 1. Test with invalid JSON
    mock_settings["SLACK"].value = "not json"  # Invalid JSON
    
    with patch('app.services.settings.get_setting', side_effect=mock_get_setting):
        # This should not raise an exception even with invalid JSON
        await disable_other_chat_services(mock_db, "MATRIX")
    
    # 2. Test when a service doesn't exist
    async def mock_get_some_missing(db, key):
        # Return None for TEAMS to simulate missing service
        if key == "TEAMS":
            return None
        return mock_settings.get(key)
    
    with patch('app.services.settings.get_setting', side_effect=mock_get_some_missing):
        # Should not raise exceptions when a service is missing
        await disable_other_chat_services(mock_db, "DISCORD")
    
    # 3. Test when a setting doesn't have 'enabled' flag
    for service in CHAT_SERVICES:
        if service != "DISCORD":
            mock_settings[service].value = json.dumps({"token": f"{service}_token"})  # No enabled flag
    
    with patch('app.services.settings.get_setting', side_effect=mock_get_setting):
        # Should work without errors when settings don't have enabled flag
        await disable_other_chat_services(mock_db, "DISCORD")


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
    # Create a mock db to avoid conflicts with other tests
    mock_db = setup_mock_db()
    
    # Create a mock setting that will be returned by get_setting
    mock_setting = MagicMock(spec=SettingsModel)
    mock_setting.key = "SLACK"
    mock_setting.value = json.dumps({"enabled": False, "token": "slack_token"})
    
    # Create a mock function for get_setting that returns our mock setting
    async def mock_get_setting(db, key):
        return mock_setting
        
    # Mock checking if it's a chat service being enabled
    async def mock_is_chat_service_enabled(key, value):
        return True  # Pretend it's being enabled
    
    # Mock the disable_other_chat_services function
    async def mock_disable(db, key):
        return None  # Do nothing
    
    # Patch all necessary functions
    with patch('app.services.settings.get_setting', side_effect=mock_get_setting), \
         patch('app.services.settings.is_chat_service_enabled', side_effect=mock_is_chat_service_enabled), \
         patch('app.services.settings.disable_other_chat_services', side_effect=mock_disable) as mock_disable_spy, \
         patch.object(mock_db, 'commit', new_callable=AsyncMock), \
         patch.object(mock_db, 'refresh', new_callable=AsyncMock):
        
        # Enable SLACK
        update_data = SettingUpdate(value=json.dumps({"enabled": True, "token": "new_slack_token"}))
        updated_setting = await update_setting(mock_db, "SLACK", update_data)
        
        # Verify the result
        assert updated_setting is mock_setting
        
        # Verify disable_other_chat_services was called
        mock_disable_spy.assert_called_once_with(mock_db, "SLACK")


@pytest.mark.asyncio
async def test_update_setting_partial(db: AsyncSession):
    """Test partial update of a setting."""
    # Create a mock db to avoid conflicts with other tests
    mock_db = setup_mock_db()
    
    # Create initial setting state
    mock_setting = MagicMock(spec=SettingsModel)
    mock_setting.key = "PARTIAL_KEY"
    mock_setting.value = "original"
    mock_setting.description = "Original description"
    
    # Create a mock function for get_setting that returns our mock setting
    async def mock_get_setting(db, key):
        return mock_setting
        
    # Mock is_chat_service_enabled
    async def mock_is_chat_service_enabled(key, value):
        return False  # Not a chat service being enabled
    
    # Patch all necessary functions for first update (value only)
    with patch('app.services.settings.get_setting', side_effect=mock_get_setting), \
         patch('app.services.settings.is_chat_service_enabled', side_effect=mock_is_chat_service_enabled), \
         patch.object(mock_db, 'commit', new_callable=AsyncMock), \
         patch.object(mock_db, 'refresh', new_callable=AsyncMock):
        
        # Update only the value
        value_update = SettingUpdate(value="updated", description=None)
        value_updated = await update_setting(mock_db, "PARTIAL_KEY", value_update)
        
        # The mock_setting object is updated by the function
        assert value_updated.value == "updated"
        assert value_updated.description == "Original description"
    
    # Patch all necessary functions for second update (description only)
    with patch('app.services.settings.get_setting', side_effect=mock_get_setting), \
         patch('app.services.settings.is_chat_service_enabled', side_effect=mock_is_chat_service_enabled), \
         patch.object(mock_db, 'commit', new_callable=AsyncMock), \
         patch.object(mock_db, 'refresh', new_callable=AsyncMock):
        
        # Update only the description
        # We need to reuse the value since it's required in the schema
        desc_update = SettingUpdate(value="updated", description="Updated description")
        desc_updated = await update_setting(mock_db, "PARTIAL_KEY", desc_update)
        
        # Description should be updated
        assert desc_updated.value == "updated"
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
    
    # Create a mock function for get_setting that returns None (setting doesn't exist)
    async def mock_get_none(db, key):
        return None
        
    # Test with an exception during creation
    with patch('app.services.settings.get_setting', side_effect=mock_get_none), \
         patch('app.services.settings.create_setting', side_effect=Exception("Creation error")), \
         pytest.raises(Exception):
        await ensure_required_settings(db, [required_setting])