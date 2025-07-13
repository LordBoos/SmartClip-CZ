"""
Twitch API Integration for SmartClip CZ
Handles Twitch clip creation and API interactions
"""

import requests
import json
import logging
import time
from typing import Optional, Dict, List
from datetime import datetime, timedelta

class TwitchAPI:
    """Twitch API client for clip creation"""
    
    def __init__(self, client_id: str, oauth_token: str, broadcaster_id: str, client_secret: str = "", refresh_token: str = ""):
        self.client_id = client_id
        self.oauth_token = oauth_token
        self.broadcaster_id = broadcaster_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token

        # API endpoints
        self.base_url = "https://api.twitch.tv/helix"
        self.clips_endpoint = f"{self.base_url}/clips"
        self.token_endpoint = "https://id.twitch.tv/oauth2/token"

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum 1 second between requests

        # Token management
        self.token_expires_at = None
        self.token_refresh_callback = None  # Callback to save new tokens

        # Statistics
        self.clips_created = 0
        self.api_errors = 0
        self.last_clip_time = None

        self.logger = logging.getLogger('SmartClipCZ.TwitchAPI')

        # Log initialization details
        self.logger.info("=== TWITCH API INITIALIZATION ===")
        self.logger.info(f"Client ID: {'[PRESENT]' if self.client_id else '[MISSING]'}")
        self.logger.info(f"OAuth token: {'[PRESENT]' if self.oauth_token else '[MISSING]'}")
        self.logger.info(f"Broadcaster ID: {'[PRESENT]' if self.broadcaster_id else '[MISSING]'}")
        self.logger.info(f"Client secret: {'[PRESENT]' if self.client_secret else '[MISSING]'}")
        self.logger.info(f"Refresh token: {'[PRESENT]' if self.refresh_token else '[MISSING]'}")

        # Check token refresh capability
        can_refresh = bool(self.client_secret and self.refresh_token)
        self.logger.info(f"Token refresh capability: {'ENABLED' if can_refresh else 'DISABLED'}")
        if not can_refresh:
            if not self.client_secret:
                self.logger.warning("  Missing client_secret for token refresh")
            if not self.refresh_token:
                self.logger.warning("  Missing refresh_token for token refresh")

        # Validate configuration
        self._is_configured = self._validate_config()

        if self._is_configured:
            self.logger.info("Twitch API configured successfully")
        else:
            self.logger.warning("Twitch API not properly configured")

            # If validation failed but we have refresh capability, try to refresh token
            if can_refresh and self.oauth_token:
                self.logger.info("Attempting token refresh during initialization...")
                if self._refresh_access_token():
                    self.logger.info("Token refreshed during initialization, re-validating...")
                    self._is_configured = self._validate_config()
                    if self._is_configured:
                        self.logger.info("Twitch API configured successfully after token refresh")
                    else:
                        self.logger.error("API validation still failed after token refresh")
                else:
                    self.logger.error("Token refresh failed during initialization")

        self.logger.info("=== TWITCH API INITIALIZATION COMPLETE ===")

    def set_token_refresh_callback(self, callback):
        """Set callback function to save new tokens when refreshed"""
        self.token_refresh_callback = callback
        self.logger.info(f"Token refresh callback set: {'OK' if callback else 'NOK'}")
    
    def _validate_config(self) -> bool:
        """Validate Twitch API configuration"""
        try:
            if not self.client_id or not self.oauth_token or not self.broadcaster_id:
                self.logger.warning("Missing Twitch API credentials")
                return False
            
            # Test API connection
            return self._test_api_connection()
            
        except Exception as e:
            self.logger.error(f"Error validating Twitch API config: {e}")
            return False
    
    def _test_api_connection(self) -> bool:
        """Test Twitch API connection"""
        try:
            self.logger.debug("--- Testing API connection ---")

            headers = {
                "Client-ID": self.client_id,
                "Authorization": f"Bearer {self.oauth_token}",
                "Content-Type": "application/json"
            }

            # Test with a simple API call (get user info)
            url = f"{self.base_url}/users"
            params = {"id": self.broadcaster_id}

            self.logger.debug(f"API test URL: {url}")
            self.logger.debug(f"API test params: {params}")
            self.logger.debug(f"Client-ID: {self.client_id[:8]}..." if self.client_id else "Client-ID: [MISSING]")
            self.logger.debug(f"OAuth token length: {len(self.oauth_token) if self.oauth_token else 0}")

            response = requests.get(url, headers=headers, params=params, timeout=10)

            self.logger.debug(f"API test response status: {response.status_code}")
            self.logger.debug(f"API test response headers: {dict(response.headers)}")

            if response.status_code == 200:
                data = response.json()
                self.logger.debug(f"API test response data keys: {list(data.keys())}")
                if data.get("data"):
                    user_info = data["data"][0]
                    display_name = user_info.get('display_name', 'Unknown')
                    self.logger.info(f"Connected to Twitch API for user: {display_name}")
                    self.logger.debug(f"User info: {user_info}")
                    return True
                else:
                    self.logger.warning("Twitch API test: No user data returned")
                    self.logger.debug(f"Full response: {data}")
                    return False
            elif response.status_code == 401:
                self.logger.error("Twitch API authentication failed - OAuth token is invalid/expired")
                try:
                    error_data = response.json()
                    self.logger.error(f"Auth error details: {error_data}")
                except:
                    self.logger.error(f"Auth error response: {response.text}")
                return False
            else:
                self.logger.error(f"Twitch API test failed: {response.status_code}")
                self.logger.error(f"Response text: {response.text}")
                try:
                    error_data = response.json()
                    self.logger.error(f"Error data: {error_data}")
                except:
                    pass
                return False
                
        except requests.exceptions.Timeout:
            self.logger.error("Twitch API test timed out")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Twitch API test request failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Twitch API test error: {e}")
            return False
    
    def create_clip(self, title: str, has_delay: bool = True, duration: int = 30) -> Optional[str]:
        """Create a Twitch clip with specified duration"""
        try:
            self.logger.info(f"=== CLIP CREATION REQUESTED: {title} ===")

            if not self._is_configured:
                self.logger.warning("Cannot create clip - Twitch API not configured")
                return None

            # CRITICAL: Validate token before EVERY clip creation attempt
            self.logger.info("Validating OAuth token before clip creation...")
            token_valid = self._ensure_valid_token()
            if not token_valid:
                self.logger.error("Cannot create clip - token validation failed")
                self.logger.error("This usually means the token is expired and refresh failed")
                return None
            self.logger.info("Token validation successful, proceeding with clip creation")
            
            # Rate limiting
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            
            if time_since_last < self.min_request_interval:
                sleep_time = self.min_request_interval - time_since_last
                time.sleep(sleep_time)
            
            # Prepare request
            headers = {
                "Client-ID": self.client_id,
                "Authorization": f"Bearer {self.oauth_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "broadcaster_id": self.broadcaster_id,
                "has_delay": has_delay
            }

            # Log the requested duration (Twitch creates 60s clips by default)
            self.logger.info(f"Creating clip with requested duration: {duration}s (Note: Twitch creates 60s clips, editing to {duration}s would require additional API call)")
            
            # Make API request
            self.last_request_time = time.time()
            response = requests.post(self.clips_endpoint, headers=headers, json=data, timeout=15)
            
            if response.status_code == 202:  # Accepted
                clip_data = response.json()
                
                if clip_data.get("data"):
                    clip_info = clip_data["data"][0]
                    clip_id = clip_info.get("id")
                    edit_url = clip_info.get("edit_url")
                    
                    # Update statistics
                    self.clips_created += 1
                    self.last_clip_time = datetime.now()
                    
                    # Note: Twitch API doesn't support setting custom titles during clip creation
                    # Clips will use the current stream title automatically
                    self.logger.info(f"Clip created successfully: {clip_id}")
                    self.logger.info(f"Intended title: {title}")
                    self.logger.info(f"Actual title: Will use current stream title")
                    self.logger.info(f"Edit URL: {edit_url}")
                    
                    return clip_id
                else:
                    self.logger.error("Clip creation response missing data")
                    self.api_errors += 1
                    return None
                    
            elif response.status_code == 401:
                self.logger.warning("Clip creation failed - authentication error (401)")
                self.logger.info("Attempting automatic token refresh and retry...")

                # Try to refresh token and retry once
                refresh_success = self._refresh_access_token()
                if refresh_success:
                    self.logger.info("Token refreshed successfully, retrying clip creation")

                    # Update headers with new token
                    headers["Authorization"] = f"Bearer {self.oauth_token}"
                    self.logger.debug(f"Updated authorization header with new token (length: {len(self.oauth_token)})")

                    # Retry the request
                    self.logger.info("Making retry clip creation request...")
                    retry_response = requests.post(self.clips_endpoint, headers=headers, json=data, timeout=15)
                    self.logger.info(f"Retry response status: {retry_response.status_code}")

                    if retry_response.status_code == 202:
                        self.logger.info("Retry clip creation successful!")
                        clip_data = retry_response.json()
                        if clip_data.get("data"):
                            clip_info = clip_data["data"][0]
                            clip_id = clip_info.get("id")
                            edit_url = clip_info.get("edit_url")

                            self.clips_created += 1
                            self.last_clip_time = datetime.now()

                            self.logger.info(f"Clip created successfully after token refresh: {clip_id}")
                            self.logger.info(f"Intended title: {title}")
                            self.logger.info(f"Edit URL: {edit_url}")

                            return clip_id
                        else:
                            self.logger.error("Retry clip creation response missing data")
                            self.logger.error(f"Retry response: {clip_data}")
                    else:
                        self.logger.error(f"Retry clip creation failed: {retry_response.status_code}")
                        self.logger.error(f"Retry response text: {retry_response.text}")
                        if retry_response.status_code == 401:
                            self.logger.error("  Still getting 401 after token refresh - token may be invalid")
                        elif retry_response.status_code == 404:
                            self.logger.error("  Broadcaster not found or not live")
                        elif retry_response.status_code == 403:
                            self.logger.error("  Insufficient permissions for clip creation")
                else:
                    self.logger.error("Token refresh failed, cannot retry clip creation")
                    self.logger.error("  Check refresh token and client secret configuration")

                self.api_errors += 1
                return None
            elif response.status_code == 403:
                self.logger.error("Clip creation failed - insufficient permissions")
                self.api_errors += 1
                return None
            elif response.status_code == 404:
                self.logger.error("Clip creation failed - broadcaster not found or not live")
                self.api_errors += 1
                return None
            else:
                self.logger.error(f"Clip creation failed: {response.status_code} - {response.text}")
                self.api_errors += 1
                return None
                
        except requests.exceptions.Timeout:
            self.logger.error("Clip creation timed out")
            self.api_errors += 1
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Clip creation request failed: {e}")
            self.api_errors += 1
            return None
        except Exception as e:
            self.logger.error(f"Error creating clip: {e}")
            self.api_errors += 1
            return None
    

    def get_stream_info(self) -> Optional[Dict]:
        """Get current stream information including title"""
        try:
            if not self.is_configured:
                return None

            headers = {
                "Client-ID": self.client_id,
                "Authorization": f"Bearer {self.oauth_token}"
            }

            params = {
                "user_id": self.broadcaster_id
            }

            response = requests.get("https://api.twitch.tv/helix/streams", headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                streams = data.get("data", [])
                if streams:
                    return streams[0]  # Return first (current) stream
                else:
                    # Not currently streaming, try to get channel info for title
                    return self._get_channel_info()
            else:
                self.logger.error(f"Failed to get stream info: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"Error getting stream info: {e}")
            return None

    def _get_channel_info(self) -> Optional[Dict]:
        """Get channel information when not streaming"""
        try:
            headers = {
                "Client-ID": self.client_id,
                "Authorization": f"Bearer {self.oauth_token}"
            }

            params = {
                "broadcaster_id": self.broadcaster_id
            }

            response = requests.get("https://api.twitch.tv/helix/channels", headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                channels = data.get("data", [])
                if channels:
                    return channels[0]

            return None

        except Exception as e:
            self.logger.error(f"Error getting channel info: {e}")
            return None

    def get_recent_clips(self, count: int = 10) -> List[Dict]:
        """Get recent clips for the broadcaster"""
        try:
            if not self.is_configured:
                return []

            headers = {
                "Client-ID": self.client_id,
                "Authorization": f"Bearer {self.oauth_token}"
            }

            params = {
                "broadcaster_id": self.broadcaster_id,
                "first": min(count, 100)  # API limit
            }

            response = requests.get(self.clips_endpoint, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            else:
                self.logger.error(f"Failed to get recent clips: {response.status_code}")
                return []

        except Exception as e:
            self.logger.error(f"Error getting recent clips: {e}")
            return []
    
    def is_broadcaster_live(self) -> bool:
        """Check if broadcaster is currently live"""
        try:
            if not self._is_configured:
                return False
            
            headers = {
                "Client-ID": self.client_id,
                "Authorization": f"Bearer {self.oauth_token}"
            }
            
            params = {
                "user_id": self.broadcaster_id
            }
            
            url = f"{self.base_url}/streams"
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                streams = data.get("data", [])
                return len(streams) > 0
            else:
                self.logger.error(f"Failed to check stream status: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error checking stream status: {e}")
            return False
    
    def get_stream_info(self) -> Optional[Dict]:
        """Get current stream information"""
        try:
            if not self.is_configured:
                return None
            
            headers = {
                "Client-ID": self.client_id,
                "Authorization": f"Bearer {self.oauth_token}"
            }
            
            params = {
                "user_id": self.broadcaster_id
            }
            
            url = f"{self.base_url}/streams"
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                streams = data.get("data", [])
                if streams:
                    return streams[0]
                else:
                    return None
            else:
                self.logger.error(f"Failed to get stream info: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting stream info: {e}")
            return None



    def _is_token_expired(self) -> bool:
        """Check if the current token is expired or about to expire"""
        self.logger.debug("--- Checking token expiration ---")

        if not self.token_expires_at:
            # If we don't have expiration time, try to validate token with API call
            self.logger.debug("No token expiration time set, testing token with API call")
            api_test_result = self._test_api_connection()
            if api_test_result:
                self.logger.debug("API test successful - token appears valid")
                return False
            else:
                self.logger.debug("API test failed - token appears invalid/expired")
                return True

        # Consider token expired if it expires within the next 5 minutes
        buffer_time = 300  # 5 minutes in seconds
        current_time = time.time()
        time_until_expiry = self.token_expires_at - current_time

        current_dt = datetime.fromtimestamp(current_time)
        expiry_dt = datetime.fromtimestamp(self.token_expires_at)

        self.logger.debug(f"Current time: {current_dt}")
        self.logger.debug(f"Token expires: {expiry_dt}")
        self.logger.debug(f"Time until expiry: {time_until_expiry:.0f} seconds")
        self.logger.debug(f"Buffer time: {buffer_time} seconds")

        is_expired = time_until_expiry <= buffer_time
        if is_expired:
            if time_until_expiry <= 0:
                self.logger.info(f"Token is EXPIRED (expired {abs(time_until_expiry):.0f} seconds ago)")
            else:
                self.logger.info(f"Token expires soon ({time_until_expiry:.0f} seconds, within {buffer_time}s buffer)")
        else:
            self.logger.debug(f"Token is valid (expires in {time_until_expiry:.0f} seconds)")

        return is_expired

    def _refresh_access_token(self) -> bool:
        """Refresh the OAuth access token using the refresh token"""
        try:
            self.logger.info("=== OAUTH TOKEN REFRESH STARTED ===")

            # Validate prerequisites
            if not self.refresh_token:
                self.logger.error("Cannot refresh token: missing refresh_token")
                self.logger.info("=== OAUTH TOKEN REFRESH FAILED ===")
                return False

            if not self.client_secret:
                self.logger.error("Cannot refresh token: missing client_secret")
                self.logger.info("=== OAUTH TOKEN REFRESH FAILED ===")
                return False

            if not self.client_id:
                self.logger.error("Cannot refresh token: missing client_id")
                self.logger.info("=== OAUTH TOKEN REFRESH FAILED ===")
                return False

            self.logger.info("All prerequisites for token refresh are present")
            self.logger.info(f"Client ID: {self.client_id[:8]}..." if self.client_id else "Client ID: [MISSING]")
            self.logger.info(f"Refresh token length: {len(self.refresh_token)}")
            self.logger.info(f"Client secret length: {len(self.client_secret)}")
            self.logger.info(f"Current OAuth token length: {len(self.oauth_token) if self.oauth_token else 0}")

            # Prepare refresh request
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            self.logger.info(f"Making token refresh request to: {self.token_endpoint}")
            self.logger.info(f"Request data keys: {list(data.keys())}")

            # Make refresh request
            response = requests.post(self.token_endpoint, data=data, headers=headers, timeout=10)

            self.logger.info(f"Token refresh response status: {response.status_code}")
            self.logger.info(f"Response headers: {dict(response.headers)}")

            if response.status_code == 200:
                self.logger.info("Token refresh request successful (HTTP 200)")

                try:
                    token_data = response.json()
                    self.logger.info(f"Token refresh response keys: {list(token_data.keys())}")
                except Exception as json_error:
                    self.logger.error(f"Failed to parse token refresh response as JSON: {json_error}")
                    self.logger.error(f"Raw response: {response.text}")
                    self.logger.info("=== OAUTH TOKEN REFRESH FAILED ===")
                    return False

                # Update tokens
                old_token = self.oauth_token
                new_access_token = token_data.get('access_token')
                new_refresh_token = token_data.get('refresh_token')
                expires_in = token_data.get('expires_in')
                token_type = token_data.get('token_type', 'bearer')
                scope = token_data.get('scope', [])

                self.logger.info(f"Access token received: {'OK' if new_access_token else 'NOK'}")
                self.logger.info(f"Refresh token received: {'OK' if new_refresh_token else 'NOK'}")
                self.logger.info(f"Expires in: {expires_in} seconds" if expires_in else "Expires in: [NOT PROVIDED]")
                self.logger.info(f"Token type: {token_type}")
                self.logger.info(f"Scope: {scope}")

                # Validate we got a new token
                if not new_access_token:
                    self.logger.error("Token refresh response missing access_token")
                    self.logger.info("=== OAUTH TOKEN REFRESH FAILED ===")
                    return False

                # Update access token
                self.oauth_token = new_access_token
                token_changed = old_token != new_access_token
                self.logger.info(f"OAuth token updated: {'OK' if token_changed else 'NOK (same token)'}")
                if token_changed:
                    self.logger.info(f"Old token length: {len(old_token) if old_token else 0}")
                    self.logger.info(f"New token length: {len(new_access_token)}")

                # Update refresh token if provided (it may change)
                if new_refresh_token:
                    old_refresh_token = self.refresh_token
                    self.refresh_token = new_refresh_token
                    refresh_changed = old_refresh_token != new_refresh_token
                    self.logger.info(f"Refresh token updated: {'OK' if refresh_changed else 'NOK (same token)'}")
                    if refresh_changed:
                        self.logger.info(f"Old refresh token length: {len(old_refresh_token) if old_refresh_token else 0}")
                        self.logger.info(f"New refresh token length: {len(new_refresh_token)}")
                else:
                    self.logger.warning("No new refresh token provided, keeping existing one")

                # Calculate expiration time
                if expires_in:
                    self.token_expires_at = time.time() + expires_in
                    expiry_time = datetime.fromtimestamp(self.token_expires_at)
                    self.logger.info(f"Token expires at: {expiry_time} ({expires_in} seconds from now)")
                else:
                    self.logger.warning("Token refresh response missing expires_in - cannot set expiration")

                # Call callback to save new tokens
                self.logger.info("Calling token refresh callback to save new tokens...")
                if self.token_refresh_callback:
                    try:
                        self.token_refresh_callback(self.oauth_token, self.refresh_token)
                        self.logger.info("Token refresh callback completed successfully")
                    except Exception as e:
                        self.logger.error(f"Error in token refresh callback: {e}")
                        import traceback
                        self.logger.error(f"Callback traceback: {traceback.format_exc()}")
                else:
                    self.logger.warning("No token refresh callback set - tokens not saved!")

                # Re-validate configuration after successful token refresh
                self.logger.info("Re-validating API configuration with new token...")
                old_configured = self._is_configured
                self._is_configured = self._validate_config()
                if self._is_configured:
                    self.logger.info("Twitch API re-validated successfully after token refresh")
                else:
                    self.logger.error("Twitch API validation failed after token refresh")
                    self.logger.error("This indicates the new token may not be working properly")

                self.logger.info(f"Configuration status: {old_configured} -> {self._is_configured}")
                self.logger.info("=== OAUTH TOKEN REFRESH COMPLETED SUCCESSFULLY ===")
                return True
            else:
                self.logger.error(f"Token refresh request failed with status: {response.status_code}")
                self.logger.error(f"Response headers: {dict(response.headers)}")

                try:
                    if response.headers.get('content-type', '').startswith('application/json'):
                        error_data = response.json()
                        self.logger.error(f"Error response data: {error_data}")
                        error_msg = error_data.get('message', f'HTTP {response.status_code}')
                        error_status = error_data.get('status', response.status_code)
                        self.logger.error(f"Twitch API error: {error_msg} (status: {error_status})")
                    else:
                        self.logger.error(f"Non-JSON error response: {response.text}")

                    # Log specific error details and recommendations
                    if response.status_code == 400:
                        self.logger.error("BAD REQUEST (400) - Invalid request parameters")
                        self.logger.error("  Check that client_id, client_secret, and refresh_token are correct")
                        self.logger.error("  Verify that grant_type is 'refresh_token'")
                    elif response.status_code == 401:
                        self.logger.error("UNAUTHORIZED (401) - Authentication failed")
                        self.logger.error("  The refresh_token may be expired or invalid")
                        self.logger.error("  The client_secret may be incorrect")
                        self.logger.error("  You may need to re-authorize the application")
                    elif response.status_code == 403:
                        self.logger.error("FORBIDDEN (403) - Access denied")
                        self.logger.error("  The client may not have permission to refresh tokens")
                        self.logger.error("  Check that the application has the correct scopes")
                    elif response.status_code == 429:
                        self.logger.error("RATE LIMITED (429) - Too many requests")
                        self.logger.error("  Wait before retrying token refresh")
                    else:
                        self.logger.error(f"UNEXPECTED ERROR ({response.status_code})")
                        self.logger.error("  This may be a temporary Twitch API issue")

                except Exception as parse_error:
                    self.logger.error(f"Error parsing token refresh error response: {parse_error}")
                    self.logger.error(f"Raw response text: {response.text}")

                self.logger.info("=== OAUTH TOKEN REFRESH FAILED ===")
                return False

        except requests.exceptions.Timeout:
            self.logger.error("Token refresh request timed out")
            self.logger.error("  Check network connection")
            self.logger.error("  Twitch API may be experiencing issues")
            self.logger.info("=== OAUTH TOKEN REFRESH FAILED ===")
            return False
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Token refresh connection error: {e}")
            self.logger.error("  Check network connection")
            self.logger.error("  Verify internet connectivity")
            self.logger.info("=== OAUTH TOKEN REFRESH FAILED ===")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during token refresh: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            self.logger.info("=== OAUTH TOKEN REFRESH FAILED ===")
            return False

    def _ensure_valid_token(self) -> bool:
        """Ensure we have a valid token, refreshing if necessary"""
        self.logger.debug("=== TOKEN VALIDATION CHECK ===")

        if not self.oauth_token:
            self.logger.warning("No OAuth token available - cannot proceed")
            self.logger.debug("=== TOKEN VALIDATION FAILED ===")
            return False

        self.logger.debug(f"Current OAuth token length: {len(self.oauth_token)}")
        self.logger.debug(f"Token expires at: {datetime.fromtimestamp(self.token_expires_at) if self.token_expires_at else 'Unknown'}")

        # If token is expired or about to expire, try to refresh
        if self._is_token_expired():
            self.logger.info("OAuth token is expired or about to expire, attempting refresh")

            # Check if we can refresh the token
            if not self.can_refresh_token():
                self.logger.error("Token is expired but cannot refresh: missing refresh_token or client_secret")
                self.logger.debug("=== TOKEN VALIDATION FAILED ===")
                return False

            refresh_success = self._refresh_access_token()
            if refresh_success:
                self.logger.info("Token refresh successful, proceeding with API call")
                self.logger.debug("=== TOKEN VALIDATION SUCCESSFUL (AFTER REFRESH) ===")
                return True
            else:
                self.logger.error("Token refresh failed and token is expired")
                self.logger.error("Cannot proceed with API call - token is invalid")
                self.logger.debug("=== TOKEN VALIDATION FAILED ===")
                return False
        else:
            self.logger.debug("OAuth token appears to be valid (not expired)")
            self.logger.debug("=== TOKEN VALIDATION SUCCESSFUL ===")
            return True

    def get_statistics(self) -> Dict:
        """Get Twitch API statistics"""
        return {
            'is_configured': self.is_configured,
            'clips_created': self.clips_created,
            'api_errors': self.api_errors,
            'last_clip_time': self.last_clip_time.isoformat() if self.last_clip_time else None,
            'client_id': self.client_id[:8] + "..." if self.client_id else None,
            'broadcaster_id': self.broadcaster_id
        }
    
    def update_credentials(self, client_id: str, oauth_token: str, broadcaster_id: str, client_secret: str = "", refresh_token: str = ""):
        """Update Twitch API credentials"""
        self.client_id = client_id
        self.oauth_token = oauth_token
        self.broadcaster_id = broadcaster_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token

        # Re-validate configuration
        self._is_configured = self._validate_config()

        if self._is_configured:
            self.logger.info("Twitch API credentials updated successfully")
        else:
            self.logger.warning("Updated Twitch API credentials are invalid")
    
    def is_configured(self) -> bool:
        """Check if Twitch API is properly configured"""
        return self._is_configured

    def can_refresh_token(self) -> bool:
        """Check if token refresh is possible with current configuration"""
        return bool(self.refresh_token and self.client_secret)

    def force_token_refresh(self) -> bool:
        """Force a token refresh for testing/debugging purposes"""
        self.logger.info("=== FORCED TOKEN REFRESH REQUESTED ===")
        if not self.can_refresh_token():
            self.logger.error("Cannot force refresh: missing refresh_token or client_secret")
            return False

        success = self._refresh_access_token()
        if success:
            self.logger.info("Forced token refresh completed successfully")
        else:
            self.logger.error("Forced token refresh failed")

        return success
