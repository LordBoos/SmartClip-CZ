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

        # Validate configuration
        self._is_configured = self._validate_config()

        if self._is_configured:
            self.logger.info("Twitch API configured successfully")
        else:
            self.logger.warning("Twitch API not properly configured")
    
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
            headers = {
                "Client-ID": self.client_id,
                "Authorization": f"Bearer {self.oauth_token}",
                "Content-Type": "application/json"
            }
            
            # Test with a simple API call (get user info)
            url = f"{self.base_url}/users"
            params = {"id": self.broadcaster_id}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    user_info = data["data"][0]
                    self.logger.info(f"Connected to Twitch API for user: {user_info.get('display_name', 'Unknown')}")
                    return True
                else:
                    self.logger.warning("Twitch API test: No user data returned")
                    return False
            elif response.status_code == 401:
                self.logger.error("Twitch API authentication failed - check OAuth token")
                return False
            else:
                self.logger.error(f"Twitch API test failed: {response.status_code} - {response.text}")
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
            if not self._is_configured:
                self.logger.warning("Cannot create clip - Twitch API not configured")
                return None

            # Ensure we have a valid token before making the request
            if not self._ensure_valid_token():
                self.logger.error("Cannot create clip - invalid or expired token")
                return None
            
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
                self.logger.error("Clip creation failed - authentication error")
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

    def set_token_refresh_callback(self, callback):
        """Set callback function to save new tokens when refreshed"""
        self.token_refresh_callback = callback

    def _is_token_expired(self) -> bool:
        """Check if the current token is expired or about to expire"""
        if not self.token_expires_at:
            self.logger.debug("No token expiration time set, assuming token is valid")
            return False

        # Consider token expired if it expires within the next 5 minutes
        buffer_time = 300  # 5 minutes in seconds
        current_time = time.time()
        time_until_expiry = self.token_expires_at - current_time

        is_expired = time_until_expiry <= buffer_time
        if is_expired:
            self.logger.info(f"Token expires in {time_until_expiry:.0f} seconds (within {buffer_time}s buffer)")
        else:
            self.logger.debug(f"Token expires in {time_until_expiry:.0f} seconds")

        return is_expired

    def _refresh_access_token(self) -> bool:
        """Refresh the OAuth access token using the refresh token"""
        try:
            if not self.refresh_token or not self.client_secret:
                self.logger.warning("Cannot refresh token: missing refresh_token or client_secret")
                return False

            self.logger.info("Attempting to refresh OAuth token...")

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

            # Make refresh request
            response = requests.post(self.token_endpoint, data=data, headers=headers, timeout=10)

            if response.status_code == 200:
                token_data = response.json()

                # Update tokens
                self.oauth_token = token_data.get('access_token')
                new_refresh_token = token_data.get('refresh_token')
                expires_in = token_data.get('expires_in')

                # Update refresh token if provided (it may change)
                if new_refresh_token:
                    self.refresh_token = new_refresh_token

                # Calculate expiration time
                if expires_in:
                    self.token_expires_at = time.time() + expires_in

                self.logger.info("OAuth token refreshed successfully")

                # Call callback to save new tokens
                if self.token_refresh_callback:
                    try:
                        self.token_refresh_callback(self.oauth_token, self.refresh_token)
                    except Exception as e:
                        self.logger.error(f"Error in token refresh callback: {e}")

                return True
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = error_data.get('message', f'HTTP {response.status_code}')
                self.logger.error(f"Token refresh failed: {error_msg}")
                return False

        except Exception as e:
            self.logger.error(f"Error refreshing token: {e}")
            return False

    def _ensure_valid_token(self) -> bool:
        """Ensure we have a valid token, refreshing if necessary"""
        if not self.oauth_token:
            self.logger.warning("No OAuth token available")
            return False

        # If token is expired or about to expire, try to refresh
        if self._is_token_expired():
            self.logger.info("OAuth token is expired or about to expire, attempting refresh")
            if not self._refresh_access_token():
                self.logger.error("Failed to refresh expired token")
                return False
        else:
            self.logger.debug("OAuth token is valid")

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
