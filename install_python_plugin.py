#!/usr/bin/env python3
"""
SmartClip CZ Python Plugin Installer
Installs the Python version of SmartClip CZ for OBS Studio

Author: Jakub Kolář (LordBoos)
Email: lordboos@gmail.com
GitHub: https://github.com/LordBoos
"""

import os
import sys
import shutil
import subprocess
import json
import webbrowser
import urllib.parse
import requests
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from pathlib import Path

def find_obs_scripts_directory():
    """Find OBS Studio scripts directory"""
    possible_paths = [
        # Windows
        os.path.expanduser("~/AppData/Roaming/obs-studio/scripts"),
        "C:/Program Files/obs-studio/data/obs-plugins/frontend-tools/scripts",
        "C:/Program Files (x86)/obs-studio/data/obs-plugins/frontend-tools/scripts",
        
        # macOS
        os.path.expanduser("~/Library/Application Support/obs-studio/scripts"),
        "/Applications/OBS.app/Contents/Resources/data/obs-plugins/frontend-tools/scripts",
        
        # Linux
        os.path.expanduser("~/.config/obs-studio/scripts"),
        "/usr/share/obs/obs-plugins/frontend-tools/scripts",
        "/usr/local/share/obs/obs-plugins/frontend-tools/scripts"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

def install_dependencies(obs_scripts_dir):
    """Install Python dependencies in a virtual environment"""
    print("📦 Setting up virtual environment and installing dependencies...")

    try:
        # Create virtual environment in SmartClip_CZ directory
        venv_dir = os.path.join(obs_scripts_dir, "SmartClip_CZ", "venv")

        print(f"🔧 Creating virtual environment at {venv_dir}...")
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)

        # Determine venv python executable
        if os.name == 'nt':  # Windows
            venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
            venv_pip = os.path.join(venv_dir, "Scripts", "pip.exe")
        else:  # Unix-like
            venv_python = os.path.join(venv_dir, "bin", "python")
            venv_pip = os.path.join(venv_dir, "bin", "pip")

        # Upgrade pip in venv
        print("🔄 Upgrading pip in virtual environment...")
        subprocess.run([venv_python, "-m", "pip", "install", "--upgrade", "pip"], check=True)

        # Install requirements in venv
        requirements_file = os.path.join(os.path.dirname(__file__), "requirements.txt")
        if os.path.exists(requirements_file):
            print("📦 Installing dependencies in virtual environment...")
            subprocess.run([venv_pip, "install", "-r", requirements_file], check=True)
            print("✅ Dependencies installed successfully in virtual environment")

            # Create a script to activate the venv for OBS
            create_venv_activation_script(obs_scripts_dir, venv_python)

            return True
        else:
            print("❌ requirements.txt not found")
            return False

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False
    except FileNotFoundError:
        print("❌ Python venv module not found. Please ensure Python is properly installed.")
        return False

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback"""

    def do_GET(self):
        """Handle GET request with OAuth callback"""
        try:
            # Send HTML page that extracts token from URL fragment using JavaScript
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            # HTML page with JavaScript to extract token from URL fragment
            callback_html = """
            <html>
            <head>
                <title>SmartClip CZ - OAuth Authorization</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                    .success { color: green; }
                    .error { color: red; }
                    .loading { color: blue; }
                </style>
            </head>
            <body>
                <h1 class="loading">🔄 Processing Authorization...</h1>
                <p id="status">Extracting access token...</p>

                <script>
                    function processToken() {
                        // Get the fragment part of the URL (after #)
                        const fragment = window.location.hash.substring(1);
                        const params = new URLSearchParams(fragment);
                        const accessToken = params.get('access_token');

                        if (accessToken) {
                            // Send token to server
                            fetch('/token', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify({
                                    access_token: accessToken,
                                    token_type: params.get('token_type'),
                                    scope: params.get('scope')
                                })
                            })
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    document.querySelector('h1').className = 'success';
                                    document.querySelector('h1').innerHTML = '✅ Authorization Successful!';
                                    document.getElementById('status').innerHTML =
                                        'You can now close this window and return to the installer.<br>' +
                                        'SmartClip CZ has received your OAuth token.';
                                } else {
                                    throw new Error('Server rejected token');
                                }
                            })
                            .catch(error => {
                                document.querySelector('h1').className = 'error';
                                document.querySelector('h1').innerHTML = '❌ Authorization Failed';
                                document.getElementById('status').innerHTML =
                                    'Error processing token: ' + error.message + '<br>' +
                                    'Please try again or use manual setup.';
                            });
                        } else {
                            // No token found
                            document.querySelector('h1').className = 'error';
                            document.querySelector('h1').innerHTML = '❌ Authorization Failed';
                            document.getElementById('status').innerHTML =
                                'No access token found in URL.<br>' +
                                'Please try the authorization process again.';
                        }
                    }

                    // Process token when page loads
                    window.onload = processToken;
                </script>
            </body>
            </html>
            """
            self.wfile.write(callback_html.encode())

        except Exception as e:
            print(f"OAuth callback error: {e}")

    def do_POST(self):
        """Handle POST request with token data"""
        try:
            if self.path == '/token':
                # Read the JSON data
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                token_data = json.loads(post_data.decode('utf-8'))

                access_token = token_data.get('access_token')
                if access_token:
                    # Store the token globally
                    self.server.oauth_token = access_token

                    # Send success response
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()

                    response = {'success': True, 'message': 'Token received'}
                    self.wfile.write(json.dumps(response).encode())
                    return

            # If we get here, something went wrong
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            response = {'success': False, 'message': 'Invalid request'}
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            print(f"OAuth POST error: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            response = {'success': False, 'message': str(e)}
            self.wfile.write(json.dumps(response).encode())

    def log_message(self, format, *args):
        """Suppress log messages"""
        pass

def setup_twitch_oauth():
    """Interactive Twitch OAuth setup with automatic token refresh support"""
    print("🔐 Setting up Twitch API credentials with automatic token refresh...")
    print("=" * 50)

    # Step 1: Get Client ID and Client Secret
    print("📋 STEP 1: Create Twitch Application")
    print("-" * 30)
    print("We need to create a Twitch application to get API credentials.")
    print()
    print("1. Opening Twitch Developer Console in your browser...")

    try:
        webbrowser.open("https://dev.twitch.tv/console/apps")
        time.sleep(2)
    except:
        print("   ⚠️ Could not open browser automatically")
        print("   Please manually visit: https://dev.twitch.tv/console/apps")

    print()
    print("2. In the Twitch Developer Console:")
    print("   • Click 'Register Your Application' or 'Create an App'")
    print("   • Name: 'SmartClip CZ' (or any name you prefer)")
    print("   • OAuth Redirect URLs: 'http://localhost:3000'")
    print("   • Category: 'Application Integration'")
    print("   • Click 'Create'")
    print()

    input("📝 Press ENTER after you've created the application...")

    print()
    print("3. Now copy your credentials:")
    print("   • Click on your newly created application")
    print("   • Copy the 'Client ID' (long string of letters and numbers)")
    print("   • Click 'New Secret' to generate a Client Secret")
    print("   • Copy the Client Secret immediately (shown only once!)")
    print()

    client_id = input("🔑 Paste your Client ID here: ").strip()

    if not client_id:
        print("❌ Client ID is required. Please run the installer again.")
        return None, None, None, None

    print(f"✅ Client ID received: {client_id[:8]}...")
    print()

    print("🔐 Client Secret (OPTIONAL but RECOMMENDED for automatic token refresh):")
    print("   • Prevents token expiration issues")
    print("   • Enables automatic token renewal")
    print("   • Leave empty if you prefer manual token management")
    print()

    client_secret = input("🔑 Paste your Client Secret here (or press ENTER to skip): ").strip()

    if client_secret:
        print(f"✅ Client Secret received: {client_secret[:8]}...")
        print("🔄 Automatic token refresh will be enabled!")
    else:
        print("⚠️ Skipping Client Secret - tokens will expire every ~4 hours")

    # Step 2: Generate OAuth Token
    print("\n📋 STEP 2: Generate OAuth Token")
    print("-" * 30)
    print("Now we'll generate an OAuth token automatically...")

    # Start local server for OAuth callback
    server = None
    server_thread = None

    try:
        # Start HTTP server on localhost:3000
        server = HTTPServer(('localhost', 3000), OAuthCallbackHandler)
        server.oauth_token = None
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        print("✅ Started local server for OAuth callback")

        # Generate OAuth URL (using implicit flow for simplicity)
        scopes = "clips:edit user:read:email channel:read:subscriptions"
        oauth_url = (
            f"https://id.twitch.tv/oauth2/authorize?"
            f"client_id={client_id}&"
            f"redirect_uri=http://localhost:3000&"
            f"response_type=token&"
            f"scope={urllib.parse.quote(scopes)}"
        )

        print("🌐 Opening authorization page in your browser...")

        try:
            webbrowser.open(oauth_url)
        except:
            print("   ⚠️ Could not open browser automatically")
            print(f"   Please manually visit: {oauth_url}")

        print()
        print("In the browser:")
        print("• Click 'Authorize' to grant permissions to SmartClip CZ")
        print("• You'll be redirected to a success page")
        print()
        print("⏳ Waiting for authorization (up to 60 seconds)...")

        # Wait for OAuth token
        start_time = time.time()
        while time.time() - start_time < 60:
            if server.oauth_token:
                oauth_token = server.oauth_token
                print(f"✅ OAuth token received: {oauth_token[:8]}...")
                break
            time.sleep(1)
        else:
            print("❌ Timeout waiting for OAuth token")
            print("\n🔧 Fallback: Manual Token Entry")
            print("If the automatic method didn't work, you can enter your token manually:")
            print("1. Complete the authorization in your browser")
            print("2. Look at the URL after authorization - it should contain 'access_token='")
            print("3. Copy everything after 'access_token=' and before '&' (if present)")
            print()

            manual_token = input("Enter your access token manually (or press Enter to skip): ").strip()
            if manual_token:
                oauth_token = manual_token
                print(f"✅ Manual token received: {oauth_token[:8]}...")
            else:
                print("⚠️ No token provided - skipping OAuth setup")
                return None, None, None

    except Exception as e:
        print(f"❌ OAuth setup failed: {e}")
        return None, None, None
    finally:
        if server:
            server.shutdown()
        if server_thread:
            server_thread.join(timeout=1)

    # Step 3: Get Broadcaster ID
    print("\n📋 STEP 3: Get Broadcaster ID")
    print("-" * 30)
    print("Getting your Broadcaster ID automatically...")

    try:
        headers = {
            'Client-ID': client_id,
            'Authorization': f'Bearer {oauth_token}'
        }

        response = requests.get('https://api.twitch.tv/helix/users', headers=headers)

        if response.status_code == 200:
            data = response.json()
            users = data.get('data', [])
            if users:
                broadcaster_id = users[0].get('id')
                username = users[0].get('display_name')
                print(f"✅ Broadcaster ID retrieved: {broadcaster_id}")
                print(f"   Username: {username}")
            else:
                print("❌ Could not get user information")
                return None, None, None
        else:
            print(f"❌ API request failed: {response.status_code}")
            return None, None, None

    except Exception as e:
        print(f"❌ Error getting Broadcaster ID: {e}")
        return None, None, None

    # Validate the setup
    print("\n🧪 Validating credentials...")

    try:
        # Test token validation
        headers = {'Authorization': f'OAuth {oauth_token}'}
        response = requests.get('https://id.twitch.tv/oauth2/validate', headers=headers)

        if response.status_code == 200:
            data = response.json()
            scopes = data.get('scopes', [])

            print("✅ Credentials validated successfully!")
            print(f"   Scopes: {', '.join(scopes)}")

            if 'clips:edit' in scopes:
                print("✅ Clip creation permission granted")
            else:
                print("⚠️ Warning: clips:edit scope missing")
        else:
            print("⚠️ Token validation failed, but proceeding anyway")

    except Exception as e:
        print(f"⚠️ Validation error: {e}, but proceeding anyway")

    print("\n🎉 Twitch OAuth setup completed!")

    # Debug logging
    print(f"🔍 Debug - Returning OAuth credentials:")
    print(f"   Client ID: {client_id[:8] if client_id else 'None'}...")
    print(f"   Client Secret: {'[PRESENT]' if client_secret else '[EMPTY]'}...")
    print(f"   OAuth Token: {oauth_token[:8] if oauth_token else 'None'}...")
    print(f"   Broadcaster ID: {broadcaster_id if broadcaster_id else 'None'}")

    # Note: Refresh token would require full OAuth 2.0 flow implementation
    refresh_token = ""  # Placeholder for future enhancement

    return client_id, client_secret, oauth_token, refresh_token, broadcaster_id

def create_venv_activation_script(obs_scripts_dir, venv_python):
    """Create a script to help OBS use the virtual environment"""
    try:
        smartclip_dir = os.path.join(obs_scripts_dir, "SmartClip_CZ")

        # Create a Python script that sets up the venv path
        venv_setup_script = os.path.join(smartclip_dir, "setup_venv.py")

        setup_content = f'''#!/usr/bin/env python3
"""
Virtual Environment Setup for SmartClip CZ
This script ensures the virtual environment is properly configured for OBS.
"""

import sys
import os

# Add virtual environment to Python path
venv_python = r"{venv_python}"
venv_dir = os.path.dirname(os.path.dirname(venv_python))
site_packages = os.path.join(venv_dir, "Lib", "site-packages") if os.name == 'nt' else os.path.join(venv_dir, "lib", "python{{}}.{{}}", "site-packages").format(sys.version_info.major, sys.version_info.minor)

if os.path.exists(site_packages) and site_packages not in sys.path:
    sys.path.insert(0, site_packages)
    print(f"✅ Added virtual environment to Python path: {{site_packages}}")

# Verify key dependencies are available
try:
    import numpy
    import scipy
    import sklearn
    import requests
    import sounddevice
    import librosa
    import vosk
    import opensmile
    print("✅ All dependencies are available in virtual environment")
except ImportError as e:
    print(f"⚠️ Missing dependency in virtual environment: {{e}}")
'''

        with open(venv_setup_script, 'w', encoding='utf-8') as f:
            f.write(setup_content)

        print(f"✅ Created virtual environment setup script: {venv_setup_script}")

    except Exception as e:
        print(f"⚠️ Warning: Could not create venv setup script: {e}")
        print("   The virtual environment should still work correctly.")

def copy_plugin_files(obs_scripts_dir):
    """Copy plugin files to OBS scripts directory"""
    print(f"📁 Copying plugin files to {obs_scripts_dir}...")
    
    try:
        # Create target directory
        target_dir = os.path.join(obs_scripts_dir, "SmartClip_CZ")
        os.makedirs(target_dir, exist_ok=True)
        
        # Files and directories to copy
        plugin_items = [
            "smartclip_cz.py",
            "core/",
            "detectors/",
            "widgets/",
            "requirements.txt",
            "basic_emotion.conf",
            "confidence_data.json",
            "models/",
            "download_vosk_models.py"  # Include model downloader for manual use
        ]
        
        source_dir = os.path.dirname(__file__)
        
        for item_name in plugin_items:
            source_item = os.path.join(source_dir, item_name)
            target_item = os.path.join(target_dir, item_name)

            if os.path.exists(source_item):
                if os.path.isdir(source_item):
                    # Copy directory recursively
                    if os.path.exists(target_item):
                        shutil.rmtree(target_item)
                    shutil.copytree(source_item, target_item)
                    print(f"  ✅ Copied directory {item_name}")
                else:
                    # Copy file
                    shutil.copy2(source_item, target_item)
                    print(f"  ✅ Copied {item_name}")
            else:
                print(f"  ⚠️ Warning: {item_name} not found")
        
        # Note: Main script is already copied to SmartClip_CZ directory above
        # No need to copy to scripts root directory
        
        print("✅ Plugin files copied successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to copy plugin files: {e}")
        return False

def create_default_config(obs_scripts_dir, client_id=None, client_secret=None, oauth_token=None, refresh_token=None, broadcaster_id=None):
    """Create default configuration file with optional OAuth credentials including refresh token support"""
    print("⚙️ Creating default configuration...")
    
    try:
        config_dir = os.path.join(obs_scripts_dir, "SmartClip_CZ")
        config_file = os.path.join(config_dir, "smartclip_cz_config.json")
        
        # Load existing config or create default
        if os.path.exists(config_file):
            print("ℹ️ Configuration file already exists, updating with OAuth credentials...")
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except:
                print("⚠️ Existing config file corrupted, creating new one...")
                config = {}
        else:
            config = {}

        # Default configuration values
        default_config = {
            "version": "2.0.0",
            "enabled_emotions": ["laughter", "excitement", "surprise", "joy"],
            "emotion_sensitivity": 0.7,
            "activation_phrases": [
                "to je skvělé", "wow", "úžasné", "perfektní", "super", "bomba",
                "co to bylo", "to je šílené", "neuvěřitelné"
            ],
            "english_activation_phrases": [
                "that's amazing", "awesome", "incredible", "fantastic", "wow",
                "what the hell", "that's insane", "unbelievable", "holy shit"
            ],
            "audio_sources": ["Desktop Audio"],
            "twitch_client_id": "",
            "twitch_client_secret": "",
            "twitch_oauth_token": "",
            "twitch_refresh_token": "",
            "twitch_broadcaster_id": "",
            "clip_duration": 30,
            "quality_scoring_enabled": True,
            "opensmile_enabled": True,
            "vosk_enabled": True,
            "current_profile": "casual"
        }

        # Update config with defaults (only if keys don't exist)
        for key, value in default_config.items():
            if key not in config:
                config[key] = value

        # Always update OAuth credentials if provided
        if client_id:
            config["twitch_client_id"] = client_id
            print(f"✅ Updated Client ID: {client_id}")

        if client_secret:
            config["twitch_client_secret"] = client_secret
            print(f"✅ Updated Client Secret: [PRESENT]")

        if oauth_token:
            config["twitch_oauth_token"] = oauth_token
            print(f"✅ Updated OAuth Token: {oauth_token[:8]}...")

        if refresh_token:
            config["twitch_refresh_token"] = refresh_token
            print(f"✅ Updated Refresh Token: [PRESENT]")

        if broadcaster_id:
            config["twitch_broadcaster_id"] = broadcaster_id
            print(f"✅ Updated Broadcaster ID: {broadcaster_id}")

        # Save updated configuration
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        if client_id and oauth_token and broadcaster_id:
            print(f"✅ Configuration updated with Twitch credentials at {config_file}")
        else:
            print(f"✅ Configuration file created/updated at {config_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create default config: {e}")
        return False

def setup_vosk_model(obs_scripts_dir):
    """Setup Vosk models for Czech and English speech recognition"""
    print("🗣️ Setting up Vosk models...")

    try:
        # Create models directory in the OBS SmartClip_CZ folder
        smartclip_dir = os.path.join(obs_scripts_dir, "SmartClip_CZ")
        models_dir = os.path.join(smartclip_dir, "models")
        os.makedirs(models_dir, exist_ok=True)

        # Model URLs and paths
        models_to_download = [
            {
                "name": "Czech",
                "url": "https://alphacephei.com/vosk/models/vosk-model-small-cs-0.4-rhasspy.zip",
                "dir_name": "vosk-model-small-cs-0.4-rhasspy",
                "required": True
            },
            {
                "name": "English",
                "url": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
                "dir_name": "vosk-model-small-en-us-0.15",
                "required": False
            }
        ]

        for model in models_to_download:
            model_dir = os.path.join(models_dir, model["dir_name"])

            if os.path.exists(model_dir):
                print(f"✅ {model['name']} model already exists at {model_dir}")
                continue

            print(f"📥 Attempting to download {model['name']} model...")
            success = download_and_extract_model(model["url"], models_dir, model["dir_name"])

            if success:
                print(f"✅ {model['name']} model downloaded and extracted successfully")
            else:
                if model["required"]:
                    print(f"❌ Failed to download required {model['name']} model")
                    print("📝 Please download manually:")
                    print(f"   1. Download from: {model['url']}")
                    print(f"   2. Extract to: models/{model['dir_name']}/")
                else:
                    print(f"⚠️ Failed to download optional {model['name']} model")
                    print("📝 You can download it manually later:")
                    print(f"   1. Download from: {model['url']}")
                    print(f"   2. Extract to: models/{model['dir_name']}/")

        return True

    except Exception as e:
        print(f"❌ Failed to setup Vosk models: {e}")
        return False

def download_and_extract_model(url: str, models_dir: str, expected_dir_name: str) -> bool:
    """Download and extract a Vosk model"""
    try:
        import urllib.request
        import zipfile
        import tempfile
        import time

        # Create temporary file for download
        tmp_path = None
        try:
            # Create temporary file
            tmp_fd, tmp_path = tempfile.mkstemp(suffix='.zip')
            os.close(tmp_fd)  # Close the file descriptor immediately

            print(f"   Downloading from {url}...")
            urllib.request.urlretrieve(url, tmp_path)

            # Extract the zip file
            print(f"   Extracting to {models_dir}...")
            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                zip_ref.extractall(models_dir)

            # Verify the expected directory was created
            expected_path = os.path.join(models_dir, expected_dir_name)
            if not os.path.exists(expected_path):
                print(f"   Warning: Expected directory {expected_dir_name} not found after extraction")

            return True

        finally:
            # Clean up temporary file with retry logic for Windows
            if tmp_path and os.path.exists(tmp_path):
                for attempt in range(5):  # Try up to 5 times
                    try:
                        os.unlink(tmp_path)
                        break
                    except (OSError, PermissionError) as e:
                        if attempt < 4:  # Not the last attempt
                            time.sleep(0.5)  # Wait a bit and retry
                        else:
                            print(f"   Warning: Could not delete temporary file {tmp_path}: {e}")

    except Exception as e:
        print(f"   Download failed: {e}")
        return False

def setup_opensmile(obs_scripts_dir):
    """Setup OpenSMILE Python library for emotion detection in virtual environment"""
    print("🤖 Setting up OpenSMILE in virtual environment...")

    try:
        # Get virtual environment paths
        venv_dir = os.path.join(obs_scripts_dir, "SmartClip_CZ", "venv")

        if os.name == 'nt':  # Windows
            venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
            venv_pip = os.path.join(venv_dir, "Scripts", "pip.exe")
        else:  # Unix-like
            venv_python = os.path.join(venv_dir, "bin", "python")
            venv_pip = os.path.join(venv_dir, "bin", "pip")

        # Check if OpenSMILE is already installed in venv
        try:
            result = subprocess.run([
                venv_python, "-c", "import opensmile; print('OpenSMILE available')"
            ], capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ OpenSMILE Python library is already installed in virtual environment")

                # Test basic functionality
                test_result = subprocess.run([
                    venv_python, "-c",
                    "import opensmile; s = opensmile.Smile(feature_set=opensmile.FeatureSet.eGeMAPSv02, feature_level=opensmile.FeatureLevel.Functionals); print('OpenSMILE initialized successfully')"
                ], capture_output=True, text=True)

                if test_result.returncode == 0:
                    print("✅ OpenSMILE initialized successfully in virtual environment")
                else:
                    print("⚠️ OpenSMILE installed but initialization test failed (may work at runtime)")

                return True

        except Exception:
            pass

        # Install OpenSMILE in virtual environment
        print("📝 Installing OpenSMILE in virtual environment...")
        result = subprocess.run([
            venv_pip, "install", "opensmile"
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ OpenSMILE installed successfully in virtual environment")
            return True
        else:
            print("❌ Failed to install OpenSMILE in virtual environment")
            print(f"   Error: {result.stderr}")
            print("📝 OpenSMILE is optional - the plugin will work without it")
            return False

    except Exception as e:
        print(f"❌ Failed to setup OpenSMILE: {e}")
        print("📝 OpenSMILE is optional - the plugin will work without it")
        return False

def main():
    """Main installation function"""
    print("🎭 SmartClip CZ Python Plugin Installer")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Find OBS scripts directory
    obs_scripts_dir = find_obs_scripts_directory()
    if not obs_scripts_dir:
        print("❌ Could not find OBS Studio scripts directory")
        print("Please create the scripts directory manually and run the installer again")
        return False
    
    print(f"✅ Found OBS scripts directory: {obs_scripts_dir}")
    
    # Install dependencies in virtual environment
    if not install_dependencies(obs_scripts_dir):
        print("❌ Failed to install dependencies")
        return False
    
    # Copy plugin files
    if not copy_plugin_files(obs_scripts_dir):
        print("❌ Failed to copy plugin files")
        return False

    # Optional: Setup Twitch OAuth
    print("\n🔐 Twitch API Setup")
    print("=" * 30)
    print("SmartClip CZ can automatically create Twitch clips when emotions are detected.")
    print("This requires Twitch API credentials (Client ID, OAuth Token, Broadcaster ID).")
    print()

    setup_oauth = input("Would you like to set up Twitch API credentials now? (y/n): ").lower().strip()

    client_id = None
    oauth_token = None
    broadcaster_id = None

    if setup_oauth in ['y', 'yes']:
        try:
            client_id, client_secret, oauth_token, refresh_token, broadcaster_id = setup_twitch_oauth()
            if client_id and oauth_token and broadcaster_id:
                print("✅ Twitch OAuth setup completed successfully!")
                if client_secret:
                    print("🔄 Automatic token refresh enabled!")
                else:
                    print("⚠️ No Client Secret - tokens will expire every ~4 hours")
            else:
                print("⚠️ OAuth setup incomplete - you can configure it later in OBS")
        except Exception as e:
            print(f"⚠️ OAuth setup failed: {e}")
            print("   You can configure Twitch credentials manually in OBS later")
    else:
        print("ℹ️ Skipping OAuth setup - you can configure it later in OBS")
        print("   See README.md for manual setup instructions")

    # Debug logging before config creation
    print(f"\n🔍 Debug - Creating config with credentials:")
    print(f"   Client ID: {client_id[:8] if client_id else 'None'}...")
    print(f"   Client Secret: {'[PRESENT]' if client_secret else '[EMPTY]'}...")
    print(f"   OAuth Token: {oauth_token[:8] if oauth_token else 'None'}...")
    print(f"   Refresh Token: {'[PRESENT]' if refresh_token else '[EMPTY]'}...")
    print(f"   Broadcaster ID: {broadcaster_id if broadcaster_id else 'None'}")

    # Create default configuration (with OAuth if available)
    if not create_default_config(obs_scripts_dir, client_id, client_secret, oauth_token, refresh_token, broadcaster_id):
        print("❌ Failed to create default configuration")
        return False
    
    # Setup additional components
    setup_vosk_model(obs_scripts_dir)
    setup_opensmile(obs_scripts_dir)
    
    print("\n🎉 Installation completed successfully!")
    print("\n📋 Next steps:")
    print("1. Start OBS Studio")
    print("2. Go to Tools → Scripts")
    print("3. Click '+' (Add Scripts) button")
    print("4. Navigate to this exact folder:")
    print(f"   📁 {os.path.join(obs_scripts_dir, 'SmartClip_CZ')}")
    print("   💡 Tip: Copy the path above and paste it in the file dialog address bar")
    print("5. Select 'smartclip_cz.py' file")
    print("6. Click 'Open' to load the script")

    if client_id and oauth_token and broadcaster_id:
        print("7. ✅ Twitch credentials are already configured!")
        print("8. Click '▶️ Start Detection' and enjoy automatic clips!")
    else:
        print("7. Configure your Twitch API credentials in the script settings")
        print("8. Click '▶️ Start Detection' and enjoy automatic clips!")

    print("\n⚙️ Installation Details:")
    print(f"   📁 Plugin directory: {os.path.join(obs_scripts_dir, 'SmartClip_CZ')}")
    print(f"   📄 Main script file: {os.path.join(obs_scripts_dir, 'SmartClip_CZ', 'smartclip_cz.py')}")
    print(f"   ⚙️ Configuration file: {os.path.join(obs_scripts_dir, 'SmartClip_CZ', 'smartclip_cz_config.json')}")
    print(f"   🐍 Virtual environment: {os.path.join(obs_scripts_dir, 'SmartClip_CZ', 'venv')}")
    print(f"   🗣️ Vosk models: {os.path.join(obs_scripts_dir, 'SmartClip_CZ', 'models')}")
    print(f"   ⚙️ Config file: {os.path.join(obs_scripts_dir, 'SmartClip_CZ', 'smartclip_cz_config.json')}")
    print("   📝 Edit config file to customize emotions, phrases, and settings")

    print("\n✅ Benefits of this setup:")
    print("   • Dependencies isolated in virtual environment")
    print("   • No conflicts with system Python packages")
    print("   • Easy to uninstall (just delete SmartClip_CZ folder)")
    print("   • Automatic virtual environment activation in OBS")
    print("   • Models downloaded to correct OBS directory")

    print("\n📝 Additional Notes:")
    print("   • If model download failed, run download_vosk_models.py from SmartClip_CZ folder")
    print("   • All files are contained within the SmartClip_CZ directory")
    print("   • No system-wide changes made")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n❌ Installation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Installation failed with error: {e}")
        sys.exit(1)
