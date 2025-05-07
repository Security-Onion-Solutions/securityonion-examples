"""Tests for settings API and services."""
import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.api.settings import (
    read_settings,
    read_setting,
    create_setting_endpoint,
    update_setting_endpoint,
    delete_setting_endpoint,
    get_so_status,
    test_so_connection,
    init_default_settings
)
from app.services.settings import (
    create_setting,
    get_setting,
    get_settings,
    update_setting,
    delete_setting,
    ensure_required_settings,
    is_chat_service_enabled,
    disable_other_chat_services
)
from app.models.settings import Settings as SettingsModel
from app.schemas.settings import Setting, SettingCreate, SettingUpdate
from app.core.default_settings import DEFAULT_SETTINGS
from .utils import await_mock, make_mock_awaitable

client = TestClient(app)

def await_mock(return_value):
    # Helper function to make mock return values awaitable in Python 3.13
    async def _awaitable():
        return return_value
    return _awaitable()

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock(spec=AsyncSession)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def mock_setting():
    """Create a mock setting."""
    setting = MagicMock(spec=SettingsModel)
    setting.key = "test_key"
    setting.value = "test_value"
    setting.description = "Test setting"
    return setting


@pytest.mark.asyncio
async def test_create_setting(db, mock_setting):
    """Test create_setting service function."""
    # Mock DB operation
    db.add = MagicMock()
    
    # Create setting data
    setting_data = SettingCreate(
        key="test_key",
        value="test_value",
        description="Test setting"
    )
    
    # Mock the instance creation
    with patch("app.services.settings.SettingsModel") as mock_model:
        mock_model.return_value = mock_setting
        
        # Test the function
        result = await create_setting(db, setting_data)
        
        # Verify
        assert result == mock_setting
        mock_model.assert_called_once_with(key="test_key", description="Test setting")
        db.add.assert_called_once_with(mock_setting)
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(mock_setting)


@pytest.mark.asyncio
async def test_get_setting(db, mock_setting):
    """Test get_setting service function."""
    # Mock DB query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_setting

    mock_result.scalar_one_or_none.return_value = await_mock(mock_result.scalar_one_or_none.return_value)
    make_mock_awaitable(mock_result, "scalar_one_or_none")
    
    db.execute.return_value = mock_result

    
    db.execute.return_value = await_mock(db.execute.return_value)
    make_mock_awaitable(db, "execute")
    
    # Test the function
    result = await get_setting(db, "test_key")
    
    # Verify
    assert result == mock_setting
    db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_setting_not_found(db):
    """Test get_setting with nonexistent key."""
    # Mock DB query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_result.scalar_one_or_none.return_value = await_mock(mock_result.scalar_one_or_none.return_value)
    make_mock_awaitable(mock_result, "scalar_one_or_none")
    
    db.execute.return_value = mock_result

    
    db.execute.return_value = await_mock(db.execute.return_value)
    make_mock_awaitable(db, "execute")
    
    # Test the function
    result = await get_setting(db, "nonexistent")
    
    # Verify
    assert result is None
    db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_settings(db, mock_setting):
    """Test get_settings service function."""
    # Mock DB query result
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_setting]
    mock_result.scalars.return_value = mock_scalars
    make_mock_awaitable(mock_result, "scalars")
    
    db.execute.return_value = mock_result

    
    db.execute.return_value = await_mock(db.execute.return_value)
    make_mock_awaitable(db, "execute")
    
    # Test the function
    result = await get_settings(db)
    
    # Verify
    assert len(result) == 1
    assert result[0] == mock_setting
    db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_is_chat_service_enabled():
    """Test is_chat_service_enabled function."""
    # Test with enabled service
    enabled = await is_chat_service_enabled("DISCORD", json.dumps({"enabled": True}))
    assert enabled is True
    
    # Test with disabled service
    disabled = await is_chat_service_enabled("DISCORD", json.dumps({"enabled": False}))
    assert disabled is False
    
    # Test with non-chat service
    non_chat = await is_chat_service_enabled("securityOnion", json.dumps({"enabled": True}))
    assert non_chat is False
    
    # Test with invalid JSON
    invalid_json = await is_chat_service_enabled("DISCORD", "not_json")
    assert invalid_json is False


