import pytest
from ..app.core.permissions import CommandPermission, has_permission, get_command_permission
from ..app.models.chat_users import ChatUserRole

@pytest.mark.asyncio
async def test_has_permission():
    """Test permission checking logic."""
    # Test public commands
    assert await has_permission(None, CommandPermission.PUBLIC), "Public commands should be accessible without a role"
    assert await has_permission(ChatUserRole.USER, CommandPermission.PUBLIC), "Public commands should be accessible to users"
    assert await has_permission(ChatUserRole.BASIC, CommandPermission.PUBLIC), "Public commands should be accessible to basic users"
    assert await has_permission(ChatUserRole.ADMIN, CommandPermission.PUBLIC), "Public commands should be accessible to admins"
    
    # Test basic commands
    assert not await has_permission(None, CommandPermission.BASIC), "Basic commands should not be accessible without a role"
    assert not await has_permission(ChatUserRole.USER, CommandPermission.BASIC), "Basic commands should not be accessible to users"
    assert await has_permission(ChatUserRole.BASIC, CommandPermission.BASIC), "Basic commands should be accessible to basic users"
    assert await has_permission(ChatUserRole.ADMIN, CommandPermission.BASIC), "Basic commands should be accessible to admins"
    
    # Test admin commands
    assert not await has_permission(None, CommandPermission.ADMIN), "Admin commands should not be accessible without a role"
    assert not await has_permission(ChatUserRole.USER, CommandPermission.ADMIN), "Admin commands should not be accessible to users"
    assert not await has_permission(ChatUserRole.BASIC, CommandPermission.ADMIN), "Admin commands should not be accessible to basic users"
    assert await has_permission(ChatUserRole.ADMIN, CommandPermission.ADMIN), "Admin commands should be accessible to admins"

def test_get_command_permission():
    """Test command permission mapping."""
    # Test known commands
    assert get_command_permission("help") == CommandPermission.PUBLIC, "Help should be public"
    assert get_command_permission("register") == CommandPermission.PUBLIC, "Register should be public"
    assert get_command_permission("alerts") == CommandPermission.ADMIN, "Alerts should be admin"
    assert get_command_permission("detections") == CommandPermission.ADMIN, "Detections should be admin"
    
    # Test unknown command defaults to admin
    assert get_command_permission("nonexistent") == CommandPermission.ADMIN, "Unknown commands should default to admin"

@pytest.mark.asyncio
async def test_command_decorator():
    """Test the requires_permission decorator."""
    from ..app.core.decorators import requires_permission
    from ..app.models.chat_users import ChatUser, ChatService
    
    # Create a test command
    @requires_permission()
    async def test_command(command: str, platform: str, user_id: str = None, username: str = None) -> str:
        return "Success"
    
    # Create test users with different roles
    admin_user = ChatUser(
        platform_id="admin123",
        username="admin",
        platform=ChatService.DISCORD,
        role=ChatUserRole.ADMIN
    )
    basic_user = ChatUser(
        platform_id="basic123",
        username="basic",
        platform=ChatService.DISCORD,
        role=ChatUserRole.BASIC
    )
    regular_user = ChatUser(
        platform_id="user123",
        username="user",
        platform=ChatService.DISCORD,
        role=ChatUserRole.USER
    )
    
    # Test admin command access
    result = await test_command("!detections enable rule1", "discord", "admin123")
    assert result == "Success", "Admin should be able to use admin commands"
    
    # Test basic command access
    result = await test_command("!alerts", "discord", "basic123")
    assert result == "Success", "Basic user should be able to use basic commands"
    
    # Test permission denied
    result = await test_command("!detections enable rule1", "discord", "basic123")
    assert "Permission denied" in result, "Basic user should not be able to use admin commands"
    
    # Test public command access
    result = await test_command("!help", "discord", "user123")
    assert result == "Success", "Regular user should be able to use public commands"
    
    # Test unauthenticated access to public command
    result = await test_command("!help", "discord")
    assert result == "Success", "Unauthenticated user should be able to use public commands"
    
    # Test unauthenticated access to protected command
    result = await test_command("!detections enable rule1", "discord")
    assert "Permission denied" in result, "Unauthenticated user should not be able to use admin commands"
