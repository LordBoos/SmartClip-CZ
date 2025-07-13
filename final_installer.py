import os
import sys
import shutil
import subprocess
import json
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import threading
import urllib.request
import zipfile
import tempfile
from pathlib import Path
import webbrowser
import urllib.parse
import requests
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback with comprehensive logging"""

    def log_oauth_callback(self, message):
        """Log OAuth callback events"""
        try:
            # Try to get install path from server if available
            log_file = "oauth_callback_debug.log"
            if hasattr(self.server, 'install_path') and self.server.install_path:
                log_file = os.path.join(self.server.install_path, "oauth_callback_debug.log")

            with open(log_file, 'a', encoding='utf-8') as f:
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {message}\n")
                f.flush()
            print(f"OAuth Callback: {message}")
        except Exception as e:
            print(f"OAuth callback logging error: {e}")

    def do_GET(self):
        """Handle GET request with OAuth callback"""
        try:
            self.log_oauth_callback(f"=== OAUTH CALLBACK RECEIVED ===")
            self.log_oauth_callback(f"Request path: {self.path}")
            self.log_oauth_callback(f"Request headers: {dict(self.headers)}")
            self.log_oauth_callback(f"Client address: {self.client_address}")
            self.log_oauth_callback(f"Server: {self.server}")
            self.log_oauth_callback(f"Sending HTML response...")
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
                <h1 class="loading">Processing Authorization...</h1>
                <p id="status">Extracting access token...</p>

                <script>
                    function processToken() {
                        // Get the fragment part of the URL (after #)
                        // Check for authorization code (authorization code flow)
                        const urlParams = new URLSearchParams(window.location.search);
                        const authCode = urlParams.get('code');

                        // Fallback to fragment for access token (implicit flow)
                        const fragment = window.location.hash.substring(1);
                        const fragmentParams = new URLSearchParams(fragment);
                        const accessToken = fragmentParams.get('access_token');

                        if (authCode) {
                            // Send authorization code to Python server for token exchange
                            fetch('/code', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ code: authCode })
                            }).then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    document.getElementById('status').innerHTML = '<span class="success">Authorization successful! You can close this window.</span>';
                                } else {
                                    document.getElementById('status').innerHTML = '<span class="error">Token exchange failed: ' + data.error + '</span>';
                                }
                            }).catch(error => {
                                document.getElementById('status').innerHTML = '<span class="error">Error: ' + error + '</span>';
                            });
                        } else if (accessToken) {
                            // Fallback: Send access token directly (implicit flow)
                            fetch('/token', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ token: accessToken })
                            }).then(() => {
                                document.getElementById('status').innerHTML =
                                    '<h1 class="success">Authorization Successful!</h1>' +
                                    '<p>You can close this window and return to the installer.</p>';
                            }).catch(() => {
                                document.getElementById('status').innerHTML =
                                    '<h1 class="error">Error processing token</h1>';
                            });
                        } else {
                            document.getElementById('status').innerHTML =
                                '<h1 class="error">No access token found</h1>' +
                                '<p>Please try the authorization process again.</p>';
                        }
                    }

                    // Process token when page loads
                    window.onload = processToken;
                </script>
            </body>
            </html>
            """

            self.wfile.write(callback_html.encode('utf-8'))

        except Exception as e:
            self.send_error(500, f"Server error: {e}")

    def do_POST(self):
        """Handle POST request with OAuth token"""
        try:
            self.log_oauth_callback(f"=== OAUTH POST REQUEST RECEIVED ===")
            self.log_oauth_callback(f"POST path: {self.path}")
            self.log_oauth_callback(f"POST headers: {dict(self.headers)}")

            if self.path == '/code':
                self.log_oauth_callback("Processing /code POST request for authorization code exchange...")
                content_length = int(self.headers['Content-Length'])
                self.log_oauth_callback(f"Content length: {content_length}")

                post_data = self.rfile.read(content_length)
                self.log_oauth_callback(f"Raw POST data: {post_data}")

                data = json.loads(post_data.decode('utf-8'))
                self.log_oauth_callback(f"Parsed JSON data: {data}")

                # Exchange authorization code for tokens
                auth_code = data.get('code')
                self.log_oauth_callback(f"Authorization code: {'[PRESENT]' if auth_code else '[MISSING]'}")

                if auth_code and hasattr(self.server, 'client_id') and hasattr(self.server, 'client_secret'):
                    try:
                        # Exchange code for tokens
                        token_response = self.exchange_code_for_tokens(auth_code, self.server.client_id, self.server.client_secret)
                        if token_response:
                            self.server.oauth_token = token_response.get('access_token')
                            self.server.refresh_token = token_response.get('refresh_token', '')
                            self.log_oauth_callback("✓ Token exchange successful")

                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            self.wfile.write(b'{"success": true}')
                        else:
                            self.log_oauth_callback("✗ Token exchange failed")
                            self.send_response(400)
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            self.wfile.write(b'{"success": false, "error": "Token exchange failed"}')
                    except Exception as e:
                        self.log_oauth_callback(f"✗ Token exchange error: {e}")
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(f'{{"success": false, "error": "{str(e)}"}}'.encode())
                else:
                    self.log_oauth_callback("✗ Missing authorization code or client credentials")
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'{"success": false, "error": "Missing required data"}')

            elif self.path == '/token':
                self.log_oauth_callback("Processing /token POST request (fallback implicit flow)...")
                content_length = int(self.headers['Content-Length'])
                self.log_oauth_callback(f"Content length: {content_length}")

                post_data = self.rfile.read(content_length)
                self.log_oauth_callback(f"Raw POST data: {post_data}")

                data = json.loads(post_data.decode('utf-8'))
                self.log_oauth_callback(f"Parsed JSON data: {data}")

                # Store token in server instance
                token = data.get('token')
                self.log_oauth_callback(f"Extracted token: {'[PRESENT]' if token else '[MISSING]'}")
                self.log_oauth_callback(f"Token length: {len(token) if token else 0}")

                self.server.oauth_token = token
                self.server.refresh_token = ""  # Implicit flow doesn't provide refresh tokens
                self.log_oauth_callback(f"Token stored in server.oauth_token")

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "success"}')
                self.log_oauth_callback("✓ Success response sent to browser")
            else:
                self.log_oauth_callback(f"✗ Unknown POST path: {self.path}")
                self.send_error(404)

        except Exception as e:
            self.log_oauth_callback(f"✗ CRITICAL ERROR in POST handler: {e}")
            import traceback
            self.log_oauth_callback(f"Traceback: {traceback.format_exc()}")
            self.send_error(500, f"Server error: {e}")

    def exchange_code_for_tokens(self, auth_code, client_id, client_secret):
        """Exchange authorization code for access and refresh tokens"""
        try:
            self.log_oauth_callback("Starting token exchange with Twitch API...")

            token_url = "https://id.twitch.tv/oauth2/token"
            token_data = {
                'client_id': client_id,
                'client_secret': client_secret,
                'code': auth_code,
                'grant_type': 'authorization_code',
                'redirect_uri': 'http://localhost:3000'
            }

            self.log_oauth_callback(f"Token exchange URL: {token_url}")
            self.log_oauth_callback(f"Token data: {dict(token_data, client_secret='[HIDDEN]')}")

            response = requests.post(token_url, data=token_data, timeout=10)
            self.log_oauth_callback(f"Token exchange response status: {response.status_code}")

            if response.status_code == 200:
                token_response = response.json()
                self.log_oauth_callback(f"Token exchange successful: {list(token_response.keys())}")
                return token_response
            else:
                self.log_oauth_callback(f"Token exchange failed: {response.text}")
                return None

        except Exception as e:
            self.log_oauth_callback(f"Token exchange exception: {e}")
            return None

    def log_message(self, format, *args):
        """Suppress log messages"""
        pass