@pytest.mark.asyncio
async def test_disable_other_chat_services(db, mock_setting):
    """Test disable_other_chat_services function."""
    with patch("app.services.settings.get_setting") as mock_get_setting:
        # Create mock settings for each chat service
        slack_setting = MagicMock(spec=SettingsModel)
        slack_setting.value = json.dumps({"enabled": True})
        
        discord_setting = MagicMock(spec=SettingsModel)
        discord_setting.value = json.dumps({"enabled": True})
        
        matrix_setting = MagicMock(spec=SettingsModel)
        matrix_setting.value = json.dumps({"enabled": True})
        
        # Configure the mock to return different settings
        async def get_setting_side_effect(db, key):
            if key == "SLACK":
                return slack_setting
            elif key == "DISCORD":
                return discord_setting
            elif key == "MATRIX":
                return matrix_setting
            else:
                return None
                
        mock_get_setting.side_effect = get_setting_side_effect
        
        # Test the function - disable all except Discord
        await disable_other_chat_services(db, "DISCORD")
        
        # Verify that Slack and Matrix were disabled, but Discord wasn't changed
        updated_slack = json.loads(slack_setting.value)
        assert updated_slack["enabled"] is False
        
        updated_matrix = json.loads(matrix_setting.value)
        assert updated_matrix["enabled"] is False
        
        # Discord should still be enabled
        updated_discord = json.loads(discord_setting.value)
        assert updated_discord["enabled"] is True


@pytest.mark.asyncio
async def test_update_setting(db, mock_setting):
    """Test update_setting service function."""
    with patch("app.services.settings.get_setting") as mock_get_setting, \
         patch("app.services.settings.is_chat_service_enabled") as mock_is_enabled, \
         patch("app.services.settings.disable_other_chat_services") as mock_disable:
        # Mock getting the existing setting
        mock_get_setting.return_value = mock_setting
        
        # Mock chat service check
        mock_is_enabled.return_value = False
        
        # Update data
        update_data = SettingUpdate(
            value="updated_value",
            description="Updated description"
        )
        
        # Test the function
        result = await update_setting(db, "test_key", update_data)
        
        # Verify
        assert result == mock_setting
        assert mock_setting.value == "updated_value"
        assert mock_setting.description == "Updated description"
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(mock_setting)
        
        # Verify chat service handling wasn't triggered
        mock_disable.assert_not_called()


@pytest.mark.asyncio
async def test_update_setting_enable_chat_service(db, mock_setting):
    """Test update_setting when enabling a chat service."""
    with patch("app.services.settings.get_setting") as mock_get_setting, \
         patch("app.services.settings.is_chat_service_enabled") as mock_is_enabled, \
         patch("app.services.settings.disable_other_chat_services") as mock_disable:
        # Mock getting the existing setting
        mock_get_setting.return_value = mock_setting
        
        # Mock chat service check - this is a chat service being enabled
        mock_is_enabled.return_value = True
        
        # Update data
        update_data = SettingUpdate(
            value=json.dumps({"enabled": True}),
            description="Updated description"
        )
        
        # Test the function
        result = await update_setting(db, "DISCORD", update_data)
        
        # Verify
        assert result == mock_setting
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(mock_setting)
        
        # Verify chat service handling was triggered
        mock_disable.assert_called_once_with(db, "DISCORD")


@pytest.mark.asyncio
async def test_update_setting_not_found(db):
    """Test update_setting with nonexistent key."""
    with patch("app.services.settings.get_setting") as mock_get_setting:
        # Mock getting the nonexistent setting
        mock_get_setting.return_value = None
        
        # Update data
        update_data = SettingUpdate(
            value="updated_value",
            description="Updated description"
        )
        
        # Test the function
        result = await update_setting(db, "nonexistent", update_data)
        
        # Verify
        assert result is None
        db.commit.assert_not_called()
        db.refresh.assert_not_called()


