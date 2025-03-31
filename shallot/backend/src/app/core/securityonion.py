from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import httpx
import json
import base64
from ..services.settings import get_setting

class SecurityOnionClient:
    """Client for interacting with Security Onion API."""
    
    def __init__(self):
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._connected: bool = False
        self._last_error: Optional[str] = None

    async def initialize(self) -> None:
        """Initialize the client with settings from the database."""
        from sqlalchemy.ext.asyncio import AsyncSession
        from ..database import AsyncSessionLocal
        
        print("\nInitializing Security Onion client...")
        try:
            async with AsyncSessionLocal() as db:
                print("Loading Security Onion settings from database...")
                so_settings = await get_setting(db, "SECURITY_ONION")
                if not so_settings:
                    self._connected = False
                    self._last_error = "Security Onion settings not found"
                    print(f"Initialization failed: {self._last_error}")
                    return

                try:
                    settings = json.loads(so_settings.value)
                    print("Checking required settings...")
                    missing = []
                    if not settings.get("apiUrl"):
                        missing.append("apiUrl")
                    if not settings.get("clientId"):
                        missing.append("clientId")
                    if not settings.get("clientSecret"):
                        missing.append("clientSecret")
                    
                    if missing:
                        self._connected = False
                        self._last_error = f"Missing required settings: {', '.join(missing)}"
                        print(f"Initialization failed: {self._last_error}")
                        return

                    print("All required settings found")
                    
                    # Validate and format API URL
                    api_url = settings["apiUrl"].strip()
                    
                    # Add protocol if missing
                    if not (api_url.startswith('http://') or api_url.startswith('https://')):
                        api_url = f"https://{api_url}"  # Default to https if no protocol specified
                    
                    # Fix common URL issues
                    while '//' in api_url[8:]:  # Look for double slashes after http(s)://
                        api_url = api_url.replace('//', '/')
                    
                    # Ensure proper URL format
                    if not api_url.endswith('/'):
                        api_url += '/'
                    
                    self._base_url = api_url
                    print(f"Formatted API URL: {api_url}")
                    self._client_id = settings["clientId"]
                    self._client_secret = settings["clientSecret"]
                    self._verify_ssl = settings.get("verifySSL", True)
                    
                    # Log settings (without sensitive data)
                    print(f"Loaded settings:")
                    print(f"  API URL: {self._base_url}")
                    print(f"  Client ID: {self._client_id}")
                    print(f"  Client Secret: {'*' * len(self._client_secret)}")
                    print(f"  Verify SSL: {self._verify_ssl}")
                    print(f"  Protocol: {'HTTPS' if self._base_url.startswith('https://') else 'HTTP'}")
                except json.JSONDecodeError as e:
                    self._connected = False
                    self._last_error = f"Invalid settings format: {str(e)}"
                    print(f"Initialization failed: {self._last_error}")
                    return
                
                print(f"Using base URL: {self._base_url}")
                print(f"SSL verification: {'enabled' if self._verify_ssl else 'disabled'}")
                
                # Initialize HTTP client with properly formatted base URL
                print("Initializing HTTP client...")
                base_url = self._base_url.rstrip('/') + '/'
                print(f"Using formatted base URL: {base_url}")
                self._client = httpx.AsyncClient(
                    base_url=base_url,
                    verify=self._verify_ssl,
                    follow_redirects=True
                )
                
                # Initial connection test
                print("Running initial connection test...")
                await self.test_connection()
                
        except Exception as e:
            self._connected = False
            self._last_error = f"Initialization error: {str(e)}"
            print(f"Failed to initialize Security Onion client: {self._last_error}")

    async def test_connection(self) -> bool:
        """Test the connection to the Security Onion API.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            print("Testing Security Onion connection...")
            
            if not self._client:
                self._last_error = "Client not initialized"
                print(f"Connection test failed: {self._last_error}")
                return False
                
            # Try to get a token first
            print("Attempting to get access token...")
            if not await self._ensure_token():
                self._connected = False
                print(f"Failed to get token: {self._last_error}")
                return False
                
            # Test API endpoint
            print("Testing API health endpoint...")
            # Format URL consistently
            base_url = self._base_url.rstrip('/') + '/'
            health_paths = ['api/health', 'health']  # Try both paths
            
            for path in health_paths:
                try:
                    health_url = f"{base_url}{path}"
                    print(f"\nTrying health endpoint: {health_url}")
            
                    response = await self._client.get(
                        health_url,
                        headers=self._get_headers(),
                        follow_redirects=True,
                        timeout=10.0
                    )
                    print(f"Health check response: {response.status_code}")
                    print(f"Health check response headers: {dict(response.headers)}")
                    
                    if response.status_code == 200:
                        self._connected = True
                        self._last_error = None
                        return True
                    
                    # Log response content for debugging
                    response_text = response.text
                    content_type = response.headers.get('content-type', '')
                    print(f"Health check response content: {response_text}")
                    print(f"Health check content type: {content_type}")
                    
                    try:
                        if 'json' in content_type.lower():
                            error_data = response.json()
                            self._last_error = error_data.get('detail') or error_data.get('message') or "Health check failed"
                        else:
                            # Handle non-JSON responses
                            self._last_error = f"Unexpected response type ({content_type}): {response_text[:100]}"
                    except Exception as e:
                        print(f"Failed to parse health check error response: {str(e)}")
                        self._last_error = f"Health check failed with status {response.status_code}"
                    
                except Exception as e:
                    print(f"Error trying health endpoint {path}: {str(e)}")
                    self._last_error = str(e)
                    continue
            
            self._connected = False
            
            print(f"Connection test {'succeeded' if self._connected else 'failed'}: {self._last_error or 'No errors'}")
            return self._connected
            
        except Exception as e:
            self._connected = False
            self._last_error = str(e)
            print(f"Connection test error: {self._last_error}")
            return False

    async def _ensure_token(self) -> bool:
        """Ensure we have a valid access token.
        
        Returns:
            bool: True if valid token available/obtained, False otherwise
        """
        print("Checking token status...")
        
        # Check if token is still valid
        if self._access_token and self._token_expires:
            if datetime.utcnow() < self._token_expires - timedelta(minutes=5):
                print("Using existing valid token")
                return True
            else:
                print("Token expired, requesting new one")
        else:
            print("No token exists, requesting new one")

        # Get new token
        try:
            # Try different token endpoint paths
            base_url = self._base_url.rstrip('/') + '/'
            token_paths = ['oauth2/token', 'api/token', 'token']
            last_error = None
            
            # Prepare auth header
            auth_str = f"{self._client_id}:{self._client_secret}"
            auth_bytes = auth_str.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            # Prepare request data
            request_data = {
                "grant_type": "client_credentials"
            }
            
            for path in token_paths:
                try:
                    token_url = f"{base_url}{path}"
                    print(f"\nTrying token endpoint: {token_url}")
                    print(f"Token request data: {request_data}")
                    
                    # Make request with full URL to avoid redirect
                    response = await self._client.post(
                        token_url,
                        data=request_data,
                        headers={
                            "Content-Type": "application/x-www-form-urlencoded",
                            "Authorization": f"Basic {auth_b64}"
                        },
                        follow_redirects=True,
                        timeout=10.0
                    )
                    print(f"Token response status: {response.status_code}")
                    print(f"Token response headers: {dict(response.headers)}")
                    
                    # Log raw response details
                    response_text = response.text
                    content_type = response.headers.get('content-type', '')
                    print(f"Token response content (raw): '{response_text}'")
                    print(f"Token response content length: {len(response_text)}")
                    print(f"Token response content type: {content_type}")
                    
                    if response.status_code == 200:
                        try:
                            if 'json' in content_type.lower():
                                data = response.json()
                                if "access_token" not in data:
                                    last_error = "Response missing access_token"
                                    continue
                                if "expires_in" not in data:
                                    last_error = "Response missing expires_in"
                                    continue
                                
                                self._access_token = data["access_token"]
                                # Set expiration with 5 minute buffer
                                expires_in = int(data["expires_in"]) - 300
                                self._token_expires = datetime.utcnow() + timedelta(seconds=expires_in)
                                print("Successfully obtained new token")
                                print(f"[DEBUG] New token: {self._access_token}")
                                return True
                            else:
                                last_error = f"Unexpected response type ({content_type})"
                                continue
                        except Exception as e:
                            print(f"Failed to parse token success response: {str(e)}")
                            last_error = "Invalid JSON response from server"
                            continue
                    else:
                        try:
                            if 'json' in content_type.lower():
                                error_data = response.json()
                                last_error = error_data.get('detail') or error_data.get('message') or "Token request failed"
                            else:
                                # Handle non-JSON responses
                                last_error = f"Unexpected response type ({content_type}): {response_text[:100]}"
                        except Exception as e:
                            print(f"Failed to parse token error response: {str(e)}")
                            last_error = f"Token request failed with status {response.status_code}"
                except Exception as e:
                    print(f"Error trying {path}: {str(e)}")
                    last_error = str(e)
                    continue
            
            self._last_error = f"Token request failed on all endpoints. Last error: {last_error}"
            print(f"Token request failed: {self._last_error}")
            return False
            
        except Exception as e:
            self._last_error = f"Token request error: {str(e)}"
            print(f"Token request error: {self._last_error}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json"
        }
        print(f"[DEBUG] Using headers: {headers}")
        return headers

    def get_status(self) -> Dict[str, Any]:
        """Get current connection status.
        
        Returns:
            Dict containing connection status and any error message
        """
        try:
            return {
                "connected": bool(self._connected),  # Ensure boolean
                "error": str(self._last_error) if self._last_error else None  # Ensure string or None
            }
        except Exception as e:
            print(f"Error getting status: {str(e)}")
            return {
                "connected": False,
                "error": f"Status error: {str(e)}"
            }

    async def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get event details by ID.
        
        Args:
            event_id: The ID of the event to retrieve
            
        Returns:
            Dict containing event details or None if not found
        """
        try:
            if not await self._ensure_token():
                return None

            response = await self._client.get(
                f"connect/events/?query=_id:{event_id}",
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("events") and len(data["events"]) > 0:
                    return data["events"][0]
            return None
            
        except Exception as e:
            self._last_error = f"Failed to get event: {str(e)}"
            return None

    async def create_case(self, case_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new case.
        
        Args:
            case_data: Dictionary containing case details
            
        Returns:
            Dict containing created case details or None if creation failed
        """
        try:
            if not await self._ensure_token():
                return None

            response = await self._client.post(
                "connect/case/",
                headers=self._get_headers(),
                json=case_data
            )
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            self._last_error = f"Failed to create case: {str(e)}"
            return None

    async def search_events(self, query: str, time_range: str = "24h", limit: int = 100) -> List[Dict[str, Any]]:
        """Search for events matching query.
        
        Args:
            query: The search query
            time_range: Time range to search (default: "24h")
            limit: Maximum number of events to return (default: 100)
            
        Returns:
            List of matching events
        """
        try:
            if not await self._ensure_token():
                return []

            # Calculate date range
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)
            date_format = "%Y/%m/%d %I:%M:%S %p"
            date_range = f"{start_time.strftime(date_format)} - {end_time.strftime(date_format)}"

            response = await self._client.get(
                "connect/events/",
                headers=self._get_headers(),
                params={
                    "query": query,
                    "range": date_range,
                    "format": date_format,
                    "zone": "UTC",
                    "metricLimit": 10,
                    "eventLimit": limit
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("events", [])
            return []
            
        except Exception as e:
            self._last_error = f"Failed to search events: {str(e)}"
            return []

    async def add_event_to_case(self, case_id: str, event_fields: Dict[str, Any]) -> bool:
        """Add an event to a case.

        Args:
            case_id: The ID of the case
            event_fields: The event fields to add

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not await self._ensure_token():
                return False

            # First attempt
            response = await self._client.post(
                "connect/case/events",
                headers=self._get_headers(),
                json={
                    "caseId": case_id,
                    "fields": event_fields
                }
            )

            # If unauthorized, try refreshing token and retry once
            # if response.status_code == 401:
            #     print("[DEBUG] Got 401, attempting token refresh")
            #     if await self._ensure_token():
            #         print("[DEBUG] Token refreshed, retrying request")
            #         response = await self._client.post(
            #             "connect/case/events",
            #             headers=self._get_headers(),  # Get fresh headers with new token
            #             json={
            #                 "caseId": case_id,
            #                 "fields": event_fields
            #             }
            #         )

            return response.status_code in [200, 202]
            
        except Exception as e:
            self._last_error = f"Failed to add event to case: {str(e)}"
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()

# Global client instance
client = SecurityOnionClient()