class SmartClipInstaller:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SmartClip CZ Installer v1.0")
        self.root.geometry("650x600")
        self.root.resizable(False, False)
        
        # Center window
        self.center_window()
        
        # Variables
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Ready to install SmartClip CZ")
        self.path_var = tk.StringVar()
        
        self.setup_ui()
        self.find_obs_directory()
    
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (650 // 2)
        y = (self.root.winfo_screenheight() // 2) - (600 // 2)
        self.root.geometry(f"650x600+{x}+{y}")
    
    def setup_ui(self):
        """Setup the installer UI"""
        # Header with gradient-like effect
        header_frame = tk.Frame(self.root, bg="#2c3e50", height=120)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        # Title
        title_label = tk.Label(header_frame, text="SmartClip CZ", 
                              font=("Arial", 24, "bold"), 
                              fg="white", bg="#2c3e50")
        title_label.pack(pady=(20, 5))
        
        # Subtitle
        subtitle_label = tk.Label(header_frame, text="Automatic Twitch Clip Creator for OBS Studio", 
                                 font=("Arial", 12), 
                                 fg="#ecf0f1", bg="#2c3e50")
        subtitle_label.pack()
        
        # Version
        version_label = tk.Label(header_frame, text="Version 1.0 - Standalone Installer", 
                                font=("Arial", 9), 
                                fg="#bdc3c7", bg="#2c3e50")
        version_label.pack(pady=(5, 0))
        
        # Main content
        content_frame = tk.Frame(self.root, padx=30, pady=25)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Description
        desc_text = """This installer will set up SmartClip CZ for OBS Studio with all required components.

Features included:
• Emotion detection from audio (laughter, excitement, surprise, joy)
• Czech and English activation phrase recognition
• Automatic Twitch clip creation with smart titles
• Complete Python environment with all dependencies"""

        desc_label = tk.Label(content_frame, text=desc_text,
                             justify=tk.LEFT, wraplength=580,
                             font=("Arial", 10), fg="#2c3e50")
        desc_label.pack(pady=(0, 15))
        
        # Installation path section
        path_section = tk.LabelFrame(content_frame, text="Installation Location", 
                                    font=("Arial", 10, "bold"), fg="#2c3e50")
        path_section.pack(fill=tk.X, pady=(0, 20))
        
        path_inner = tk.Frame(path_section, padx=10, pady=10)
        path_inner.pack(fill=tk.X)
        
        self.path_entry = tk.Entry(path_inner, textvariable=self.path_var,
                                  font=("Arial", 9), relief=tk.SOLID, bd=1)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        browse_btn = tk.Button(path_inner, text="Browse...", 
                              command=self.browse_path, width=12,
                              relief=tk.SOLID, bd=1)
        browse_btn.pack(side=tk.RIGHT, padx=(8, 0))
        
        # Progress section
        progress_section = tk.LabelFrame(content_frame, text="Installation Progress", 
                                        font=("Arial", 10, "bold"), fg="#2c3e50")
        progress_section.pack(fill=tk.X, pady=(0, 20))
        
        progress_inner = tk.Frame(progress_section, padx=10, pady=10)
        progress_inner.pack(fill=tk.X)
        
        self.progress_bar = ttk.Progressbar(progress_inner, 
                                           variable=self.progress_var, 
                                           maximum=100,
                                           style="TProgressbar")
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))
        
        self.status_label = tk.Label(progress_inner, textvariable=self.status_var,
                                    font=("Arial", 9), fg="#7f8c8d", anchor=tk.W)
        self.status_label.pack(fill=tk.X)
        
        # Buttons section
        button_section = tk.Frame(content_frame)
        button_section.pack(fill=tk.X, pady=(20, 10))

        # Center the buttons
        button_frame = tk.Frame(button_section)
        button_frame.pack(expand=True)

        self.install_btn = tk.Button(button_frame, text="Install SmartClip CZ",
                                    command=self.start_installation,
                                    bg="#27ae60", fg="white",
                                    font=("Arial", 12, "bold"),
                                    width=22, height=2,
                                    relief=tk.SOLID, bd=0,
                                    cursor="hand2")
        self.install_btn.pack(side=tk.LEFT, padx=(0, 15))

        self.close_btn = tk.Button(button_frame, text="Close",
                                  command=self.root.quit,
                                  width=15, height=2,
                                  relief=tk.SOLID, bd=1)
        self.close_btn.pack(side=tk.LEFT)
    
    def find_obs_directory(self):
        """Find OBS Studio scripts directory"""
        possible_paths = [
            os.path.expanduser("~/AppData/Roaming/obs-studio/scripts"),
            "C:/Program Files/obs-studio/data/obs-plugins",
            "C:/Program Files (x86)/obs-studio/data/obs-plugins"
        ]

        for path in possible_paths:
            if os.path.exists(path):
                default_path = os.path.join(path, "SmartClip_CZ")
                # Convert to Windows path format
                default_path = os.path.normpath(default_path)
                self.path_var.set(default_path)
                return

        # Fallback
        fallback_path = os.path.expanduser("~/SmartClip_CZ")
        fallback_path = os.path.normpath(fallback_path)
        self.path_var.set(fallback_path)
    
    def browse_path(self):
        """Browse for installation directory"""
        path = filedialog.askdirectory(title="Select Installation Directory")
        if path:
            # Convert to Windows path format
            path = os.path.normpath(path)
            self.path_var.set(path)
    
    def update_progress(self, value, status):
        """Update progress bar and status"""
        self.progress_var.set(value)
        self.status_var.set(status)
        self.root.update()
    
    def start_installation(self):
        """Start installation in separate thread"""
        self.install_btn.config(state=tk.DISABLED, text="Installing...", bg="#95a5a6")
        thread = threading.Thread(target=self.run_installation)
        thread.daemon = True
        thread.start()
    
    def run_installation(self):
        """Run the actual installation"""
        try:
            install_path = self.path_var.get()
            
            # Step 1: Create directories
            self.update_progress(10, "Creating installation directories...")
            os.makedirs(install_path, exist_ok=True)
            
            # Step 2: Copy SmartClip files
            self.update_progress(25, "Copying SmartClip CZ files...")
            self.copy_smartclip_files(install_path)
            
            # Step 3: Setup Python environment
            self.update_progress(45, "Setting up Python virtual environment...")
            venv_success, venv_python, system_python = self.setup_python_environment(install_path)

            # Step 4: Install packages
            self.update_progress(65, "Installing Python packages...")
            self.install_python_packages(install_path, venv_python)

            # Step 5: Create venv activation for OBS
            self.update_progress(75, "Setting up OBS Python environment...")
            self.create_venv_activation_script(install_path, venv_python)

            # Step 6: Download models
            self.update_progress(85, "Downloading AI models...")
            self.download_models(install_path)
            
            # Step 6: Create configuration
            self.update_progress(95, "Creating configuration files...")
            self.create_configuration(install_path)
            
            # Step 7: Complete
            self.update_progress(100, "Installation completed successfully!")
            
            self.show_completion_dialog(install_path, system_python)
            
        except Exception as e:
            error_msg = f"Installation failed: {str(e)}"
            messagebox.showerror("Installation Error", error_msg)
            self.status_var.set(error_msg)
            self.install_btn.config(state=tk.NORMAL, text="Install SmartClip CZ", bg="#27ae60")
    
    def get_startup_info(self):
        """Get startup info to hide subprocess windows"""
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            return startupinfo
        return None

    def copy_smartclip_files(self, install_path):
        """Copy SmartClip CZ files from bundled resources"""
        try:
            # Get bundled files from PyInstaller
            if hasattr(sys, '_MEIPASS'):
                bundle_dir = sys._MEIPASS
            else:
                bundle_dir = os.path.dirname(os.path.abspath(__file__))

            # Files to copy
            files_to_copy = [
                "smartclip_cz.py",
                "requirements.txt",
                "README.md"
            ]

            # Directories to copy
            dirs_to_copy = ["core", "detectors", "widgets"]

            # Copy files
            for file_name in files_to_copy:
                src = os.path.join(bundle_dir, file_name)
                if os.path.exists(src):
                    dst = os.path.join(install_path, file_name)
                    shutil.copy2(src, dst)

            # Copy directories
            for dir_name in dirs_to_copy:
                src = os.path.join(bundle_dir, dir_name)
                if os.path.exists(src):
                    dst = os.path.join(install_path, dir_name)
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)

        except Exception as e:
            raise Exception(f"Failed to copy SmartClip files: {e}")
    
    def find_existing_python_311(self, install_path=None):
        """Find existing Python 3.11.9 installation with comprehensive logging"""

        # Create detection log
        if install_path:
            detection_log = os.path.join(install_path, "python_detection_debug.log")
        else:
            detection_log = "python_detection_debug.log"

        def log_detection(message):
            try:
                with open(detection_log, 'a', encoding='utf-8') as f:
                    import datetime
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] {message}\n")
                    f.flush()
                print(message)
            except Exception as e:
                print(f"Detection logging error: {e}")

        try:
            log_detection("=== PYTHON 3.11.9 DETECTION DEBUG LOG ===")
            import subprocess
            import winreg

            # Check common Python installation locations
            possible_paths = [
                r"C:\Python311\python.exe",
                r"C:\Program Files\Python311\python.exe",
                r"C:\Program Files (x86)\Python311\python.exe",
                os.path.expanduser(r"~\AppData\Local\Programs\Python\Python311\python.exe"),
                os.path.expanduser(r"~\AppData\Local\Programs\Python\Python311-32\python.exe"),
            ]

            log_detection(f"Checking {len(possible_paths)} common installation paths...")

            # Check registry for Python installations (more comprehensive)
            registry_keys = [
                (winreg.HKEY_CURRENT_USER, r"Software\Python\PythonCore\3.11\InstallPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Python\PythonCore\3.11\InstallPath"),
                (winreg.HKEY_CURRENT_USER, r"Software\Python\PythonCore\3.11-32\InstallPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Python\PythonCore\3.11-32\InstallPath"),
                # Check for newer registry format
                (winreg.HKEY_CURRENT_USER, r"Software\Python\PythonCore\3.11.9\InstallPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Python\PythonCore\3.11.9\InstallPath"),
            ]

            log_detection("Checking Windows registry for Python installations...")
            for hive, key_path in registry_keys:
                try:
                    hive_name = "HKEY_CURRENT_USER" if hive == winreg.HKEY_CURRENT_USER else "HKEY_LOCAL_MACHINE"
                    log_detection(f"  Checking {hive_name}\\{key_path}")

                    with winreg.OpenKey(hive, key_path) as key:
                        install_path_reg = winreg.QueryValue(key, "")
                        python_path = os.path.join(install_path_reg, "python.exe")
                        possible_paths.append(python_path)
                        log_detection(f"    Found registry entry: {python_path}")
                except Exception as e:
                    log_detection(f"    Registry key not found: {e}")

            log_detection(f"Total paths to check: {len(possible_paths)}")

            # Check each possible path
            for i, python_path in enumerate(possible_paths, 1):
                log_detection(f"[{i}/{len(possible_paths)}] Checking: {python_path}")

                if os.path.exists(python_path):
                    log_detection(f"  ✓ File exists")
                    try:
                        # Verify it's Python 3.11.x
                        log_detection(f"  Testing Python version...")
                        result = subprocess.run([python_path, "--version"], capture_output=True, text=True, timeout=5,
                                               creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
                        log_detection(f"  Version check return code: {result.returncode}")
                        log_detection(f"  Version output: {result.stdout.strip()}")

                        if result.returncode == 0 and "Python 3.11" in result.stdout:
                            log_detection(f"  ✓ Python 3.11.x confirmed")

                            # Verify pip is available
                            log_detection(f"  Testing pip availability...")
                            pip_result = subprocess.run([python_path, "-m", "pip", "--version"], capture_output=True, timeout=5,
                                                       creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
                            log_detection(f"  Pip check return code: {pip_result.returncode}")

                            if pip_result.returncode == 0:
                                log_detection(f"  ✓ Pip confirmed working")
                                log_detection(f"✓ FOUND VALID PYTHON 3.11.9: {python_path}")
                                return python_path
                            else:
                                log_detection(f"  ✗ Pip not available")
                        else:
                            log_detection(f"  ✗ Not Python 3.11.x")
                    except Exception as e:
                        log_detection(f"  ✗ Error testing Python: {e}")
                else:
                    log_detection(f"  ✗ File does not exist")

            log_detection("✗ No valid Python 3.11.9 installation found")
            return None

        except Exception as e:
            log_detection(f"CRITICAL ERROR in Python detection: {e}")
            import traceback
            log_detection(f"Traceback: {traceback.format_exc()}")
            return None

    def download_and_install_python_311(self, install_path):
        """Download Python installer and run it normally (not silent)"""

        # Create Python installation log
        python_log = os.path.join(install_path, "python_installation_debug.log")

        def log_python(message):
            try:
                with open(python_log, 'a', encoding='utf-8') as f:
                    import datetime
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] {message}\n")
                    f.flush()
                print(message)
            except Exception as e:
                print(f"Python logging error: {e}")

        try:
            log_python("=== PYTHON INSTALLATION DEBUG LOG ===")
            log_python(f"Install path: {install_path}")

            self.update_progress(22, "Downloading Python 3.11.9 installer...")

            # Download to temp directory
            import tempfile
            temp_dir = tempfile.gettempdir()
            python_installer = os.path.join(temp_dir, "python-3.11.9-installer.exe")

            # Python 3.11.9 full installer URL
            python_url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
            log_python(f"Python installer URL: {python_url}")
            log_python(f"Python installer path: {python_installer}")

            try:
                log_python("Downloading Python installer...")
                import urllib.request
                urllib.request.urlretrieve(python_url, python_installer)
                log_python(f"Python installer downloaded: {os.path.exists(python_installer)}")
                log_python(f"Installer size: {os.path.getsize(python_installer) if os.path.exists(python_installer) else 'N/A'} bytes")

                # Show user dialog about Python installation
                import tkinter.messagebox as mb
                install_python = mb.askyesno(
                    "Python 3.11.9 Required",
                    "SmartClip CZ requires Python 3.11.9 which was not found on your system.\n\n"
                    "The Python installer will now open. Please:\n"
                    "1. DO NOT check 'Add Python to PATH' (to avoid conflicts)\n"
                    "2. Choose 'Install Now' or 'Customize installation'\n"
                    "3. Wait for installation to complete\n"
                    "4. Return to this installer\n\n"
                    "Note: Python will be installed without modifying your PATH to prevent conflicts with existing Python installations.\n\n"
                    "Do you want to proceed with Python installation?"
                )

                if not install_python:
                    log_python("User cancelled Python installation")
                    return None

                # Run Python installer normally (not silent)
                self.update_progress(24, "Running Python installer - please complete the installation...")
                log_python("Starting Python installer (normal mode)...")
                import subprocess

                # Run installer normally - user will see the GUI
                result = subprocess.run([python_installer], timeout=600)  # 10 minute timeout

                log_python(f"Python installer completed with return code: {result.returncode}")

                # Remove installer file
                try:
                    os.remove(python_installer)
                    log_python("Installer file removed")
                except:
                    log_python("Failed to remove installer file")

                # Now try to find the installed Python
                self.update_progress(25, "Detecting installed Python...")
                log_python("Searching for newly installed Python...")

                # Wait a moment for installation to settle
                import time
                time.sleep(2)

                # Find the installed Python
                python_exe = self.find_existing_python_311()

                if python_exe:
                    log_python(f"✓ Found Python 3.11.9 at: {python_exe}")
                    self.update_progress(25, "Python 3.11.9 detected successfully")
                    return python_exe
                else:
                    log_python("✗ Could not find Python 3.11.9 after installation")
                    mb.showerror("Python Not Found",
                               "Could not detect Python 3.11.9 after installation.\n"
                               "Please ensure Python 3.11.9 is properly installed and try again.")
                    return None

            except subprocess.TimeoutExpired:
                log_python("Python installer timed out")
                self.update_progress(25, "Python installation timed out")
                return None
            except Exception as e:
                log_python(f"CRITICAL ERROR during Python installation: {e}")
                import traceback
                log_python(f"Traceback: {traceback.format_exc()}")
                self.update_progress(25, f"Python installation failed: {str(e)}")
                return None

        except Exception as e:
            log_python(f"CRITICAL ERROR in Python download: {e}")
            import traceback
            log_python(f"Traceback: {traceback.format_exc()}")
            self.update_progress(25, f"Python download failed: {str(e)}")
            return None

    def setup_python_for_smartclip(self, install_path):
        """Setup Python for SmartClip - check existing or install new"""
        try:
            self.update_progress(20, "Checking for Python 3.11.9...")

            # First, try to find existing Python 3.11.9 with detailed logging
            existing_python = self.find_existing_python_311(install_path)

            if existing_python:
                self.update_progress(22, "Found existing Python 3.11.9")
                return existing_python
            else:
                # No existing Python found, need to install
                self.update_progress(22, "Python 3.11.9 not found - installation required")
                installed_python = self.download_and_install_python_311(install_path)

                if installed_python:
                    # Verify the installation was successful
                    verified_python = self.find_existing_python_311(install_path)
                    if verified_python:
                        self.update_progress(25, "Python 3.11.9 installation verified")
                        return verified_python
                    else:
                        self.update_progress(25, "Python installation could not be verified")
                        return None
                else:
                    return None

        except Exception as e:
            self.update_progress(25, f"Python setup failed: {str(e)}")
            return None


    def setup_python_environment(self, install_path):
        """Setup Python virtual environment using system or newly installed Python"""
        try:
            self.update_progress(20, "Setting up Python environment...")

            # Find or install Python 3.11.9
            system_python = self.setup_python_for_smartclip(install_path)

            if system_python and os.path.exists(system_python):
                # Create virtual environment using DOWNLOADED Python
                self.update_progress(25, "Creating virtual environment with downloaded Python...")
                venv_path = os.path.join(install_path, "venv")

                # Create debug log for venv creation
                venv_log = os.path.join(install_path, "venv_creation_debug.log")

                def log_venv(message):
                    try:
                        with open(venv_log, 'a', encoding='utf-8') as f:
                            import datetime
                            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            f.write(f"[{timestamp}] {message}\n")
                            f.flush()
                        print(message)
                    except Exception as e:
                        print(f"Venv logging error: {e}")

                log_venv("=== VENV CREATION DEBUG LOG ===")
                log_venv(f"System Python: {system_python}")
                log_venv(f"System Python exists: {os.path.exists(system_python)}")
                log_venv(f"Target venv path: {venv_path}")
                log_venv(f"Install path: {install_path}")

                # Use subprocess with system Python to create venv
                # This ensures the venv uses the system Python, not the installer's Python
                import subprocess

                try:
                    # Create venv using system Python - remove --with-pip as it's not supported
                    cmd = [system_python, "-m", "venv", venv_path]
                    log_venv(f"Running command: {' '.join(cmd)}")

                    result = subprocess.run(
                        cmd,
                        cwd=install_path,
                        capture_output=True,
                        text=True,
                        timeout=60,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    )

                    log_venv(f"Command return code: {result.returncode}")
                    log_venv(f"Command stdout: {result.stdout}")
                    log_venv(f"Command stderr: {result.stderr}")

                    if result.returncode == 0:
                        self.update_progress(29, "Virtual environment created successfully")
                        venv_python = os.path.join(venv_path, "Scripts", "python.exe")
                        log_venv(f"Expected venv Python: {venv_python}")
                        log_venv(f"Venv Python exists: {os.path.exists(venv_python)}")

                        if os.path.exists(venv_python):
                            # Ensure pip is available in the venv
                            log_venv("Installing pip to venv using ensurepip...")
                            try:
                                pip_cmd = [venv_python, "-m", "ensurepip", "--default-pip"]
                                pip_result = subprocess.run(pip_cmd, capture_output=True, timeout=30,
                                                          creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
                                log_venv(f"Pip installation result: {pip_result.returncode}")
                                log_venv(f"Pip installation stdout: {pip_result.stdout.decode('utf-8', errors='ignore')}")
                                log_venv(f"Pip installation stderr: {pip_result.stderr.decode('utf-8', errors='ignore')}")

                                if pip_result.returncode == 0:
                                    log_venv("✓ Pip installed successfully to venv")
                                else:
                                    log_venv("⚠ Pip installation failed, but continuing...")
                            except Exception as e:
                                log_venv(f"Pip installation failed: {e}")

                            # Verify pip is working in venv
                            try:
                                pip_test = subprocess.run([venv_python, "-m", "pip", "--version"],
                                                        capture_output=True, timeout=10,
                                                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
                                if pip_test.returncode == 0:
                                    log_venv("✓ Pip is working in venv")
                                else:
                                    log_venv("⚠ Pip test failed in venv")
                            except:
                                log_venv("⚠ Could not test pip in venv")

                            log_venv("✓ Venv creation successful")
                            self.update_progress(30, "Virtual environment with pip ready")
                            return True, venv_python, system_python
                        else:
                            raise Exception("Venv Python executable not found after creation")
                    else:
                        raise Exception(f"Venv creation failed: {result.stderr}")

                except Exception as e:
                    log_venv(f"Venv creation with subprocess failed: {str(e)}")
                    self.update_progress(28, f"Venv creation failed - using system Python directly")
                    # Fallback: return system Python directly if venv creation fails
                    log_venv("Using system Python directly as fallback")
                    return True, system_python, system_python
            else:
                # No downloaded Python - installation failed
                self.update_progress(25, "Downloaded Python not available - installation failed")
                self.update_progress(30, "Python installation failed - cannot create virtual environment")
                return False, None, None

        except Exception as e:
            self.update_progress(30, f"Python environment setup failed: {str(e)}")
            return False, None, None



    def create_venv_fallback_with_downloaded_python(self, install_path, downloaded_python):
        """Fallback: create proper venv structure that references downloaded Python (no copying)"""
        try:
            self.update_progress(28, "Creating venv structure that references downloaded Python...")

            venv_path = os.path.join(install_path, "venv")
            venv_scripts = os.path.join(venv_path, "Scripts")
            venv_lib = os.path.join(venv_path, "Lib")
            venv_site_packages = os.path.join(venv_lib, "site-packages")
            python_dir = os.path.dirname(downloaded_python)

            # Create directory structure (but DON'T copy Python binaries)
            os.makedirs(venv_scripts, exist_ok=True)
            os.makedirs(venv_site_packages, exist_ok=True)

            # Create pyvenv.cfg file that points to downloaded Python
            pyvenv_cfg = os.path.join(venv_path, "pyvenv.cfg")
            with open(pyvenv_cfg, 'w') as f:
                f.write(f"home = {python_dir}\n")
                f.write("include-system-site-packages = false\n")
                f.write("version = 3.11.9\n")
                f.write("executable = {}\n".format(downloaded_python.replace('\\', '/')))
                f.write("command = {} -m venv {}\n".format(downloaded_python.replace('\\', '/'), venv_path.replace('\\', '/')))

            # Create activation scripts that reference downloaded Python
            activate_bat = os.path.join(venv_scripts, "activate.bat")
            with open(activate_bat, 'w') as f:
                f.write(f'@echo off\n')
                f.write(f'set "VIRTUAL_ENV={venv_path}"\n')
                f.write(f'set "PATH={venv_scripts};%PATH%"\n')
                f.write(f'set "_OLD_VIRTUAL_PATH=%PATH%"\n')
                f.write(f'set "_OLD_VIRTUAL_PROMPT=%PROMPT%"\n')
                f.write(f'set "PROMPT=(venv) %PROMPT%"\n')

            # Create python.exe and pip.exe scripts that call downloaded Python
            venv_python_script = os.path.join(venv_scripts, "python.exe")
            venv_pip_script = os.path.join(venv_scripts, "pip.exe")

            # Instead of copying binaries, create batch files that call downloaded Python
            python_bat = os.path.join(venv_scripts, "python.bat")
            with open(python_bat, 'w') as f:
                f.write(f'@echo off\n')
                f.write(f'"{downloaded_python}" %*\n')

            pip_bat = os.path.join(venv_scripts, "pip.bat")
            with open(pip_bat, 'w') as f:
                f.write(f'@echo off\n')
                f.write(f'"{downloaded_python}" -m pip %*\n')

            # Ensure pip is available with downloaded Python
            try:
                self.update_progress(29, "Installing pip to downloaded Python...")
                pip_cmd = [downloaded_python, "-m", "ensurepip", "--default-pip"]
                subprocess.run(pip_cmd, capture_output=True, timeout=30,
                             creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            except Exception as e:
                # If ensurepip fails, try to use get-pip.py
                try:
                    import urllib.request
                    get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
                    get_pip_path = os.path.join(install_path, "get-pip.py")
                    urllib.request.urlretrieve(get_pip_url, get_pip_path)

                    pip_cmd = [downloaded_python, get_pip_path]
                    subprocess.run(pip_cmd, capture_output=True, timeout=60,
                                 creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)

                    # Clean up
                    os.unlink(get_pip_path)
                except:
                    pass  # pip installation failed, but continue

            # For package installation, we'll use downloaded Python directly
            # Return downloaded Python path, not venv python path
            if os.path.exists(downloaded_python):
                self.update_progress(30, "Venv structure created (references downloaded Python)")
                return True, downloaded_python  # Use downloaded Python for package installation
            else:
                return False, sys.executable

        except Exception as e:
            self.update_progress(30, f"Venv structure creation failed: {str(e)}")
            return False, sys.executable

    def create_venv_fallback(self, install_path):
        """Final fallback: create venv with current Python"""
        try:
            venv_path = os.path.join(install_path, "venv")

            # Use Python's venv module with current Python
            import venv
            venv_builder = venv.EnvBuilder(with_pip=True)
            venv_builder.create(venv_path)

            venv_python = os.path.join(venv_path, "Scripts", "python.exe")
            if os.path.exists(venv_python):
                # Copy venv python to /python/ directory for consistency
                python_dir = os.path.join(install_path, "python")
                os.makedirs(python_dir, exist_ok=True)
                target_python = os.path.join(python_dir, "python.exe")
                shutil.copy2(venv_python, target_python)

                return True, venv_python
            else:
                return False, sys.executable

        except Exception as e:
            self.update_progress(30, f"Final fallback venv creation failed: {str(e)}")
            return False, sys.executable

        except Exception as e:
            self.update_progress(30, f"Warning: Python environment setup failed: {str(e)}")
            return False, sys.executable
    
    def install_python_packages(self, install_path, venv_python):
        """Install required Python packages to virtual environment using existing requirements.txt"""
        try:
            self.update_progress(30, "Installing Python dependencies...")

            # Use the existing requirements.txt from the project
            source_requirements = os.path.join(os.path.dirname(__file__), "requirements.txt")
            target_requirements = os.path.join(install_path, "requirements.txt")

            # Copy the existing requirements.txt if it exists
            if os.path.exists(source_requirements):
                shutil.copy2(source_requirements, target_requirements)
                self.update_progress(32, "Using project requirements.txt...")
            else:
                # Fallback: create basic requirements.txt
                packages = [
                    "requests>=2.25.0",
                    "numpy>=1.19.0",
                    "scipy>=1.5.0",
                    "scikit-learn>=0.24.0",
                    "sounddevice>=0.4.0",
                    "librosa>=0.8.0",
                    "vosk>=0.3.30",
                    "opensmile>=2.0.0"
                ]

                with open(target_requirements, 'w') as f:
                    for package in packages:
                        f.write(f"{package}\n")
                self.update_progress(32, "Created fallback requirements.txt...")

            # Create a comprehensive installation batch file
            install_bat = os.path.join(install_path, "install_all_packages.bat")
            with open(install_bat, 'w') as f:
                f.write("@echo off\n")
                f.write("echo Installing SmartClip CZ packages to virtual environment...\n")
                f.write(f'cd /d "{install_path}"\n')
                f.write(f'"{venv_python}" -m pip install --upgrade pip\n')
                f.write(f'"{venv_python}" -m pip install -r requirements.txt --no-warn-script-location\n')
                f.write("echo Package installation completed!\n")
                f.write("pause\n")

            # Install packages using the downloaded Python binaries
            self.update_progress(35, "Installing packages using downloaded Python...")

            try:
                # Read requirements.txt to get package list
                with open(target_requirements, 'r') as f:
                    packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]

                # Use the downloaded Python to install packages
                downloaded_python = os.path.join(install_path, "python", "python.exe")

                # Create main log file
                main_log = os.path.join(install_path, "installer_main_debug.log")

                def log_main(message):
                    try:
                        with open(main_log, 'a', encoding='utf-8') as f:
                            import datetime
                            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            f.write(f"[{timestamp}] {message}\n")
                            f.flush()
                        print(message)
                    except Exception as e:
                        print(f"Main logging error: {e}")

                log_main("=== MAIN INSTALLER PACKAGE INSTALLATION ===")
                log_main(f"Install path: {install_path}")
                log_main(f"System Python path: {system_python if 'system_python' in locals() else 'Not available'}")
                log_main(f"Venv Python path: {venv_python}")
                log_main(f"Venv Python exists: {os.path.exists(venv_python) if venv_python else 'N/A - venv_python is None'}")
                log_main(f"Number of packages to install: {len(packages)}")
                log_main(f"Packages: {packages}")

                # Check if we have a valid Python installation (either venv or system)
                log_main(f"Checking Python installation validity...")
                log_main(f"venv_python value: {venv_python}")
                log_main(f"venv_python is not None: {venv_python is not None}")
                if venv_python:
                    log_main(f"venv_python exists on disk: {os.path.exists(venv_python)}")
                else:
                    log_main("venv_python is None")

                if venv_python and os.path.exists(venv_python):
                    log_main("✓ Valid venv Python found - calling install_packages_with_python")
                    log_main(f"About to call install_packages_with_python with:")
                    log_main(f"  install_path: {install_path}")
                    log_main(f"  venv_python: {venv_python}")
                    log_main(f"  packages: {packages}")

                    try:
                        success = self.install_packages_with_python(install_path, venv_python, packages)
                        log_main(f"install_packages_with_python returned: {success}")

                        if success:
                            self.update_progress(45, "All packages installed successfully!")
                            log_main("Package installation reported as successful")
                        else:
                            self.update_progress(45, "Some packages installed - check installation folder for details")
                            log_main("Package installation reported as failed/partial")
                    except Exception as e:
                        log_main(f"ERROR: Exception in install_packages_with_python: {e}")
                        import traceback
                        log_main(f"Traceback: {traceback.format_exc()}")
                        self.update_progress(45, "Package installation failed with error")
                else:
                    # No valid Python installation
                    log_main("✗ No valid Python installation found - cannot install packages")
                    log_main(f"Reason: venv_python={'None' if venv_python is None else venv_python}")
                    if venv_python:
                        log_main(f"File exists: {os.path.exists(venv_python)}")
                    self.update_progress(45, "Python installation failed - cannot install packages")
                    self.create_fallback_installers(install_path, None)

            except Exception as e:
                self.update_progress(45, f"Package installation error: {str(e)[:50]}...")

                # Create fallback batch file
                self.create_fallback_installers(install_path, venv_python)

            # Create user-friendly installation instructions
            install_info = os.path.join(install_path, "PACKAGE_INSTALLATION.txt")
            with open(install_info, 'w') as f:
                f.write("SmartClip CZ - Package Installation\n")
                f.write("=" * 40 + "\n\n")
                f.write("To install all required packages:\n")
                f.write("1. Double-click 'install_all_packages.bat'\n")
                f.write("2. Wait for installation to complete\n\n")
                f.write("Required packages:\n")
                for package in packages:
                    f.write(f"- {package}\n")
                f.write("\nAll packages will be installed to the virtual environment.\n")
                f.write("Basic functionality works with just requests and numpy.\n")

            return True

        except Exception as e:
            self.update_progress(45, f"Package installation failed: {str(e)}")
            return False

    def install_packages_with_python(self, install_path, python_exe, packages):
        """Install packages using subprocess with proper venv Python"""

        # Import modules first
        import sys
        import os
        import subprocess

        # Setup logging
        log_file = os.path.join(install_path, "package_installation_debug.log")

        def log_debug(message):
            try:
                with open(log_file, 'a', encoding='utf-8') as f:
                    import datetime
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] {message}\n")
                    f.flush()
                print(message)  # Also print to console
            except Exception as e:
                print(f"Logging error: {e}")

        try:
            log_debug("=== PACKAGE INSTALLATION DEBUG LOG ===")
            log_debug(f"Function called with parameters:")
            log_debug(f"  Install path: {install_path}")
            log_debug(f"  Python executable: {python_exe}")
            log_debug(f"  Packages to install: {packages}")
            log_debug(f"  Number of packages: {len(packages)}")

            # Verify Python executable exists
            if not os.path.exists(python_exe):
                log_debug(f"ERROR: Python executable does not exist: {python_exe}")
                return False

            # Test Python executable
            try:
                test_result = subprocess.run([python_exe, "--version"], capture_output=True, text=True, timeout=10,
                                            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
                log_debug(f"Python version test: {test_result.returncode}")
                log_debug(f"Python version: {test_result.stdout.strip()}")
                if test_result.returncode != 0:
                    log_debug(f"ERROR: Python executable test failed")
                    return False
            except Exception as e:
                log_debug(f"ERROR: Could not test Python executable: {e}")
                return False

            # Test pip availability
            try:
                pip_test = subprocess.run([python_exe, "-m", "pip", "--version"], capture_output=True, text=True, timeout=10,
                                         creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
                log_debug(f"Pip test result: {pip_test.returncode}")
                log_debug(f"Pip version: {pip_test.stdout.strip()}")
                if pip_test.returncode != 0:
                    log_debug(f"ERROR: Pip is not available in this Python")
                    return False
            except Exception as e:
                log_debug(f"ERROR: Could not test pip: {e}")
                return False

            # Create a debug batch file for manual testing
            debug_batch = os.path.join(install_path, "debug_package_install.bat")
            try:
                with open(debug_batch, 'w') as f:
                    f.write("@echo off\n")
                    f.write("echo SmartClip CZ Package Installation Debug\n")
                    f.write("echo ========================================\n")
                    f.write(f'echo Python executable: {python_exe}\n')
                    f.write(f'echo Python exists: {os.path.exists(python_exe)}\n')
                    f.write("echo.\n")
                    f.write(f'"{python_exe}" --version\n')
                    f.write("echo.\n")
                    f.write(f'"{python_exe}" -m pip --version\n')
                    f.write("echo.\n")
                    f.write("echo Installing packages...\n")
                    for package in packages:
                        f.write(f'echo Installing {package}...\n')
                        f.write(f'"{python_exe}" -m pip install {package} --no-warn-script-location --verbose\n')
                        f.write("echo.\n")
                    f.write("echo Installation completed!\n")
                    f.write("pause\n")
                log_debug(f"Created debug batch file: {debug_batch}")
            except Exception as e:
                log_debug(f"Could not create debug batch file: {e}")

            # Install packages using subprocess
            log_debug("Starting package installation using subprocess...")
            successful_packages = []
            failed_packages = []

            for i, package in enumerate(packages, 1):
                log_debug(f"[{i}/{len(packages)}] Installing package: {package}")
                self.update_progress(35 + (i * 10 // len(packages)), f"Installing {package}...")

                try:
                    # Use subprocess to install package with venv Python
                    install_cmd = [python_exe, "-m", "pip", "install", package, "--no-warn-script-location", "--verbose"]
                    log_debug(f"Running command: {' '.join(install_cmd)}")
                    log_debug(f"Working directory: {os.getcwd()}")
                    log_debug(f"Python executable exists: {os.path.exists(python_exe)}")
                    log_debug(f"Python executable path: {python_exe}")

                    # Test the Python executable first
                    try:
                        test_cmd = [python_exe, "--version"]
                        test_result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10,
                                                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
                        log_debug(f"Python version test: return_code={test_result.returncode}")
                        log_debug(f"Python version output: {test_result.stdout.strip()}")
                        if test_result.stderr:
                            log_debug(f"Python version stderr: {test_result.stderr.strip()}")
                    except Exception as e:
                        log_debug(f"ERROR: Could not test Python executable: {e}")
                        failed_packages.append(package)
                        continue

                    # Test pip availability
                    try:
                        pip_test_cmd = [python_exe, "-m", "pip", "--version"]
                        pip_test_result = subprocess.run(pip_test_cmd, capture_output=True, text=True, timeout=10,
                                                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
                        log_debug(f"Pip test: return_code={pip_test_result.returncode}")
                        log_debug(f"Pip version output: {pip_test_result.stdout.strip()}")
                        if pip_test_result.stderr:
                            log_debug(f"Pip test stderr: {pip_test_result.stderr.strip()}")
                        if pip_test_result.returncode != 0:
                            log_debug(f"ERROR: Pip is not working in this Python")
                            failed_packages.append(package)
                            continue
                    except Exception as e:
                        log_debug(f"ERROR: Could not test pip: {e}")
                        failed_packages.append(package)
                        continue

                    # Now try to install the package
                    log_debug(f"Starting package installation for: {package}")

                    # Hide all terminal windows for clean installation
                    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    log_debug(f"Using creation flags: {creation_flags} (hidden terminal)")

                    result = subprocess.run(
                        install_cmd,
                        capture_output=True,
                        text=True,
                        timeout=120,  # 2 minute timeout per package
                        creationflags=creation_flags,
                        cwd=os.path.dirname(python_exe)  # Set working directory to Python's directory
                    )

                    log_debug(f"Package {package} installation completed")
                    log_debug(f"Package {package} return code: {result.returncode}")
                    log_debug(f"Package {package} stdout length: {len(result.stdout)} chars")
                    log_debug(f"Package {package} stderr length: {len(result.stderr)} chars")

                    # Log stdout (truncated if too long)
                    if result.stdout:
                        stdout_lines = result.stdout.split('\n')
                        log_debug(f"Package {package} stdout (first 10 lines):")
                        for line in stdout_lines[:10]:
                            log_debug(f"  STDOUT: {line}")
                        if len(stdout_lines) > 10:
                            log_debug(f"  ... and {len(stdout_lines) - 10} more stdout lines")

                    # Log stderr (truncated if too long)
                    if result.stderr:
                        stderr_lines = result.stderr.split('\n')
                        log_debug(f"Package {package} stderr (first 10 lines):")
                        for line in stderr_lines[:10]:
                            log_debug(f"  STDERR: {line}")
                        if len(stderr_lines) > 10:
                            log_debug(f"  ... and {len(stderr_lines) - 10} more stderr lines")

                    if result.returncode == 0:
                        log_debug(f"✓ Package {package} installed successfully")
                        successful_packages.append(package)
                    else:
                        log_debug(f"✗ Package {package} installation failed with return code {result.returncode}")
                        failed_packages.append(package)

                except subprocess.TimeoutExpired as e:
                    log_debug(f"✗ Package {package} installation timed out after 120 seconds")
                    log_debug(f"Timeout details: {e}")
                    failed_packages.append(package)
                except Exception as e:
                    log_debug(f"✗ Package {package} installation error: {e}")
                    log_debug(f"Exception type: {type(e).__name__}")
                    import traceback
                    log_debug(f"Exception traceback: {traceback.format_exc()}")
                    failed_packages.append(package)

            # Summary
            log_debug("=== PACKAGE INSTALLATION SUMMARY ===")
            log_debug(f"Total packages: {len(packages)}")
            log_debug(f"Successful installations: {len(successful_packages)}")
            log_debug(f"Failed installations: {len(failed_packages)}")

            if successful_packages:
                log_debug("✓ Successfully installed packages:")
                for pkg in successful_packages:
                    log_debug(f"  - {pkg}")

            if failed_packages:
                log_debug("✗ Failed to install packages:")
                for pkg in failed_packages:
                    log_debug(f"  - {pkg}")

            # Verify installations
            log_debug("=== INSTALLATION VERIFICATION ===")
            verified_packages = []
            for package in successful_packages:
                package_name = package.split('>=')[0].split('==')[0].split('[')[0]
                try:
                    verify_cmd = [python_exe, "-c", f"import {package_name}; print(f'{package_name} imported successfully')"]
                    verify_result = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=10,
                                                  creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
                    if verify_result.returncode == 0:
                        log_debug(f"✓ {package_name} import verification successful")
                        verified_packages.append(package_name)
                    else:
                        log_debug(f"✗ {package_name} import verification failed: {verify_result.stderr}")
                except Exception as e:
                    log_debug(f"✗ {package_name} verification error: {e}")

            log_debug(f"Verified packages: {len(verified_packages)}/{len(successful_packages)}")

            # Return success if at least some packages were installed
            success = len(successful_packages) > 0
            log_debug(f"Overall installation success: {success}")
            return success

        except Exception as e:
            log_debug(f"CRITICAL ERROR in package installation: {e}")
            import traceback
            log_debug(f"Traceback: {traceback.format_exc()}")
            return False

    def create_venv_activation_script(self, install_path, venv_python):
        """Create a script that modifies smartclip_cz.py to use venv packages"""
        try:
            import os
            import sys

            # Get venv site-packages path
            if venv_python and os.path.exists(venv_python):
                venv_dir = os.path.dirname(os.path.dirname(venv_python))
                venv_site_packages = os.path.join(venv_dir, "Lib", "site-packages")
            else:
                # Fallback to manual venv path
                venv_site_packages = os.path.join(install_path, "venv", "Lib", "site-packages")

            # Read the original smartclip_cz.py
            smartclip_path = os.path.join(install_path, "smartclip_cz.py")
            if not os.path.exists(smartclip_path):
                return

            with open(smartclip_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if venv activation is already present
            if "Auto-generated venv activation for OBS" in content:
                print("✓ Venv activation already present in smartclip_cz.py")
                return

            # Add venv path to sys.path at the beginning of the script
            venv_activation_lines = [
                "# Auto-generated venv activation for OBS",
                "import sys",
                "import os",
                "",
                "# Add venv site-packages to Python path",
                f'venv_site_packages = r"{venv_site_packages}"',
                "if os.path.exists(venv_site_packages) and venv_site_packages not in sys.path:",
                "    sys.path.insert(0, venv_site_packages)",
                '    print(f"SmartClip CZ: Added venv packages from {venv_site_packages}")',
                ""
            ]

            # Insert the activation code at the very beginning of the file
            lines = content.split('\n')

            # Insert each line at the beginning
            for i, line in enumerate(venv_activation_lines):
                lines.insert(i, line)

            # Write the modified content back
            modified_content = '\n'.join(lines)
            with open(smartclip_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)

            print(f"✓ Added venv activation to smartclip_cz.py")

        except Exception as e:
            print(f"Error creating venv activation script: {e}")

    def get_clean_environment(self):
        """Get a clean environment for subprocess calls"""
        import os

        # Create clean environment without installer-specific variables
        env = {
            'PATH': os.environ.get('PATH', ''),
            'SYSTEMROOT': os.environ.get('SYSTEMROOT', ''),
            'TEMP': os.environ.get('TEMP', ''),
            'TMP': os.environ.get('TMP', ''),
        }

        return env

    def open_installation_folder(self, install_path):
        """Open the installation folder in Windows Explorer"""
        try:
            import os
            import subprocess

            # Use Windows Explorer to open folder - this is safe and won't cause multiple instances
            subprocess.run(['explorer', install_path], check=False)

        except Exception as e:
            print(f"Failed to open installation folder: {e}")

    def create_fallback_installers(self, install_path, venv_python):
        """Create fallback installation scripts"""
        try:
            # Create batch file
            install_bat = os.path.join(install_path, "install_all_packages.bat")
            with open(install_bat, 'w') as f:
                f.write("@echo off\n")
                f.write("echo Installing SmartClip CZ packages to virtual environment...\n")
                f.write(f'cd /d "{install_path}"\n')
                f.write(f'"{venv_python}" -m pip install --upgrade pip\n')
                f.write(f'"{venv_python}" -m pip install -r requirements.txt --no-warn-script-location\n')
                f.write("echo Package installation completed!\n")
                f.write("pause\n")

        except Exception as e:
            print(f"Failed to create fallback installers: {e}")
    
    def download_models(self, install_path):
        """Download Vosk models for Czech and English"""
        try:
            self.update_progress(50, "Setting up Vosk models...")

            models_dir = os.path.join(install_path, "models")
            os.makedirs(models_dir, exist_ok=True)

            # Model configurations
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

            downloaded_count = 0
            for i, model in enumerate(models_to_download):
                try:
                    progress = 50 + (i * 20 // len(models_to_download))
                    self.update_progress(progress, f"Downloading {model['name']} model...")

                    model_dir = os.path.join(models_dir, model["dir_name"])

                    # Skip if already exists
                    if os.path.exists(model_dir):
                        downloaded_count += 1
                        continue

                    # Download and extract
                    if self.download_and_extract_model(model["url"], models_dir, model["dir_name"]):
                        downloaded_count += 1
                    elif model["required"]:
                        self.update_progress(progress, f"Failed to download required {model['name']} model")

                except Exception:
                    continue

            if downloaded_count > 0:
                self.update_progress(70, f"Vosk models ready ({downloaded_count}/{len(models_to_download)} downloaded)")
                return True
            else:
                self.update_progress(70, "Warning: No models downloaded - manual setup required")
                return False

        except Exception as e:
            self.update_progress(70, f"Model download failed: {str(e)}")
            return False

    def download_and_extract_model(self, url, models_dir, expected_dir_name):
        """Download and extract a Vosk model"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                tmp_path = tmp_file.name

            # Download with timeout
            urllib.request.urlretrieve(url, tmp_path)

            # Extract
            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                zip_ref.extractall(models_dir)

            # Cleanup
            os.unlink(tmp_path)

            # Verify extraction
            expected_path = os.path.join(models_dir, expected_dir_name)
            return os.path.exists(expected_path)

        except Exception:
            return False

    def setup_twitch_oauth(self, install_path):
        """Automatic Twitch OAuth setup with local server"""

        # Setup OAuth logging
        oauth_log = os.path.join(install_path, "oauth_setup_debug.log")

        def log_oauth(message):
            try:
                with open(oauth_log, 'a', encoding='utf-8') as f:
                    import datetime
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] {message}\n")
                    f.flush()
                print(message)
            except Exception as e:
                print(f"OAuth logging error: {e}")

        try:
            log_oauth("=== TWITCH OAUTH SETUP DEBUG LOG ===")
            log_oauth(f"Install path: {install_path}")
            log_oauth("Starting Twitch OAuth setup process...")

            self.update_progress(75, "Setting up Twitch OAuth...")

            # Check if user wants to setup OAuth now
            log_oauth("Showing OAuth setup confirmation dialog...")
            setup_oauth = messagebox.askyesno(
                "Twitch OAuth Setup",
                "Would you like to set up Twitch OAuth credentials now?\n\n"
                "This will automatically configure Twitch API access for clip creation.\n"
                "You can also set this up later by editing the config file."
            )
            log_oauth(f"User OAuth setup choice: {setup_oauth}")

            if not setup_oauth:
                log_oauth("User chose to skip OAuth setup")
                self.update_progress(80, "Skipping Twitch OAuth setup")
                return "", "", "", "", ""

            # Step 1: Get Client ID
            log_oauth("Starting Client ID collection process...")
            self.update_progress(76, "Opening Twitch Developer Console...")

            try:
                log_oauth("Opening Twitch Developer Console in browser...")
                import webbrowser
                import time
                webbrowser.open("https://dev.twitch.tv/console/apps")
                time.sleep(2)
                log_oauth("Browser opened successfully")
            except Exception as e:
                log_oauth(f"Failed to open browser: {e}")

            log_oauth("Creating Client ID input dialog...")
            client_id_dialog = tk.Toplevel(self.root)
            client_id_dialog.title("Twitch Client ID")
            client_id_dialog.geometry("600x450")
            client_id_dialog.transient(self.root)
            client_id_dialog.grab_set()
            log_oauth("Client ID dialog created and configured")

            # Instructions for Client ID
            instructions = tk.Label(client_id_dialog,
                text="Step 1: Create Twitch Application & Get Credentials",
                font=("Arial", 14, "bold"))
            instructions.pack(pady=10)

            steps_text = ("1. In the Twitch Developer Console (opened in browser):\n" +
                         "   • Click 'Register Your Application' or 'Create an App'\n" +
                         "   • Name: 'SmartClip CZ' (or any name you prefer)\n" +
                         "   • OAuth Redirect URLs: 'http://localhost:3000' (without / at the end!)\n" +
                         "   • Category: 'Application Integration'\n" +
                         "   • Click 'Create'\n\n" +
                         "2. From your application details:\n" +
                         "   • Copy the 'Client ID' (always visible)\n" +
                         "3. Paste your Client ID below to continue:")

            steps_label = tk.Label(client_id_dialog, text=steps_text, justify=tk.LEFT, wraplength=550)
            steps_label.pack(pady=10, padx=20)

            # Client ID input
            tk.Label(client_id_dialog, text="Paste your Client ID here:", font=("Arial", 10, "bold")).pack(pady=(20,5))
            client_id_var = tk.StringVar()
            client_id_entry = tk.Entry(client_id_dialog, textvariable=client_id_var, width=60, font=("Arial", 10))
            client_id_entry.pack(pady=5)
            client_id_entry.focus()

            # Buttons
            button_frame = tk.Frame(client_id_dialog)
            button_frame.pack(pady=20)

            def continue_oauth():
                log_oauth("User clicked Continue button")
                if client_id_var.get().strip():
                    log_oauth(f"Client ID provided: [PRESENT - {len(client_id_var.get().strip())} chars]")
                    client_id_dialog.destroy()
                else:
                    log_oauth("No Client ID provided - showing warning")
                    messagebox.showwarning("Missing Client ID", "Please enter your Client ID to continue.")

            def skip_oauth():
                log_oauth("User clicked Skip OAuth Setup button")
                client_id_var.set("")
                client_id_dialog.destroy()

            tk.Button(button_frame, text="Continue", command=continue_oauth, bg="#27ae60", fg="white", font=("Arial", 10, "bold"), width=12, height=2).pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Skip OAuth Setup", command=skip_oauth, font=("Arial", 10), width=15, height=2).pack(side=tk.LEFT, padx=5)

            # Wait for dialog
            log_oauth("Waiting for user input on Client ID dialog...")
            client_id_dialog.wait_window()
            log_oauth("Client ID dialog closed")

            client_id = client_id_var.get().strip()
            log_oauth(f"Final Client ID: {'[PRESENT]' if client_id else '[EMPTY]'}")

            if not client_id:
                log_oauth("No Client ID - skipping OAuth setup")
                self.update_progress(80, "Skipping Twitch OAuth setup")
                return "", "", "", "", ""

            # Step 1.5: Get Client Secret (optional but recommended)
            log_oauth("Starting Client Secret collection process...")
            self.update_progress(77, "Collecting Client Secret for token refresh...")

            client_secret_dialog = tk.Toplevel(self.root)
            client_secret_dialog.title("Twitch Client Secret (Optional)")
            client_secret_dialog.geometry("600x400")
            client_secret_dialog.transient(self.root)
            client_secret_dialog.grab_set()

            # Instructions for Client Secret
            instructions = tk.Label(client_secret_dialog,
                text="Step 2: Client Secret (Recommended for Auto-Refresh)",
                font=("Arial", 14, "bold"))
            instructions.pack(pady=10)

            secret_text = ("For automatic token refresh (prevents expiration issues):\n\n" +
                          "1. In your Twitch application details:\n" +
                          "   • Click 'New Secret' button\n" +
                          "   • Copy the Client Secret immediately (shown only once!)\n" +
                          "   • Paste it below\n\n" +
                          "2. If you skip this step:\n" +
                          "   • Tokens will expire every ~4 hours\n" +
                          "   • You'll need to manually refresh them\n\n" +
                          "Paste your Client Secret below to continue:")

            secret_label = tk.Label(client_secret_dialog, text=secret_text, justify=tk.LEFT, wraplength=550)
            secret_label.pack(pady=10, padx=20)

            # Client Secret input
            client_secret_var = tk.StringVar()
            client_secret_entry = tk.Entry(client_secret_dialog, textvariable=client_secret_var, width=60, font=("Arial", 10), show="*")
            client_secret_entry.pack(pady=5)
            client_secret_entry.focus()

            # Buttons
            secret_button_frame = tk.Frame(client_secret_dialog)
            secret_button_frame.pack(pady=20)

            def continue_with_secret():
                log_oauth(f"Client Secret provided: {'[PRESENT]' if client_secret_var.get().strip() else '[EMPTY]'}")
                client_secret_dialog.destroy()

            def skip_secret():
                log_oauth("User chose to skip Client Secret")
                client_secret_var.set("")
                client_secret_dialog.destroy()

            tk.Button(secret_button_frame, text="Continue", command=continue_with_secret, bg="#27ae60", fg="white", font=("Arial", 10, "bold"), width=12, height=2).pack(side=tk.LEFT, padx=5)
            tk.Button(secret_button_frame, text="Skip (Not Recommended)", command=skip_secret, font=("Arial", 10), width=20, height=2).pack(side=tk.LEFT, padx=5)

            # Wait for dialog
            log_oauth("Waiting for user input on Client Secret dialog...")
            client_secret_dialog.wait_window()
            log_oauth("Client Secret dialog closed")

            client_secret = client_secret_var.get().strip()
            log_oauth(f"Final Client Secret: {'[PRESENT]' if client_secret else '[EMPTY]'}")

            # Step 2: Automatic OAuth Token Generation with timeout
            log_oauth("Starting automatic OAuth token generation...")
            self.update_progress(78, "Starting automatic OAuth token generation...")

            try:
                # Add timeout protection to prevent hanging
                log_oauth("Setting up OAuth thread with timeout protection...")
                import threading
                import time

                oauth_result = [None, None, None]  # [oauth_token, broadcaster_id, refresh_token]
                oauth_error = [None]
                oauth_status = ["starting"]  # Track OAuth progress

                def oauth_thread():
                    print("=== OAUTH THREAD STARTED ===")
                    try:
                        print("OAuth thread: About to call log_oauth...")
                        log_oauth("OAuth thread started - calling get_oauth_token_automatic...")
                        print("OAuth thread: Setting status to running...")
                        oauth_status[0] = "running"
                        print("OAuth thread: About to call get_oauth_token_automatic...")
                        token, broadcaster, refresh_token = self.get_oauth_token_automatic(client_id, client_secret, install_path)
                        print(f"OAuth thread: get_oauth_token_automatic returned - token: {'[PRESENT]' if token else '[NONE]'}")
                        oauth_status[0] = "completed"
                        log_oauth(f"OAuth thread completed - token: {'[PRESENT]' if token else '[NONE]'}, broadcaster: {'[PRESENT]' if broadcaster else '[NONE]'}")
                        oauth_result[0] = token
                        oauth_result[1] = broadcaster
                        oauth_result[2] = refresh_token
                        print("OAuth thread: Results stored successfully")
                    except Exception as e:
                        print(f"OAuth thread: EXCEPTION OCCURRED: {e}")
                        oauth_status[0] = "error"
                        log_oauth(f"OAuth thread error: {e}")
                        oauth_error[0] = str(e)
                        import traceback
                        log_oauth(f"OAuth thread traceback: {traceback.format_exc()}")
                        print(f"OAuth thread: Exception logged")

                # Start OAuth in separate thread with timeout
                log_oauth("Starting OAuth thread...")
                thread = threading.Thread(target=oauth_thread)
                thread.daemon = True
                thread.start()

                # Wait for OAuth with status monitoring (max 300 seconds)
                log_oauth("Waiting for OAuth thread to complete (300 second timeout)...")
                log_oauth(f"Initial OAuth status: {oauth_status[0]}")

                # Check status every 5 seconds
                for i in range(60):  # 6 * 5 = 300 seconds
                    thread.join(timeout=5)
                    log_oauth(f"OAuth status check {i+1}/60: {oauth_status[0]}")
                    log_oauth(f"Thread alive: {thread.is_alive()}")

                    if not thread.is_alive():
                        log_oauth("OAuth thread completed before timeout")
                        break

                    if oauth_status[0] in ["completed", "error"]:
                        log_oauth(f"OAuth thread finished with status: {oauth_status[0]}")
                        break

                if thread.is_alive():
                    # OAuth is taking too long, skip it
                    log_oauth("OAuth thread timed out after 300 seconds")
                    self.update_progress(80, "OAuth setup timed out - continuing without credentials")

                    # Try to force cleanup
                    try:
                        log_oauth("Attempting to cleanup OAuth resources...")
                        # The thread will continue running but we'll ignore it
                    except:
                        pass

                    return "", "", ""
                elif oauth_error[0]:
                    log_oauth(f"OAuth thread returned error: {oauth_error[0]}")
                    self.update_progress(80, f"OAuth setup error: {oauth_error[0]} - continuing without credentials")
                    return "", "", "", "", ""
                elif oauth_result[0] and oauth_result[1]:
                    log_oauth("OAuth setup completed successfully")
                    self.update_progress(80, "Twitch OAuth setup completed successfully")
                    return client_id, client_secret, oauth_result[0], oauth_result[2] or "", oauth_result[1]
                else:
                    log_oauth("OAuth setup failed - no token or broadcaster ID received")
                    self.update_progress(80, "OAuth setup failed - continuing without credentials")
                    return "", "", "", "", ""

            except Exception as e:
                self.update_progress(80, f"OAuth setup error: {str(e)} - continuing without credentials")
                return "", "", "", "", ""

        except Exception as e:
            self.update_progress(80, f"OAuth setup failed: {str(e)}")
            return "", "", "", "", ""

    def get_oauth_token_automatic(self, client_id, client_secret, install_path=None):
        """Get OAuth token automatically using local server with comprehensive logging
        Returns: (access_token, broadcaster_id, refresh_token)
        """

        # IMMEDIATE LOGGING - First thing to do
        print("=== OAUTH TOKEN GENERATION STARTED ===")
        print(f"get_oauth_token_automatic called with client_id: {'[PRESENT]' if client_id else '[MISSING]'}")

        import socket
        import threading
        import time
        import os

        # Create OAuth-specific log in install directory if available
        if install_path and os.path.exists(install_path):
            oauth_token_log = os.path.join(install_path, "oauth_token_debug.log")
        else:
            oauth_token_log = "oauth_token_debug.log"

        def log_token(message):
            try:
                with open(oauth_token_log, 'a', encoding='utf-8') as f:
                    import datetime
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] {message}\n")
                    f.flush()
                print(f"OAuth Token: {message}")
            except Exception as e:
                print(f"OAuth token logging error: {e}")

        try:
            log_token("=== OAUTH TOKEN GENERATION DEBUG LOG ===")
            log_token(f"Method started successfully")
            log_token(f"Current working directory: {os.getcwd()}")
            log_token(f"Client ID: {'[PRESENT]' if client_id else '[MISSING]'}")
            log_token(f"Client ID length: {len(client_id) if client_id else 0}")

            # Start local server for OAuth callback
            server = None
            server_thread = None

            # Check if port is available first
            def is_port_available(port):
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.bind(('localhost', port))
                        return True
                except:
                    return False

            # Find available port (use 3000 first, then fallback)
            ports_to_try = [3000, 8080, 8081, 8082, 8083, 8084]
            port = None

            log_token("Checking for available ports...")
            for test_port in ports_to_try:
                log_token(f"Testing port {test_port}...")
                if is_port_available(test_port):
                    port = test_port
                    log_token(f"✓ Port {port} is available")
                    break
                else:
                    log_token(f"✗ Port {test_port} is in use")

            if port is None:
                raise Exception("No available ports for OAuth callback server")

            oauth_token = None
            broadcaster_id = None

            try:
                log_token(f"Starting HTTP server on localhost:{port}...")
                # Use the found available port
                server = HTTPServer(('localhost', port), OAuthCallbackHandler)
                server.oauth_token = None
                server.refresh_token = None
                server.client_id = client_id
                server.client_secret = client_secret
                server.install_path = install_path  # Pass install path for logging
                server_thread = threading.Thread(target=server.serve_forever)
                server_thread.daemon = True
                server_thread.start()
                log_token("✓ HTTP server started successfully")

                # Generate OAuth URL with correct port
                scopes = "clips:edit user:read:email channel:read:subscriptions"
                redirect_uri = f"http://localhost:{port}"
                # Use authorization code flow if client_secret is available, otherwise fallback to implicit
                response_type = "code" if client_secret else "token"
                oauth_url = (
                    f"https://id.twitch.tv/oauth2/authorize?"
                    f"client_id={client_id}&"
                    f"redirect_uri={redirect_uri}&"
                    f"response_type={response_type}&"
                    f"scope={urllib.parse.quote(scopes)}"
                )

                log_token(f"Generated OAuth URL with redirect_uri: {redirect_uri}")
                log_token("OAuth URL ready for browser")

                # Show authorization dialog
                log_token("Creating Twitch authorization dialog...")
                auth_dialog = tk.Toplevel(self.root)
                auth_dialog.title("Twitch Authorization")
                auth_dialog.geometry("500x300")
                auth_dialog.transient(self.root)
                auth_dialog.grab_set()
                log_token("Authorization dialog created and configured")

                tk.Label(auth_dialog, text="Step 2: Authorize SmartClip CZ",
                        font=("Arial", 14, "bold")).pack(pady=10)

                tk.Label(auth_dialog,
                        text="1. Click 'Open Authorization Page' below\n" +
                             "2. In your browser, click 'Authorize' to grant permissions\n" +
                             "3. Wait for the success message\n" +
                             "4. Return to this installer",
                        justify=tk.LEFT).pack(pady=10, padx=20)

                def open_auth():
                    try:
                        log_token("Opening OAuth URL in browser...")
                        log_token(f"OAuth URL: {oauth_url}")
                        webbrowser.open(oauth_url)
                        log_token("✓ Browser opened successfully")
                    except Exception as e:
                        log_token(f"✗ Failed to open browser: {e}")
                        messagebox.showerror("Error", f"Could not open browser. Please visit:\n{oauth_url}")

                tk.Button(auth_dialog, text="Open Authorization Page",
                         command=open_auth, bg="#9146ff", fg="white",
                         font=("Arial", 12, "bold")).pack(pady=10)

                status_label = tk.Label(auth_dialog, text="Waiting for authorization...",
                                       font=("Arial", 10))
                status_label.pack(pady=10)

                # Improved timeout mechanism with periodic checks
                start_time = time.time()
                timeout_seconds = 300
                check_interval = 1000  # milliseconds

                # Use a flag to track if dialog should close
                dialog_should_close = [False]

                def check_token():
                    try:
                        log_token(f"=== TOKEN CHECK CYCLE ===")
                        log_token(f"Dialog should close: {dialog_should_close[0]}")

                        if dialog_should_close[0]:
                            log_token("Dialog is already closing - returning")
                            return  # Dialog is already closing

                        current_time = time.time()
                        elapsed = current_time - start_time
                        log_token(f"Elapsed time: {elapsed:.1f}s")

                        # Check server status
                        log_token(f"Server exists: {server is not None}")
                        if server:
                            log_token(f"Server oauth_token: {'[PRESENT]' if server.oauth_token else '[NONE]'}")
                            if server.oauth_token:
                                log_token(f"Token length: {len(server.oauth_token)}")

                        if server and server.oauth_token:
                            # Success - close dialog immediately
                            log_token("✓ OAuth token received - closing dialog")
                            log_token(f"Refresh token: {'[PRESENT]' if getattr(server, 'refresh_token', None) else '[NONE]'}")
                            dialog_should_close[0] = True
                            status_label.config(text="Authorization successful!", fg="green")
                            auth_dialog.update()  # Force UI update
                            # Close dialog immediately without after() to prevent hanging
                            try:
                                auth_dialog.destroy()
                                log_token("✓ Dialog destroyed successfully")
                            except Exception as e:
                                log_token(f"Error destroying dialog: {e}")
                            return

                        if elapsed >= timeout_seconds:
                            # Timeout - close dialog safely
                            log_token(f"✗ OAuth timeout after {elapsed:.1f}s")
                            dialog_should_close[0] = True
                            status_label.config(text="Authorization timed out", fg="red")
                            auth_dialog.update()  # Force UI update
                            # Use safe destroy with delay for user to see message
                            auth_dialog.after(1500, lambda: self.safe_destroy_dialog(auth_dialog))
                            return

                        # Update progress
                        remaining = int(timeout_seconds - elapsed)
                        status_label.config(text=f"Waiting for authorization... ({remaining}s remaining)")
                        log_token(f"Waiting... {remaining}s remaining")

                        # Schedule next check
                        auth_dialog.after(check_interval, check_token)
                        log_token("Next token check scheduled")

                    except Exception as e:
                        # Error - close dialog safely
                        log_token(f"✗ CRITICAL ERROR in check_token: {e}")
                        import traceback
                        log_token(f"Traceback: {traceback.format_exc()}")
                        dialog_should_close[0] = True
                        self.safe_destroy_dialog(auth_dialog)

                # Start checking for token
                log_token("Starting token check cycle...")
                auth_dialog.after(check_interval, check_token)

                # Add skip button to prevent hanging
                def skip_oauth():
                    try:
                        log_token("Skip OAuth button clicked")
                        auth_dialog.destroy()
                        log_token("Dialog destroyed via skip button")
                    except Exception as e:
                        log_token(f"Error in skip_oauth: {e}")

                tk.Button(auth_dialog, text="Skip OAuth Setup",
                         command=skip_oauth, bg="#e74c3c", fg="white",
                         font=("Arial", 10)).pack(pady=5)

                # Wait for dialog with timeout protection
                log_token("About to call auth_dialog.wait_window() - THIS MAY HANG")
                try:
                    auth_dialog.wait_window()
                    log_token("auth_dialog.wait_window() completed normally")
                except Exception as e:
                    log_token(f"auth_dialog.wait_window() failed: {e}")

                log_token("Finished waiting for dialog")

                log_token("Retrieving OAuth tokens from server...")
                oauth_token = server.oauth_token if server else None
                refresh_token = getattr(server, 'refresh_token', None) if server else None
                log_token(f"Retrieved access token: {'[PRESENT]' if oauth_token else '[NONE]'}")
                log_token(f"Retrieved refresh token: {'[PRESENT]' if refresh_token else '[NONE]'}")

                if oauth_token:
                    log_token("Getting broadcaster ID...")
                    # Get broadcaster ID with timeout protection
                    try:
                        broadcaster_id = self.get_broadcaster_id(client_id, oauth_token)
                        log_token(f"Broadcaster ID: {'[PRESENT]' if broadcaster_id else '[NONE]'}")
                    except Exception as e:
                        log_token(f"Error getting broadcaster ID: {e}")
                        broadcaster_id = None
                else:
                    log_token("No token available - skipping broadcaster ID")
                    broadcaster_id = None

            finally:
                # Clean up server and dialog with timeout protection
                log_token("Starting cleanup process...")
                try:
                    if auth_dialog:
                        log_token("Destroying auth dialog...")
                        auth_dialog.destroy()
                        log_token("✓ Auth dialog destroyed")
                except Exception as e:
                    log_token(f"Error destroying auth dialog: {e}")

                try:
                    if server:
                        log_token("Shutting down HTTP server...")
                        # Use a separate thread to shutdown server to prevent hanging
                        def shutdown_server():
                            try:
                                server.shutdown()
                                server.server_close()
                            except:
                                pass

                        shutdown_thread = threading.Thread(target=shutdown_server)
                        shutdown_thread.daemon = True
                        shutdown_thread.start()
                        shutdown_thread.join(timeout=2)  # Wait max 2 seconds
                        log_token("✓ HTTP server shutdown initiated")
                except Exception as e:
                    log_token(f"Error shutting down server: {e}")

                try:
                    if server_thread and server_thread.is_alive():
                        log_token("Joining server thread...")
                        server_thread.join(timeout=1)
                        if server_thread.is_alive():
                            log_token("⚠ Server thread still alive after timeout")
                        else:
                            log_token("✓ Server thread joined")
                except Exception as e:
                    log_token(f"Error joining server thread: {e}")

                log_token("Cleanup completed")

            log_token(f"OAuth process completed - returning results")
            log_token(f"Final access token: {'[PRESENT]' if oauth_token else '[NONE]'}")
            log_token(f"Final refresh token: {'[PRESENT]' if refresh_token else '[NONE]'}")
            log_token(f"Final broadcaster ID: {'[PRESENT]' if broadcaster_id else '[NONE]'}")
            return oauth_token, broadcaster_id, refresh_token or ""

        except Exception as e:
            messagebox.showerror("OAuth Error", f"OAuth setup failed: {str(e)}")
            return None, None

    def safe_destroy_dialog(self, dialog):
        """Safely destroy a dialog without causing hanging"""
        try:
            if dialog and dialog.winfo_exists():
                dialog.destroy()  # Just destroy, don't quit mainloop
        except Exception:
            pass  # Ignore errors during dialog destruction

    def get_broadcaster_id(self, client_id, oauth_token):
        """Get broadcaster ID from Twitch API"""
        try:
            headers = {
                'Authorization': f'Bearer {oauth_token}',
                'Client-Id': client_id
            }

            response = requests.get('https://api.twitch.tv/helix/users', headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('data') and len(data['data']) > 0:
                    return data['data'][0]['id']

            return None

        except Exception:
            return None

    def create_configuration(self, install_path):
        """Create default configuration file"""
        try:
            self.update_progress(85, "Creating configuration...")

            # Get OAuth credentials
            client_id, client_secret, oauth_token, refresh_token, broadcaster_id = self.setup_twitch_oauth(install_path)

            config = {
                "enabled_emotions": ["laughter", "excitement", "surprise", "joy"],
                "emotion_sensitivity": 0.7,
                "activation_phrases": [
                    "skvělé", "wow", "úžasné", "perfektní", "bomba", "super", "fantastické"
                ],
                "english_activation_phrases": [
                    "that's amazing", "awesome", "incredible", "fantastic", "wow",
                    "what the hell", "that's insane", "unbelievable", "holy shit",
                    "that's crazy", "amazing", "perfect", "excellent"
                ],
                "audio_sources": ["Desktop Audio"],
                "twitch_client_id": client_id,
                "twitch_client_secret": client_secret,
                "twitch_oauth_token": oauth_token,
                "twitch_refresh_token": refresh_token,
                "twitch_broadcaster_id": broadcaster_id,
                "clip_duration": 30,
                "quality_scoring_enabled": True,
                "basic_emotion_enabled": True,
                "opensmile_enabled": True,
                "vosk_enabled": True,
                "auto_start_on_stream": False
            }

            config_path = os.path.join(install_path, "smartclip_cz_config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            self.update_progress(90, "Configuration created successfully")
            return True

        except Exception as e:
            self.update_progress(90, f"Configuration creation failed: {str(e)}")
            return False
    
    def show_completion_dialog(self, install_path, system_python=None):
        """Show installation completion dialog with clickable paths"""
        # Get the actual Python installation folder (detected system Python)
        if system_python and os.path.exists(system_python):
            python_folder = os.path.dirname(system_python)
        else:
            # Fallback to bundled Python if system Python not available
            python_folder = os.path.join(install_path, "python")
        venv_path = os.path.join(install_path, "venv")

        # Create custom dialog instead of messagebox for clickable elements
        completion_dialog = tk.Toplevel(self.root)
        completion_dialog.title("Installation Complete")
        completion_dialog.geometry("700x600")
        completion_dialog.transient(self.root)
        completion_dialog.grab_set()

        # Main frame with scrollbar
        main_frame = tk.Frame(completion_dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Title
        title_label = tk.Label(main_frame, text="SmartClip CZ Installation Complete!",
                              font=("Arial", 16, "bold"), fg="#27ae60")
        title_label.pack(pady=(0, 20))

        # Installation path section
        path_frame = tk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(path_frame, text="Installation completed successfully!", font=("Arial", 12, "bold"), fg="#27ae60").pack(anchor=tk.W)
        tk.Label(path_frame, text="Use the 'Copy Installation Path' button below when loading the script in OBS.", font=("Arial", 10)).pack(anchor=tk.W, pady=(5, 0))

        # OBS Configuration section
        obs_frame = tk.Frame(main_frame)
        obs_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(obs_frame, text="OBS Python Configuration:",
                font=("Arial", 12, "bold")).pack(anchor=tk.W)

        obs_text = f"""1. Open OBS Studio
2. Go to Tools -> Scripts
3. Click the Python Settings tab
4. Click 'Copy Python Path' button below, then paste the path
5. Click OK to apply settings"""

        tk.Label(obs_frame, text=obs_text, justify=tk.LEFT).pack(anchor=tk.W, pady=(5, 2))

        # Script loading section
        script_frame = tk.Frame(main_frame)
        script_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(script_frame, text="Loading the Script:",
                font=("Arial", 12, "bold")).pack(anchor=tk.W)

        script_text = f"""1. In Scripts tab, click '+' (Add Scripts) button
2. Click 'Copy Installation Path' button below, then paste in file dialog to navigate
3. Select 'smartclip_cz.py' file
4. Click 'Open' to load the script"""

        tk.Label(script_frame, text=script_text, justify=tk.LEFT).pack(anchor=tk.W, pady=(5, 0))

        # Package installation section
        package_frame = tk.Frame(main_frame)
        package_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(package_frame, text="Package Installation:",
                font=("Arial", 12, "bold")).pack(anchor=tk.W)

        package_text = """SmartClip CZ has been installed successfully!
1. All packages have been installed to the virtual environment
2. All SmartClip files are ready to use
3. If any packages failed, use the backup installer in the folder"""

        tk.Label(package_frame, text=package_text, justify=tk.LEFT).pack(anchor=tk.W, pady=(5, 0))

        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        tk.Button(button_frame, text="Copy Installation Path",
                 command=lambda: self.copy_to_clipboard(install_path),
                 bg="#3498db", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(button_frame, text="Copy Python Path",
                 command=lambda: self.copy_to_clipboard(python_folder),
                 bg="#9b59b6", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(button_frame, text="Open Installation Folder",
                 command=lambda: self.open_folder(install_path),
                 bg="#e67e22", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(button_frame, text="Close",
                 command=lambda: [completion_dialog.destroy(), self.root.quit()],
                 bg="#27ae60", fg="white", font=("Arial", 10, "bold")).pack(side=tk.RIGHT)

        # Update main installer buttons
        self.close_btn.config(text="Close", command=self.root.quit)
        self.install_btn.config(text="Completed", bg="#27ae60", state=tk.DISABLED)

    def open_folder(self, path):
        """Open folder in Windows Explorer"""
        try:
            import os
            os.startfile(path)
        except Exception:
            try:
                import subprocess
                subprocess.run(['explorer', path], check=False)
            except:
                pass

    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            # Show brief confirmation
            import tkinter.messagebox as mb
            mb.showinfo("Copied", f"Path copied to clipboard:\n{text}")
        except Exception:
            pass

    def run_package_installer(self, install_path):
        """Open installation folder"""
        try:
            import tkinter.messagebox as mb

            mb.showinfo("Installation Folder",
                       "Opening SmartClip CZ installation folder.\n\n"
                       "All files including backup installers are located here.")

            # Open folder safely
            self.open_installation_folder(install_path)

        except Exception as e:
            import tkinter.messagebox as mb
            mb.showerror("Error", f"Could not access installation folder: {e}")
    
    def run(self):
        """Run the installer"""
        try:
            self.root.mainloop()
        except Exception as e:
            messagebox.showerror("Error", f"Installer error: {e}")

if __name__ == "__main__":
    # Prevent multiple instances when running as EXE
    import multiprocessing
    multiprocessing.freeze_support()

    try:
        app = SmartClipInstaller()
        app.run()
    except Exception as e:
        import tkinter.messagebox as mb
        mb.showerror("Startup Error", f"Failed to start installer: {e}")
        sys.exit(1)
