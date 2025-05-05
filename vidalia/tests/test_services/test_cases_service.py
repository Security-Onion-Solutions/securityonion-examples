import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import requests
import responses
from src.services.cases import CaseService

def test_get_cases_success(app, mock_responses):
    """Test successful retrieval of cases."""
    with app.app_context():
        # Create mock client
        client = MagicMock()
        client.base_url = "https://mock-so-api"
        client.session = requests.Session()
        client._get_bearer_header.return_value = {"Authorization": "Bearer test-token"}
        client._ensure_authenticated = MagicMock()
        
        # Sample cases data
        cases_data = {
            "events": [
                {
                    "id": "case1",
                    "payload": {
                        "so_kind": "case",
                        "so_case.id": "case1",
                        "so_case.title": "Test Case 1",
                        "so_case.description": "This is a test case",
                        "so_case.status": "open",
                        "so_case.severity": "high",
                        "so_case.priority": "1",
                        "so_case.tags": ["test", "important"],
                        "so_case.category": "security",
                        "so_case.createTime": "2023-01-01T00:00:00Z",
                        "so_case.completeTime": "2023-01-02T00:00:00Z",
                        "so_case.userId": "user1"
                    }
                },
                {
                    "id": "case2",
                    "payload": {
                        "so_kind": "case",
                        "so_case.id": "case2",
                        "so_case.title": "Test Case 2",
                        "so_case.description": "Another test case",
                        "so_case.status": "closed",
                        "so_case.severity": "medium",
                        "so_case.priority": "2",
                        "so_case.createTime": "2023-01-03T00:00:00Z",
                        "so_case.completeTime": "2023-01-04T00:00:00Z",
                        "so_case.userId": "user2"
                    }
                },
                {
                    "id": "not-a-case",
                    "payload": {
                        "so_kind": "comment",  # This should be skipped
                        "text": "This is a comment"
                    }
                }
            ]
        }
        
        # Mock the datetime to get consistent date ranges
        with patch('src.services.cases.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 15, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            thirty_days_ago = mock_now - timedelta(days=30)
            
            # Setup the expected date range in the required format
            date_range = f"{thirty_days_ago.strftime('%Y/%m/%d %I:%M:%S %p')} - {mock_now.strftime('%Y/%m/%d %I:%M:%S %p')}"
            
            # Mock the events endpoint for getting cases
            mock_responses.get(
                "https://mock-so-api/connect/events/",
                json=cases_data,
                status=200,
                match_querystring=False  # Don't strictly match query string
            )
            
            # Mock user service to return usernames
            with patch('src.services.users.UserService.get_user_name') as mock_get_user_name:
                mock_get_user_name.side_effect = lambda user_id: f"User {user_id}"
                
                service = CaseService(client)
                cases = service.get_cases()
                
                # Only 2 cases should be returned (skipping the comment)
                assert len(cases) == 2
                
                # Verify first case
                assert cases[0]['id'] == "case1"
                assert cases[0]['title'] == "Test Case 1"
                assert cases[0]['status'] == "open"
                assert cases[0]['severity'] == "high"
                assert cases[0]['priority'] == 1
                assert cases[0]['tags'] == ["test", "important"]
                assert cases[0]['category'] == "security"
                assert cases[0]['user'] == "User user1"
                
                # Verify second case
                assert cases[1]['id'] == "case2"
                assert cases[1]['title'] == "Test Case 2"
                assert cases[1]['status'] == "closed"
                assert cases[1]['priority'] == 2

def test_get_cases_empty(app, mock_responses):
    """Test handling of empty cases response."""
    with app.app_context():
        # Create mock client
        client = MagicMock()
        client.base_url = "https://mock-so-api"
        client.session = requests.Session()
        client._get_bearer_header.return_value = {"Authorization": "Bearer test-token"}
        client._ensure_authenticated = MagicMock()
        
        # Mock the datetime to get consistent date ranges
        with patch('src.services.cases.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 15, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            # Empty response
            mock_responses.get(
                "https://mock-so-api/connect/events/",
                json={"events": []},
                status=200,
                match_querystring=False
            )
            
            service = CaseService(client)
            cases = service.get_cases()
            
            # Should return empty list
            assert cases == []

def test_get_cases_api_error(app, mock_responses):
    """Test error handling when cases API request fails."""
    with app.app_context():
        # Create mock client
        client = MagicMock()
        client.base_url = "https://mock-so-api"
        client.session = requests.Session()
        client._get_bearer_header.return_value = {"Authorization": "Bearer test-token"}
        client._ensure_authenticated = MagicMock()
        
        # Mock the datetime to get consistent date ranges
        with patch('src.services.cases.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 15, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            # Mock error response
            mock_responses.get(
                "https://mock-so-api/connect/events/",
                json={"error": "API Error"},
                status=500,
                match_querystring=False
            )
            
            service = CaseService(client)
            
            # Should raise exception
            with pytest.raises(requests.exceptions.HTTPError):
                service.get_cases()

def test_get_case_success(app, mock_responses):
    """Test successful retrieval of a single case."""
    with app.app_context():
        # Create mock client
        client = MagicMock()
        client.base_url = "https://mock-so-api"
        client.session = requests.Session()
        client._get_bearer_header.return_value = {"Authorization": "Bearer test-token"}
        client._ensure_authenticated = MagicMock()
        
        # Mock case data
        case_data = {
            "id": "case1",
            "title": "Test Case",
            "description": "This is a test case",
            "status": "open",
            "severity": "high",
            "priority": "1",
            "tags": ["test", "important"],
            "category": "security",
            "createTime": "2023-01-01T00:00:00Z",
            "updateTime": "2023-01-02T00:00:00Z",
            "so_case.userId": "user1"
        }
        
        # Mock comments data
        comments_data = [
            {
                "id": "comment1",
                "description": "This is comment 1",
                "createTime": "2023-01-01T12:00:00Z",
                "userId": "user1"
            },
            {
                "id": "comment2",
                "description": "This is comment 2",
                "createTime": "2023-01-02T12:00:00Z",
                "userId": "user2"
            }
        ]
        
        # Mock endpoints
        mock_responses.get(
            "https://mock-so-api/connect/case/case1",
            json=case_data,
            status=200
        )
        
        mock_responses.get(
            "https://mock-so-api/connect/case/comments/case1",
            json=comments_data,
            status=200
        )
        
        # Mock user service
        with patch('src.services.users.UserService.get_user_name') as mock_get_user_name:
            mock_get_user_name.side_effect = lambda user_id: f"User {user_id}"
            
            service = CaseService(client)
            case = service.get_case("case1")
            
            # Verify case data
            assert case['id'] == "case1"
            assert case['title'] == "Test Case"
            assert case['status'] == "open"
            assert case['severity'] == "high"
            assert case['priority'] == 1
            assert case['tags'] == ["test", "important"]
            assert case['category'] == "security"
            assert case['user'] == "User user1"
            
            # Verify comments
            assert len(case['comments']) == 2
            # Comments should be sorted newest first
            assert case['comments'][0]['id'] == "comment2"
            assert case['comments'][0]['text'] == "This is comment 2"
            assert case['comments'][0]['user'] == "User user2"
            assert case['comments'][1]['id'] == "comment1"
            assert case['comments'][1]['text'] == "This is comment 1"
            assert case['comments'][1]['user'] == "User user1"

def test_get_case_not_found(app, mock_responses):
    """Test error handling when case is not found."""
    with app.app_context():
        # Create mock client
        client = MagicMock()
        client.base_url = "https://mock-so-api"
        client.session = requests.Session()
        client._get_bearer_header.return_value = {"Authorization": "Bearer test-token"}
        client._ensure_authenticated = MagicMock()
        
        # Mock 404 response
        mock_responses.get(
            "https://mock-so-api/connect/case/nonexistent",
            json={"error": "Case not found"},
            status=404
        )
        
        service = CaseService(client)
        
        # Should raise exception
        with pytest.raises(requests.exceptions.HTTPError):
            service.get_case("nonexistent")

def test_get_case_with_comments_error(app, mock_responses):
    """Test handling of comments API error when getting a case."""
    with app.app_context():
        # Create mock client
        client = MagicMock()
        client.base_url = "https://mock-so-api"
        client.session = requests.Session()
        client._get_bearer_header.return_value = {"Authorization": "Bearer test-token"}
        client._ensure_authenticated = MagicMock()
        
        # Mock case data
        case_data = {
            "id": "case1",
            "title": "Test Case",
            "description": "This is a test case",
            "status": "open",
            "severity": "high",
            "priority": "1",
            "tags": ["test", "important"],
            "category": "security",
            "createTime": "2023-01-01T00:00:00Z",
            "updateTime": "2023-01-02T00:00:00Z",
            "so_case.userId": "user1"
        }
        
        # Mock endpoints
        mock_responses.get(
            "https://mock-so-api/connect/case/case1",
            json=case_data,
            status=200
        )
        
        # Mock comments endpoint with error
        mock_responses.get(
            "https://mock-so-api/connect/case/comments/case1",
            json={"error": "Comments not available"},
            status=500
        )
        
        # Mock user service
        with patch('src.services.users.UserService.get_user_name') as mock_get_user_name:
            mock_get_user_name.side_effect = lambda user_id: f"User {user_id}"
            
            service = CaseService(client)
            case = service.get_case("case1")
            
            # Verify case data
            assert case['id'] == "case1"
            assert case['title'] == "Test Case"
            
            # Comments should be empty due to error
            assert case['comments'] == []

def test_transform_case_payload(app):
    """Test case payload transformation."""
    with app.app_context():
        # Create mock client
        client = MagicMock()
        # Mock user service
        with patch('src.services.users.UserService.get_user_name') as mock_get_user_name:
            mock_get_user_name.return_value = "Test User"
            
            service = CaseService(client)
            
            # Test with complete data
            complete_data = {
                "so_case.id": "case1",
                "so_case.title": "Test Case",
                "so_case.description": "Description",
                "so_case.status": "open",
                "so_case.severity": "critical",
                "so_case.priority": "3",
                "so_case.tags": ["tag1", "tag2"],
                "so_case.category": "incident",
                "so_case.createTime": "2023-01-01T00:00:00Z",
                "so_case.completeTime": "2023-01-02T00:00:00Z",
                "so_case.userId": "user123"
            }
            
            result = service._transform_case_payload(complete_data)
            
            assert result['id'] == "case1"
            assert result['title'] == "Test Case"
            assert result['description'] == "Description"
            assert result['status'] == "open"
            assert result['severity'] == "critical"
            assert result['priority'] == 3
            assert result['tags'] == ["tag1", "tag2"]
            assert result['category'] == "incident"
            assert result['created'] == "2023-01-01T00:00:00Z"
            assert result['updated'] == "2023-01-02T00:00:00Z"
            assert result['user'] == "Test User"
            assert result['user_id'] == "user123"
            
            # Test with minimal data and event_id
            minimal_data = {}
            result = service._transform_case_payload(minimal_data, "event123")
            
            assert result['id'] == "event123"
            assert result['title'] == "Untitled Case"
            assert result['description'] == ""
            assert result['status'] == "open"
            assert result['severity'] == "medium"
            assert result['priority'] == 0
            assert result['tags'] == []
            assert result['category'] == "general"
            assert result['user'] is None
            
            # Test with data that has no case ID and no event_id
            data_without_id = {
                "title": "Case Without ID"
            }
            result = service._transform_case_payload(data_without_id, None)
            
            assert result['id'] is None
            assert result['title'] == "Case Without ID"

def test_user_name_lookup_error(app, mock_responses):
    """Test handling of user lookup errors in transform_case_payload."""
    with app.app_context():
        # Create mock client
        client = MagicMock()
        client.base_url = "https://mock-so-api"
        client.session = requests.Session()
        client._get_bearer_header.return_value = {"Authorization": "Bearer test-token"}
        client._ensure_authenticated = MagicMock()
        
        # Test case data with user ID
        case_data = {
            "so_case.id": "case1",
            "so_case.title": "Test Case",
            "so_case.userId": "user1"
        }
        
        # Mock user service to throw an exception
        with patch('src.services.users.UserService.get_user_name') as mock_get_user_name:
            mock_get_user_name.side_effect = Exception("User lookup failed")
            
            service = CaseService(client)
            result = service._transform_case_payload(case_data)
            
            # Should still return case data but without user name
            assert result['id'] == "case1"
            assert result['title'] == "Test Case"
            assert result['user'] is None
            assert result['user_id'] == "user1"

def test_comment_user_lookup_error(app, mock_responses):
    """Test handling of user lookup errors in comments."""
    with app.app_context():
        # Create mock client
        client = MagicMock()
        client.base_url = "https://mock-so-api"
        client.session = requests.Session()
        client._get_bearer_header.return_value = {"Authorization": "Bearer test-token"}
        client._ensure_authenticated = MagicMock()
        
        # Mock case and comments data
        case_data = {
            "id": "case1",
            "title": "Test Case"
        }
        
        comments_data = [
            {
                "id": "comment1",
                "description": "This is a comment",
                "createTime": "2023-01-01T00:00:00Z",
                "userId": "user1"
            }
        ]
        
        # Mock endpoints
        mock_responses.get(
            "https://mock-so-api/connect/case/case1",
            json=case_data,
            status=200
        )
        
        mock_responses.get(
            "https://mock-so-api/connect/case/comments/case1",
            json=comments_data,
            status=200
        )
        
        # Mock user service to throw an exception for comment user lookup
        with patch('src.services.users.UserService.get_user_name') as mock_get_user_name:
            mock_get_user_name.side_effect = Exception("User lookup failed")
            
            service = CaseService(client)
            case = service.get_case("case1")
            
            # Should still return comment but with user ID as name
            assert len(case['comments']) == 1
            assert case['comments'][0]['id'] == "comment1"
            assert case['comments'][0]['text'] == "This is a comment"
            assert case['comments'][0]['user'] == "user1"  # Falls back to user ID