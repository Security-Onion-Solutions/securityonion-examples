import pytest
from flask import url_for
import json
import requests
from unittest.mock import patch

def test_list_cases_success(app, client, mock_responses, sample_case, api_client):
    """Test retrieving cases list successfully."""
    # Mock OAuth token endpoint
    mock_responses.post(
        "https://mock-so-api/oauth2/token",
        json={
            "access_token": "test-token",
            "token_type": "Bearer",
            "expires_in": 3600
        },
        status=200
    )
    
    # Mock cases endpoint with events endpoint as it's in the code
    mock_responses.get(
        "https://mock-so-api/connect/events/",
        json={
            "events": [
                {
                    "_id": "case-1",
                    "_source": {
                        "title": "Case 1",
                        "status": "open",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-02T00:00:00Z",
                        "owner": "user1"
                    }
                },
                {
                    "_id": "case-2",
                    "_source": {
                        "title": "Case 2",
                        "status": "closed",
                        "created_at": "2024-01-03T00:00:00Z",
                        "updated_at": "2024-01-04T00:00:00Z",
                        "owner": "user2"
                    }
                }
            ]
        },
        status=200
    )
    
    # Access cases list page
    response = client.get("/cases/")
    
    # Check response
    assert response.status_code == 200
    assert b"Case 1" in response.data
    assert b"Case 2" in response.data
    
    # Check sorting works (default is by updated date)
    assert response.data.index(b"Case 2") < response.data.index(b"Case 1")

def test_list_cases_with_sort(app, client, mock_responses, api_client):
    """Test cases list with different sorting options."""
    # Mock OAuth token endpoint
    mock_responses.post(
        "https://mock-so-api/oauth2/token",
        json={
            "access_token": "test-token",
            "token_type": "Bearer",
            "expires_in": 3600
        },
        status=200
    )
    
    # Mock cases endpoint with events endpoint as it's in the code
    mock_responses.get(
        "https://mock-so-api/connect/events/",
        json={
            "events": [
                {
                    "_id": "case-1",
                    "_source": {
                        "title": "A Case",
                        "status": "open",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-05T00:00:00Z",
                        "owner": "user1"
                    }
                },
                {
                    "_id": "case-2",
                    "_source": {
                        "title": "B Case",
                        "status": "closed",
                        "created_at": "2024-01-03T00:00:00Z",
                        "updated_at": "2024-01-04T00:00:00Z",
                        "owner": "user2"
                    }
                }
            ]
        },
        status=200
    )
    
    # Sort by title ascending
    response = client.get("/cases/?sort=title&dir=asc")
    
    # Check response
    assert response.status_code == 200
    assert response.data.index(b"A Case") < response.data.index(b"B Case")
    
    # Sort by created date descending
    response = client.get("/cases/?sort=created&dir=desc")
    
    # Check response
    assert response.status_code == 200
    assert response.data.index(b"B Case") < response.data.index(b"A Case")

def test_list_cases_simulated_error(app, client, mock_responses, api_client):
    """Test simulated error in cases list."""
    # Mock OAuth token endpoint
    mock_responses.post(
        "https://mock-so-api/oauth2/token",
        json={
            "access_token": "test-token",
            "token_type": "Bearer",
            "expires_in": 3600
        },
        status=200
    )
    
    # Access cases list page with error parameter
    response = client.get("/cases/?error=true")
    
    # Check response shows error message but renders page
    assert response.status_code == 200
    assert b"Error retrieving cases" in response.data
    assert b"No cases found" in response.data

def test_list_cases_api_error(app, client, mock_responses, api_client):
    """Test error handling when cases API request fails."""
    # Mock OAuth token endpoint
    mock_responses.post(
        "https://mock-so-api/oauth2/token",
        json={
            "access_token": "test-token",
            "token_type": "Bearer",
            "expires_in": 3600
        },
        status=200
    )
    
    # Mock cases endpoint with error
    mock_responses.get(
        "https://mock-so-api/connect/events/",
        json={"error": "API Error"},
        status=500
    )
    
    # Access cases list page
    response = client.get("/cases/")
    
    # Check response
    assert response.status_code == 200
    assert b"Error retrieving cases" in response.data
    assert b"No cases found" in response.data

def test_list_cases_method_not_allowed(app, client, mock_responses, api_client):
    """Test error handling when cases API returns 405 (not configured)."""
    # Mock OAuth token endpoint
    mock_responses.post(
        "https://mock-so-api/oauth2/token",
        json={
            "access_token": "test-token",
            "token_type": "Bearer",
            "expires_in": 3600
        },
        status=200
    )
    
    # Mock cases endpoint with method not allowed
    mock_responses.get(
        "https://mock-so-api/connect/events/",
        json={"error": "Method not allowed"},
        status=405
    )
    
    # Access cases list page
    response = client.get("/cases/")
    
    # Check response
    assert response.status_code == 200
    assert b"Case management is not configured" in response.data
    assert b"No cases found" in response.data

def test_list_cases_unexpected_exception(app, client, mock_responses, api_client):
    """Test error handling for unexpected exceptions."""
    # Mock OAuth token endpoint
    mock_responses.post(
        "https://mock-so-api/oauth2/token",
        json={
            "access_token": "test-token",
            "token_type": "Bearer",
            "expires_in": 3600
        },
        status=200
    )
    
    # Mock cases endpoint but raise an unexpected exception when accessed
    with patch('src.services.cases.CaseService.get_cases') as mock_get_cases:
        mock_get_cases.side_effect = Exception("Unexpected error")
        
        # Access cases list page
        response = client.get("/cases/")
        
        # Check response
        assert response.status_code == 200
        assert b"Error retrieving cases" in response.data
        assert b"No cases found" in response.data

