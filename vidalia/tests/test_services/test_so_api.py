import pytest
from unittest.mock import MagicMock, patch
from src.services.so_api import SecurityOnionAPI

@pytest.fixture
def mock_services():
    """Fixture to mock all service classes."""
    with patch('src.services.so_api.UserService') as mock_user_service, \
         patch('src.services.so_api.AlertsService') as mock_alerts_service, \
         patch('src.services.so_api.PcapService') as mock_pcap_service, \
         patch('src.services.so_api.GridService') as mock_grid_service, \
         patch('src.services.so_api.CaseService') as mock_case_service:
        
        # Set up mock instances
        mock_user_service_instance = MagicMock()
        mock_alerts_service_instance = MagicMock()
        mock_pcap_service_instance = MagicMock()
        mock_grid_service_instance = MagicMock()
        mock_case_service_instance = MagicMock()
        
        # Make the constructors return the mock instances
        mock_user_service.return_value = mock_user_service_instance
        mock_alerts_service.return_value = mock_alerts_service_instance
        mock_pcap_service.return_value = mock_pcap_service_instance
        mock_grid_service.return_value = mock_grid_service_instance
        mock_case_service.return_value = mock_case_service_instance
        
        yield {
            'user': mock_user_service_instance,
            'alerts': mock_alerts_service_instance,
            'pcap': mock_pcap_service_instance,
            'grid': mock_grid_service_instance,
            'case': mock_case_service_instance
        }

def test_initialization(mock_services):
    """Test that the API client initializes all services correctly."""
    # Instantiate the API client (which will use our mocked services)
    api = SecurityOnionAPI(
        base_url="https://securityonion.local",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    # Verify that all services were initialized
    assert api._user_service == mock_services['user']
    assert api._alert_service == mock_services['alerts']
    assert api._pcap_service == mock_services['pcap']
    assert api._grid_service == mock_services['grid']
    assert api._case_service == mock_services['case']

def test_user_operations(mock_services):
    """Test user operations delegation."""
    api = SecurityOnionAPI(
        base_url="https://securityonion.local",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    # Set up return values
    mock_services['user'].get_user_name.return_value = "Test User"
    mock_services['user'].get_users.return_value = [{"id": "user1", "name": "Test User"}]
    
    # Test get_user_name delegation
    result = api.get_user_name("user1")
    assert result == "Test User"
    mock_services['user'].get_user_name.assert_called_once_with("user1")
    
    # Test get_users delegation
    result = api.get_users()
    assert result == [{"id": "user1", "name": "Test User"}]
    mock_services['user'].get_users.assert_called_once()

def test_alert_operations(mock_services):
    """Test alert operations delegation."""
    api = SecurityOnionAPI(
        base_url="https://securityonion.local",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    # Set up return values
    mock_services['alerts'].get_alerts.return_value = [{"id": "alert1", "title": "Test Alert"}]
    
    # Test get_alerts delegation with default parameters
    result = api.get_alerts()
    assert result == [{"id": "alert1", "title": "Test Alert"}]
    mock_services['alerts'].get_alerts.assert_called_with(24, 5)  # Default values
    
    # Test get_alerts delegation with custom parameters
    result = api.get_alerts(hours=48, limit=10)
    assert result == [{"id": "alert1", "title": "Test Alert"}]
    mock_services['alerts'].get_alerts.assert_called_with(48, 10)

def test_pcap_operations(mock_services):
    """Test PCAP operations delegation."""
    api = SecurityOnionAPI(
        base_url="https://securityonion.local",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    # Set up return values
    mock_services['pcap'].create_pcap_job.return_value = 123
    mock_services['pcap'].get_job_status.return_value = {"status": "complete"}
    mock_services['pcap'].download_pcap.return_value = b"pcap_data"
    
    # Test create_pcap_job delegation
    job_data = {"sensor": "sensor1", "start": "2023-01-01", "end": "2023-01-02"}
    result = api.create_pcap_job(job_data)
    assert result == 123
    mock_services['pcap'].create_pcap_job.assert_called_once_with(job_data)
    
    # Test get_job_status delegation
    result = api.get_job_status(123)
    assert result == {"status": "complete"}
    mock_services['pcap'].get_job_status.assert_called_once_with(123)
    
    # Test download_pcap delegation
    result = api.download_pcap(123)
    assert result == b"pcap_data"
    mock_services['pcap'].download_pcap.assert_called_once_with(123)

def test_grid_operations(mock_services):
    """Test grid operations delegation."""
    api = SecurityOnionAPI(
        base_url="https://securityonion.local",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    # Set up return values
    mock_services['grid'].get_grid_nodes.return_value = [{"id": "node1", "name": "Node 1"}]
    mock_services['grid'].get_grid_members.return_value = [{"id": "member1", "name": "Member 1"}]
    
    # Test get_grid_nodes delegation
    result = api.get_grid_nodes()
    assert result == [{"id": "node1", "name": "Node 1"}]
    mock_services['grid'].get_grid_nodes.assert_called_once()
    
    # Test get_grid_members delegation
    result = api.get_grid_members()
    assert result == [{"id": "member1", "name": "Member 1"}]
    mock_services['grid'].get_grid_members.assert_called_once()
    
    # Test restart_node delegation
    api.restart_node("node1")
    mock_services['grid'].restart_node.assert_called_once_with("node1")
    
    # Test reboot_node delegation (should call restart_node)
    api.reboot_node("node2")
    mock_services['grid'].restart_node.assert_called_with("node2")

def test_case_operations(mock_services):
    """Test case operations delegation."""
    api = SecurityOnionAPI(
        base_url="https://securityonion.local",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    # Set up return values
    mock_services['case'].get_cases.return_value = [{"id": "case1", "title": "Test Case"}]
    mock_services['case'].get_case.return_value = {"id": "case1", "title": "Test Case"}
    mock_services['case'].create_case.return_value = {"id": "case2", "title": "New Case"}
    mock_services['case'].update_case.return_value = {"id": "case1", "title": "Updated Case"}
    mock_services['case'].add_case_comment.return_value = {"id": "case1", "comments": ["New comment"]}
    
    # Test get_cases delegation
    result = api.get_cases()
    assert result == [{"id": "case1", "title": "Test Case"}]
    mock_services['case'].get_cases.assert_called_once()
    
    # Test get_case delegation
    result = api.get_case("case1")
    assert result == {"id": "case1", "title": "Test Case"}
    mock_services['case'].get_case.assert_called_once_with("case1")
    
    # Test create_case delegation
    case_data = {"title": "New Case", "description": "Description"}
    result = api.create_case(case_data)
    assert result == {"id": "case2", "title": "New Case"}
    mock_services['case'].create_case.assert_called_once_with(case_data)
    
    # Test update_case delegation
    update_data = {"title": "Updated Case"}
    result = api.update_case("case1", update_data)
    assert result == {"id": "case1", "title": "Updated Case"}
    mock_services['case'].update_case.assert_called_once_with("case1", update_data)
    
    # Test add_case_comment delegation with default hours
    result = api.add_case_comment("case1", "New comment")
    assert result == {"id": "case1", "comments": ["New comment"]}
    mock_services['case'].add_case_comment.assert_called_with("case1", "New comment", 0.0)
    
    # Test add_case_comment delegation with custom hours
    result = api.add_case_comment("case1", "New comment", 1.5)
    assert result == {"id": "case1", "comments": ["New comment"]}
    mock_services['case'].add_case_comment.assert_called_with("case1", "New comment", 1.5)
    
    # Test delete_case delegation
    api.delete_case("case1")
    mock_services['case'].delete_case.assert_called_once_with("case1")