@pytest.mark.asyncio
async def test_delete_setting(db, mock_setting):
    """Test delete_setting service function."""
    with patch("app.services.settings.get_setting") as mock_get_setting:
        # Mock getting the existing setting
        mock_get_setting.return_value = mock_setting
        
        # Test the function
        result = await delete_setting(db, "test_key")
        
        # Verify
        assert result is True
        db.delete.assert_called_once_with(mock_setting)
        db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_setting_not_found(db):
    """Test delete_setting with nonexistent key."""
    with patch("app.services.settings.get_setting") as mock_get_setting:
        # Mock getting the nonexistent setting
        mock_get_setting.return_value = None
        
        # Test the function
        result = await delete_setting(db, "nonexistent")
        
        # Verify
        assert result is False
        db.delete.assert_not_called()
        db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_required_settings(db):
    """Test ensure_required_settings service function."""
    with patch("app.services.settings.get_setting") as mock_get_setting, \
         patch("app.services.settings.create_setting") as mock_create:
        # Mock getting the setting (not found)
        mock_get_setting.return_value = None
        
        # Test data
        required_settings = [
            SettingCreate(key="key1", value="value1", description="Setting 1"),
            SettingCreate(key="key2", value="value2", description="Setting 2")
        ]
        
        # Test the function
        await ensure_required_settings(db, required_settings)
        
        # Verify
        assert mock_get_setting.call_count == 2
        assert mock_create.call_count == 2


@pytest.mark.asyncio
async def test_ensure_required_settings_existing(db, mock_setting):
    """Test ensure_required_settings with existing settings."""
    with patch("app.services.settings.get_setting") as mock_get_setting, \
         patch("app.services.settings.create_setting") as mock_create:
        # Mock getting the setting (found)
        mock_get_setting.return_value = mock_setting
        
        # Test data
        required_settings = [
            SettingCreate(key="key1", value="value1", description="Setting 1"),
            SettingCreate(key="key2", value="value2", description="Setting 2")
        ]
        
        # Test the function
        await ensure_required_settings(db, required_settings)
        
        # Verify
        assert mock_get_setting.call_count == 2
        assert mock_create.call_count == 0


# API endpoint tests

@pytest.mark.asyncio
async def test_read_settings_api(db, mock_setting):
    """Test read_settings API endpoint."""
    with patch("app.api.settings.get_settings") as mock_get_settings:
        # Mock getting all settings
        mock_get_settings.return_value = [mock_setting]
        
        # Test the function
        result = await read_settings(db=db)
        
        # Verify
        assert len(result) == 1
        assert result[0] == mock_setting
        mock_get_settings.assert_called_once_with(db, skip=0, limit=100)


@pytest.mark.asyncio
async def test_read_setting_api(db, mock_setting):
    """Test read_setting API endpoint."""
    with patch("app.api.settings.get_setting") as mock_get_setting:
        # Mock getting the setting
        mock_get_setting.return_value = mock_setting
        
        # Test the function
        result = await read_setting("test_key", db)
        
        # Verify
        assert result == mock_setting
        mock_get_setting.assert_called_once_with(db, "test_key")


@pytest.mark.asyncio
async def test_read_setting_api_not_found(db):
    """Test read_setting API endpoint with nonexistent key."""
    with patch("app.api.settings.get_setting") as mock_get_setting:
        # Mock getting the setting (not found)
        mock_get_setting.return_value = None
        
        # Test the function raises exception
        with pytest.raises(HTTPException) as exc_info:
            await read_setting("nonexistent", db)
        
        # Verify exception details
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_setting_api(db, mock_setting):
    """Test create_setting_endpoint API endpoint."""
    with patch("app.api.settings.get_setting") as mock_get_setting, \
         patch("app.api.settings.create_setting") as mock_create:
        # Mock getting the setting (not found)
        mock_get_setting.return_value = None
        
        # Mock creating the setting
        mock_create.return_value = mock_setting
        
        # Test data
        setting_data = SettingCreate(
            key="test_key",
            value="test_value",
            description="Test setting"
        )
        
        # Test the function
        result = await create_setting_endpoint(setting_data, db)
        
        # Verify
        assert result == mock_setting
        mock_get_setting.assert_called_once_with(db, "test_key")
        mock_create.assert_called_once_with(db, setting_data)


