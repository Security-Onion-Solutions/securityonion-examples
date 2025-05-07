import pytest
from app.core.permissions import CommandPermission, has_permission, get_command_permission
from app.models.chat_users import ChatUserRole

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

@pytest.mark.skip(reason="This test requires mocking of the chat_users service, moved to test_decorators.py")
@pytest.mark.asyncio
async def test_command_decorator():
    """Test the requires_permission decorator."""
    # This test has been moved to a separate test file dedicated to testing decorators
    # as it requires mocking of the underlying chat_users service
    pass

@pytest.mark.asyncio
async def test_permission_hierarchy():
    """Test the permission hierarchy to ensure roles have the right levels."""
    # None user should only have access to public commands
    assert await has_permission(None, CommandPermission.PUBLIC)
    assert not await has_permission(None, CommandPermission.BASIC)
    assert not await has_permission(None, CommandPermission.ADMIN)
    
    # USER role should only have access to public commands
    assert await has_permission(ChatUserRole.USER, CommandPermission.PUBLIC)
    assert not await has_permission(ChatUserRole.USER, CommandPermission.BASIC)
    assert not await has_permission(ChatUserRole.USER, CommandPermission.ADMIN)
    
    # BASIC role should have access to public and basic commands, but not admin commands
    assert await has_permission(ChatUserRole.BASIC, CommandPermission.PUBLIC)
    assert await has_permission(ChatUserRole.BASIC, CommandPermission.BASIC)
    assert not await has_permission(ChatUserRole.BASIC, CommandPermission.ADMIN)
    
    # ADMIN role should have access to all command levels
    assert await has_permission(ChatUserRole.ADMIN, CommandPermission.PUBLIC)
    assert await has_permission(ChatUserRole.ADMIN, CommandPermission.BASIC)
    assert await has_permission(ChatUserRole.ADMIN, CommandPermission.ADMIN)
