import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.api.commands.escalate import process

# Mock event data
MOCK_EVENT = {
    "id": "test_event_1",
    "rule.name": "Test Alert",
    "network.community_id": "1:test123"
}

MOCK_CASE = {
    "id": "case_123",
    "title": "Test Alert",
    "status": "new"
}

MOCK_RELATED_EVENTS = [
    {"id": "test_event_1", "network.community_id": "1:test123"},
    {"id": "test_event_2", "network.community_id": "1:test123"}
]

@pytest.mark.asyncio
async def test_escalate_with_title():
    """Test escalate command with custom title"""
    with patch('app.api.commands.escalate.SecurityOnionClient') as mock_client:
        # Setup mock client
        client_instance = mock_client.return_value
        client_instance.get_event = AsyncMock(return_value=MOCK_EVENT)
        client_instance.create_case = AsyncMock(return_value=MOCK_CASE)
        client_instance.search_events = AsyncMock(return_value=MOCK_RELATED_EVENTS)
        client_instance.add_event_to_case = AsyncMock()

        # Test command with custom title
        result = await process("!escalate test_event_1 Custom Case Title", "slack", "user123", "testuser")
        
        # Verify case was created with custom title
        client_instance.create_case.assert_called_once_with({
            "title": "Custom Case Title",
            "status": "new"
        })
        
        # Verify events were added
        assert client_instance.add_event_to_case.call_count == 2
        assert "case_123" in result
        assert "2 related events" in result

@pytest.mark.asyncio
async def test_escalate_without_title():
    """Test escalate command using rule name as title"""
    with patch('app.api.commands.escalate.SecurityOnionClient') as mock_client:
        # Setup mock client
        client_instance = mock_client.return_value
        client_instance.get_event = AsyncMock(return_value=MOCK_EVENT)
        client_instance.create_case = AsyncMock(return_value=MOCK_CASE)
        client_instance.search_events = AsyncMock(return_value=MOCK_RELATED_EVENTS)
        client_instance.add_event_to_case = AsyncMock()

        # Test command without title
        result = await process("!escalate test_event_1", "slack", "user123", "testuser")
        
        # Verify case was created with rule name as title
        client_instance.create_case.assert_called_once_with({
            "title": "Test Alert",
            "status": "new"
        })
        
        assert "case_123" in result
        assert "2 related events" in result

@pytest.mark.asyncio
async def test_escalate_event_not_found():
    """Test escalate command with non-existent event"""
    with patch('app.api.commands.escalate.SecurityOnionClient') as mock_client:
        client_instance = mock_client.return_value
        client_instance.get_event = AsyncMock(return_value=None)

        result = await process("!escalate nonexistent_event", "slack", "user123", "testuser")
        assert "Error: Event nonexistent_event not found" in result

@pytest.mark.asyncio
async def test_escalate_no_community_id():
    """Test escalate command with event missing community_id"""
    with patch('app.api.commands.escalate.SecurityOnionClient') as mock_client:
        # Setup mock client with event missing community_id
        event_without_community = {**MOCK_EVENT}
        del event_without_community["network.community_id"]
        
        client_instance = mock_client.return_value
        client_instance.get_event = AsyncMock(return_value=event_without_community)
        client_instance.create_case = AsyncMock(return_value=MOCK_CASE)
        client_instance.add_event_to_case = AsyncMock()

        result = await process("!escalate test_event_1", "slack", "user123", "testuser")
        
        # Verify only original event was added
        client_instance.add_event_to_case.assert_called_once()
        assert "no community ID found" in result.lower()

@pytest.mark.asyncio
async def test_escalate_no_eventid():
    """Test escalate command without event ID"""
    result = await process("!escalate", "slack", "user123", "testuser")
    assert "Error: Event ID is required" in result