@pytest.mark.asyncio
async def test_create_setting_api_existing(db, mock_setting):
    """Test create_setting_endpoint with existing key."""
    with patch("app.api.settings.get_setting") as mock_get_setting:
        # Mock getting the setting (found)
        mock_get_setting.return_value = mock_setting
        
        # Test data
        setting_data = SettingCreate(
            key="test_key",
            value="test_value",
            description="Test setting"
        )
        
        # Test the function raises exception
        with pytest.raises(HTTPException) as exc_info:
            await create_setting_endpoint(setting_data, db)
        
        # Verify exception details
        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_setting_api(db, mock_setting):
    """Test update_setting_endpoint API endpoint."""
    with patch("app.api.settings.update_setting") as mock_update, \
         patch("app.core.securityonion.client") as mock_so, \
         patch("app.core.discord.client") as mock_discord, \
         patch("app.core.slack.client") as mock_slack, \
         patch("app.core.matrix.client") as mock_matrix:
        # Mock updating the setting
        mock_update.return_value = mock_setting
        
        # Mock client initializations
        for client in [mock_so, mock_discord, mock_slack, mock_matrix]:
            client.initialize = AsyncMock()
            
        # Also mock Security Onion test_connection
        mock_so.test_connection = AsyncMock()
        
        # Test data
        update_data = SettingUpdate(
            value="updated_value",
            description="Updated description"
        )
        
        # Test the function with a regular setting
        result = await update_setting_endpoint("test_key", update_data, db)
        
        # Verify
        assert result == mock_setting
        mock_update.assert_called_once_with(db, "test_key", update_data)
        
        # Verify no clients were initialized
        for client in [mock_so, mock_discord, mock_slack, mock_matrix]:
            client.initialize.assert_not_called()
            
        # Test with Security Onion setting
        mock_update.reset_mock()
        result = await update_setting_endpoint("securityOnion", update_data, db)
        
        # Verify SO client was initialized and tested
        mock_so.initialize.assert_called_once()
        mock_so.test_connection.assert_called_once()
        
        # Test with Discord setting
        mock_update.reset_mock()
        mock_so.initialize.reset_mock()
        mock_so.test_connection.reset_mock()
        
        result = await update_setting_endpoint("DISCORD", update_data, db)
        
        # Verify Discord client was initialized
        mock_discord.initialize.assert_called_once()
        
        # Test with Slack setting
        mock_update.reset_mock()
        mock_discord.initialize.reset_mock()
        
        result = await update_setting_endpoint("SLACK", update_data, db)
        
        # Verify Slack client was initialized
        mock_slack.initialize.assert_called_once()
        
        # Test with Matrix setting
        mock_update.reset_mock()
        mock_slack.initialize.reset_mock()
        
        result = await update_setting_endpoint("MATRIX", update_data, db)
        
        # Verify Matrix client was initialized
        mock_matrix.initialize.assert_called_once()


@pytest.mark.asyncio
async def test_update_setting_api_not_found(db):
    """Test update_setting_endpoint with nonexistent key."""
    with patch("app.api.settings.update_setting") as mock_update:
        # Mock updating the setting (not found)
        mock_update.return_value = None
        
        # Test data
        update_data = SettingUpdate(
            value="updated_value",
            description="Updated description"
        )
        
        # Test the function raises exception
        with pytest.raises(HTTPException) as exc_info:
            await update_setting_endpoint("nonexistent", update_data, db)
        
        # Verify exception details
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_delete_setting_api(db):
    """Test delete_setting_endpoint API endpoint."""
    with patch("app.api.settings.delete_setting") as mock_delete:
        # Mock deleting the setting (success)
        mock_delete.return_value = True
        
        # Test the function
        result = await delete_setting_endpoint("test_key", db)
        
        # Verify
        assert result == {"message": "Setting 'test_key' deleted"}
        mock_delete.assert_called_once_with(db, "test_key")