def test_view_case_success(app, client, mock_responses, api_client):
    """Test viewing a specific case successfully."""
    # Mock OAuth token endpoint
    mock_responses.post(
        "https://mock-so-api/oauth2/token",
        json={
            "access_token": "test-token",
            "token_type": "Bearer",
            "expires_in": 3600
        },
        status=200
    )
    
    # Mock specific case endpoint with the correct endpoint from code
    test_case = {
        "id": "case-1",
        "title": "Test Case",
        "description": "This is a test case description",
        "status": "open",
        "create_time": "2024-01-01T00:00:00Z",
        "update_time": "2024-01-02T00:00:00Z", 
        "owner": "user1",
        "assignee": "user2",
        "priority": "high",
        "severity": "critical",
        "tlp": "amber",
        "tags": ["test", "important"],
        "events": []
    }
    
    mock_responses.get(
        f"https://mock-so-api/connect/case/case-1",
        json=test_case,
        status=200
    )
    
    # Mock the comments endpoint 
    mock_responses.get(
        f"https://mock-so-api/connect/case/comments/case-1",
        json=[
            {
                "id": "comment-1",
                "description": "First comment",
                "createTime": "2024-01-01T01:00:00Z",
                "userId": "user1",
                "timeSpent": 0.5
            }
        ],
        status=200
    )
    
    # Mock users endpoint for name resolution
    mock_responses.get(
        "https://mock-so-api/connect/users",
        json=[
            {"username": "user1", "firstname": "User", "lastname": "One"},
            {"username": "user2", "firstname": "User", "lastname": "Two"}
        ],
        status=200
    )
    
    # Access case detail page
    response = client.get("/cases/case-1")
    
    # Check response
    assert response.status_code == 200
    assert b"Test Case" in response.data
    assert b"test case description" in response.data
    assert b"First comment" in response.data
    assert b"user1" in response.data
    assert b"test" in response.data
    assert b"important" in response.data

def test_view_case_not_found(app, client, mock_responses, api_client):
    """Test viewing a case that does not exist."""
    # Mock OAuth token endpoint
    mock_responses.post(
        "https://mock-so-api/oauth2/token",
        json={
            "access_token": "test-token",
            "token_type": "Bearer",
            "expires_in": 3600
        },
        status=200
    )
    
    # Mock specific case endpoint with 404 error using correct endpoint from code
    mock_responses.get(
        "https://mock-so-api/connect/case/nonexistent-case",
        json={"error": "Case not found"},
        status=404
    )
    
    # Access nonexistent case
    response = client.get("/cases/nonexistent-case", follow_redirects=True)
    
    # Check redirect to cases list with error message
    assert b"Error retrieving case" in response.data
    assert response.request.path == "/cases/"

def test_view_case_api_error(app, client, mock_responses, api_client):
    """Test error handling when case retrieval API request fails."""
    # Mock OAuth token endpoint
    mock_responses.post(
        "https://mock-so-api/oauth2/token",
        json={
            "access_token": "test-token",
            "token_type": "Bearer",
            "expires_in": 3600
        },
        status=200
    )
    
    # Mock specific case endpoint with server error using correct endpoint from code
    mock_responses.get(
        "https://mock-so-api/connect/case/case-1",
        json={"error": "Server error"},
        status=500
    )
    
    # Access case with API error
    response = client.get("/cases/case-1", follow_redirects=True)
    
    # Check redirect to cases list with error message
    assert b"Error retrieving case" in response.data
    assert response.request.path == "/cases/"

def test_view_case_not_configured(app, client, mock_responses, api_client):
    """Test error handling when case API returns 405 (not configured)."""
    # Mock OAuth token endpoint
    mock_responses.post(
        "https://mock-so-api/oauth2/token",
        json={
            "access_token": "test-token",
            "token_type": "Bearer",
            "expires_in": 3600
        },
        status=200
    )
    
    # Mock specific case endpoint with method not allowed using correct endpoint from code
    mock_responses.get(
        "https://mock-so-api/connect/case/case-1",
        json={"error": "Method not allowed"},
        status=405
    )
    
    # Access case with API not configured
    response = client.get("/cases/case-1", follow_redirects=True)
    
    # Check redirect to cases list with specific error message
    assert b"Case management is not configured" in response.data
    assert response.request.path == "/cases/"

def test_view_case_unexpected_exception(app, client, mock_responses, api_client):
    """Test error handling for unexpected exceptions in case view."""
    # Mock OAuth token endpoint
    mock_responses.post(
        "https://mock-so-api/oauth2/token",
        json={
            "access_token": "test-token",
            "token_type": "Bearer",
            "expires_in": 3600
        },
        status=200
    )
    
    # Use unittest.mock to raise an unexpected exception
    with patch('src.services.cases.CaseService.get_case') as mock_get_case:
        mock_get_case.side_effect = Exception("Unexpected error")
        
        # Access case with unexpected error
        response = client.get("/cases/case-1", follow_redirects=True)
        
        # Check redirect to cases list with error message
        assert b"Error retrieving case" in response.data
        assert response.request.path == "/cases/"