@pytest.mark.asyncio
async def test_delete_setting_api_not_found(db):
    """Test delete_setting_endpoint with nonexistent key."""
    with patch("app.api.settings.delete_setting") as mock_delete:
        # Mock deleting the setting (not found)
        mock_delete.return_value = False
        
        # Test the function raises exception
        with pytest.raises(HTTPException) as exc_info:
            await delete_setting_endpoint("nonexistent", db)
        
        # Verify exception details
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_so_status():
    """Test get_so_status API endpoint."""
    with patch("app.api.settings.so_client") as mock_so:
        # Mock Security Onion client status
        mock_so.get_status.return_value = {
            "connected": True,
            "base_url": "https://example.com"
        }
        
        # Test the function
        result = await get_so_status()
        
        # Verify
        assert result["connected"] is True
        assert result["base_url"] == "https://example.com"
        mock_so.get_status.assert_called_once()


@pytest.mark.asyncio
async def test_get_so_status_error():
    """Test get_so_status with error."""
    with patch("app.api.settings.so_client") as mock_so:
        # Mock Security Onion client status raising an exception
        mock_so.get_status.side_effect = Exception("Connection error")
        
        # Test the function
        result = await get_so_status()
        
        # Verify error handling
        assert result["connected"] is False
        assert "error" in result
        assert "Connection error" in result["error"]
        mock_so.get_status.assert_called_once()


@pytest.mark.asyncio
async def test_test_so_connection():
    """Test test_so_connection API endpoint."""
    with patch("app.api.settings.so_client") as mock_so:
        # Mock Security Onion client
        mock_so.initialize = AsyncMock()
        mock_so.test_connection = AsyncMock(return_value=True)
        mock_so.get_status.return_value = {
            "connected": True,
            "base_url": "https://example.com"
        }
        
        # Test the function
        result = await test_so_connection()
        
        # Verify
        assert result["success"] is True
        assert result["status"]["connected"] is True
        assert result["status"]["base_url"] == "https://example.com"
        mock_so.initialize.assert_called_once()
        mock_so.test_connection.assert_called_once()
        mock_so.get_status.assert_called_once()


@pytest.mark.asyncio
async def test_test_so_connection_error():
    """Test test_so_connection with error."""
    with patch("app.api.settings.so_client") as mock_so:
        # Mock Security Onion client initialization raising an exception
        mock_so.initialize = AsyncMock(side_effect=Exception("Connection error"))
        
        # Test the function
        result = await test_so_connection()
        
        # Verify error handling
        assert result["success"] is False
        assert result["status"]["connected"] is False
        assert "Connection error" in result["status"]["error"]
        mock_so.initialize.assert_called_once()


@pytest.mark.asyncio
async def test_init_default_settings(db):
    """Test init_default_settings function."""
    # Mock DB execution for initial checks
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("existing_key",)]
    db.execute.return_value = mock_result

    db.execute.return_value = await_mock(db.execute.return_value)
    make_mock_awaitable(db, "execute")
    
    # Mock settings operations
    with patch("app.api.settings.get_setting") as mock_get_setting, \
         patch("app.api.settings.update_setting") as mock_update, \
         patch("app.api.settings.create_setting") as mock_create:
        # Mock existing setting
        existing_setting = MagicMock(spec=SettingsModel)
        existing_setting.value = ""  # Empty value should be updated
        mock_get_setting.return_value = existing_setting
        
        # Test the function
        await init_default_settings(db)
        
        # Verify settings were checked and created/updated
        assert mock_get_setting.call_count > 0
        assert mock_update.call_count > 0
        assert mock_create.call_count > 0