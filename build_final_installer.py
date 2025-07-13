#!/usr/bin/env python3
"""
Final Build Script for SmartClip CZ Standalone Installer
Creates a robust .exe installer with proper error handling and encoding.

Author: Jakub Kolář (LordBoos)
Email: lordboos@gmail.com
GitHub: https://github.com/LordBoos
"""

import os
import sys
import shutil
import subprocess
import tempfile
import time

def check_requirements():
    """Check build requirements"""
    print("🔍 Checking build requirements...")
    
    # Check Python version
    if sys.version_info < (3, 11):
        print("❌ Python 3.11+ required")
        return False
    print("✅ Python version OK")
    
    # Check PyInstaller
    try:
        import PyInstaller
        print("✅ PyInstaller available")
    except ImportError:
        print("📦 Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("✅ PyInstaller installed")
    
    return True

def create_robust_installer():
    """Create a robust installer script with better error handling"""
    installer_code = '''import os
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
                <h1 class="loading">Processing Authorization...</h1>
                <p id="status">Extracting access token...</p>

                <script>
                    function processToken() {
                        // Get the fragment part of the URL (after #)
                        const fragment = window.location.hash.substring(1);
                        const params = new URLSearchParams(fragment);
                        const accessToken = params.get('access_token');

                        if (accessToken) {
                            // Send token to Python server
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
            if self.path == '/token':
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))

                # Store token in server instance
                self.server.oauth_token = data.get('token')

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "success"}')
            else:
                self.send_error(404)

        except Exception as e:
            self.send_error(500, f"Server error: {e}")

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
            venv_success, venv_python = self.setup_python_environment(install_path)

            # Step 4: Install packages
            self.update_progress(65, "Installing Python packages...")
            self.install_python_packages(install_path, venv_python)
            
            # Step 5: Download models
            self.update_progress(85, "Downloading AI models...")
            self.download_models(install_path)
            
            # Step 6: Create configuration
            self.update_progress(95, "Creating configuration files...")
            self.create_configuration(install_path)
            
            # Step 7: Complete
            self.update_progress(100, "Installation completed successfully!")
            
            self.show_completion_dialog(install_path)
            
        except Exception as e:
            error_msg = f"Installation failed: {str(e)}"
            messagebox.showerror("Installation Error", error_msg)
            self.status_var.set(error_msg)
            self.install_btn.config(state=tk.NORMAL, text="Install SmartClip CZ", bg="#27ae60")
    
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
    
    def download_python_311(self, install_path):
        """Download Python 3.11.9 portable"""
        try:
            self.update_progress(22, "Downloading Python 3.11.9...")

            python_dir = os.path.join(install_path, "python")
            os.makedirs(python_dir, exist_ok=True)

            # Python 3.11.9 embeddable zip URL
            python_url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
            python_zip = os.path.join(python_dir, "python-3.11.9-embed-amd64.zip")

            try:
                import urllib.request
                urllib.request.urlretrieve(python_url, python_zip)

                # Extract Python
                self.update_progress(24, "Extracting Python 3.11.9...")
                import zipfile
                with zipfile.ZipFile(python_zip, 'r') as zip_ref:
                    zip_ref.extractall(python_dir)

                # Remove zip file
                os.remove(python_zip)

                # Verify python.exe exists
                python_exe = os.path.join(python_dir, "python.exe")
                if os.path.exists(python_exe):
                    self.update_progress(25, "Python 3.11.9 installed successfully")
                    return python_exe
                else:
                    raise Exception("Python executable not found after extraction")

            except Exception as e:
                # Fallback: create info file for manual installation
                self.update_progress(25, f"Python download failed: {str(e)}")
                info_file = os.path.join(python_dir, "python_installation_required.txt")
                with open(info_file, 'w') as f:
                    f.write("Python 3.11.9 Installation Required\\n")
                    f.write("=" * 40 + "\\n\\n")
                    f.write("SmartClip CZ requires Python 3.11.9 for OBS Studio.\\n\\n")
                    f.write("Please download Python 3.11.9 embeddable package from:\\n")
                    f.write("https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip\\n\\n")
                    f.write("Extract the contents to this directory:\\n")
                    f.write(f"{python_dir}\\n\\n")
                    f.write("Then use this path in OBS Python Settings:\\n")
                    f.write(f"{os.path.join(python_dir, 'python.exe')}\\n")

                return None

        except Exception as e:
            self.update_progress(25, f"Python setup failed: {str(e)}")
            return None

    def setup_python_environment(self, install_path):
        """Setup Python virtual environment"""
        try:
            self.update_progress(20, "Setting up Python environment...")

            # First try to download Python 3.11.9
            downloaded_python = self.download_python_311(install_path)

            # Create virtual environment using current Python (for package installation)
            venv_path = os.path.join(install_path, "venv")

            # Use Python's venv module directly without subprocess to avoid multiple instances
            import venv
            venv_builder = venv.EnvBuilder(with_pip=True)
            venv_builder.create(venv_path)

            # Verify virtual environment was created
            venv_python = os.path.join(venv_path, "Scripts", "python.exe")
            if os.path.exists(venv_python):
                self.update_progress(30, "Virtual environment created successfully")

                # If Python 3.11.9 download failed, copy venv python as fallback
                if not downloaded_python:
                    python_dir = os.path.join(install_path, "python")
                    os.makedirs(python_dir, exist_ok=True)
                    target_python = os.path.join(python_dir, "python.exe")

                    try:
                        shutil.copy2(venv_python, target_python)

                        # Copy essential DLLs from venv Scripts directory
                        venv_scripts = os.path.dirname(venv_python)
                        for file in os.listdir(venv_scripts):
                            if file.endswith('.dll'):
                                src = os.path.join(venv_scripts, file)
                                dst = os.path.join(python_dir, file)
                                try:
                                    shutil.copy2(src, dst)
                                except:
                                    pass  # Skip if copy fails

                        downloaded_python = target_python

                    except Exception as e:
                        self.update_progress(30, f"Warning: Could not copy Python for OBS: {str(e)}")

                return True, venv_python
            else:
                self.update_progress(30, "Warning: Virtual environment creation failed")
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
                        f.write(f"{package}\\n")
                self.update_progress(32, "Created fallback requirements.txt...")

            # Create a comprehensive installation batch file
            install_bat = os.path.join(install_path, "install_all_packages.bat")
            with open(install_bat, 'w') as f:
                f.write("@echo off\\n")
                f.write("echo Installing SmartClip CZ packages to virtual environment...\\n")
                f.write(f'cd /d "{install_path}"\\n')
                f.write(f'"{venv_python}" -m pip install --upgrade pip\\n')
                f.write(f'"{venv_python}" -m pip install -r requirements.txt --no-warn-script-location\\n')
                f.write("echo Package installation completed!\\n")
                f.write("pause\\n")

            # Install all packages from requirements.txt during installation
            self.update_progress(35, "Installing packages from requirements.txt...")

            try:
                # First upgrade pip
                pip_cmd = [venv_python, "-m", "pip", "install", "--upgrade", "pip"]
                subprocess.run(pip_cmd, capture_output=True, text=True, timeout=60,
                             cwd=install_path, check=False,
                             creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)

                self.update_progress(40, "Installing all packages...")

                # Install all packages from requirements.txt
                install_cmd = [venv_python, "-m", "pip", "install", "-r", "requirements.txt", "--no-warn-script-location"]
                result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=300,
                                      cwd=install_path, check=False,
                                      creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)

                if result.returncode == 0:
                    self.update_progress(45, "All packages installed successfully!")
                else:
                    self.update_progress(45, "Package installation completed with some warnings")

            except subprocess.TimeoutExpired:
                self.update_progress(45, "Package installation timed out - batch file available for manual installation")
            except Exception as e:
                self.update_progress(45, f"Package installation error: {str(e)[:50]}... - batch file available")

            # Create user-friendly installation instructions
            install_info = os.path.join(install_path, "PACKAGE_INSTALLATION.txt")
            with open(install_info, 'w') as f:
                f.write("SmartClip CZ - Package Installation\\n")
                f.write("=" * 40 + "\\n\\n")
                f.write("To install all required packages:\\n")
                f.write("1. Double-click 'install_all_packages.bat'\\n")
                f.write("2. Wait for installation to complete\\n\\n")
                f.write("Required packages:\\n")
                for package in packages:
                    f.write(f"- {package}\\n")
                f.write("\\nAll packages will be installed to the virtual environment.\\n")
                f.write("Basic functionality works with just requests and numpy.\\n")

            return True

        except Exception as e:
            self.update_progress(45, f"Package installation failed: {str(e)}")
            return False
    
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
        try:
            self.update_progress(75, "Setting up Twitch OAuth...")

            # Check if user wants to setup OAuth now
            setup_oauth = messagebox.askyesno(
                "Twitch OAuth Setup",
                "Would you like to set up Twitch OAuth credentials now?\\n\\n"
                "This will automatically configure Twitch API access for clip creation.\\n"
                "You can also set this up later by editing the config file."
            )

            if not setup_oauth:
                self.update_progress(80, "Skipping Twitch OAuth setup")
                return "", "", ""

            # Step 1: Get Client ID
            self.update_progress(76, "Opening Twitch Developer Console...")

            try:
                webbrowser.open("https://dev.twitch.tv/console/apps")
                time.sleep(2)
            except:
                pass

            client_id_dialog = tk.Toplevel(self.root)
            client_id_dialog.title("Twitch Client ID")
            client_id_dialog.geometry("600x400")
            client_id_dialog.transient(self.root)
            client_id_dialog.grab_set()

            # Instructions for Client ID
            instructions = tk.Label(client_id_dialog,
                text="Step 1: Create Twitch Application",
                font=("Arial", 14, "bold"))
            instructions.pack(pady=10)

            steps_text = ("1. In the Twitch Developer Console (opened in browser):\\n" +
                         "   • Click 'Register Your Application' or 'Create an App'\\n" +
                         "   • Name: 'SmartClip CZ' (or any name you prefer)\\n" +
                         "   • OAuth Redirect URLs: 'http://localhost:3000'\\n" +
                         "   • Category: 'Application Integration'\\n" +
                         "   • Click 'Create'\\n\\n" +
                         "2. Copy your Client ID from the application details")

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
                if client_id_var.get().strip():
                    client_id_dialog.destroy()
                else:
                    messagebox.showwarning("Missing Client ID", "Please enter your Client ID to continue.")

            def skip_oauth():
                client_id_var.set("")
                client_id_dialog.destroy()

            tk.Button(button_frame, text="Continue", command=continue_oauth, bg="#27ae60", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Skip OAuth Setup", command=skip_oauth).pack(side=tk.LEFT, padx=5)

            # Wait for dialog
            client_id_dialog.wait_window()

            client_id = client_id_var.get().strip()
            if not client_id:
                self.update_progress(80, "Skipping Twitch OAuth setup")
                return "", "", ""

            # Step 2: Automatic OAuth Token Generation with timeout
            self.update_progress(78, "Starting automatic OAuth token generation...")

            try:
                # Add timeout protection to prevent hanging
                import threading
                import time

                oauth_result = [None, None]  # [oauth_token, broadcaster_id]
                oauth_error = [None]

                def oauth_thread():
                    try:
                        token, broadcaster = self.get_oauth_token_automatic(client_id)
                        oauth_result[0] = token
                        oauth_result[1] = broadcaster
                    except Exception as e:
                        oauth_error[0] = str(e)

                # Start OAuth in separate thread with timeout
                thread = threading.Thread(target=oauth_thread)
                thread.daemon = True
                thread.start()

                # Wait for OAuth with timeout (max 45 seconds)
                thread.join(timeout=45)

                if thread.is_alive():
                    # OAuth is taking too long, skip it
                    self.update_progress(80, "OAuth setup timed out - continuing without credentials")
                    return "", "", ""
                elif oauth_error[0]:
                    self.update_progress(80, f"OAuth setup error: {oauth_error[0]} - continuing without credentials")
                    return "", "", ""
                elif oauth_result[0] and oauth_result[1]:
                    self.update_progress(80, "Twitch OAuth setup completed successfully")
                    return client_id, oauth_result[0], oauth_result[1]
                else:
                    self.update_progress(80, "OAuth setup failed - continuing without credentials")
                    return "", "", ""

            except Exception as e:
                self.update_progress(80, f"OAuth setup error: {str(e)} - continuing without credentials")
                return "", "", ""

        except Exception as e:
            self.update_progress(80, f"OAuth setup failed: {str(e)}")
            return "", "", ""

    def get_oauth_token_automatic(self, client_id):
        """Get OAuth token automatically using local server"""
        try:
            # Start local server for OAuth callback
            server = None
            server_thread = None
            oauth_token = None
            broadcaster_id = None

            try:
                # Start HTTP server on localhost:3000
                server = HTTPServer(('localhost', 3000), OAuthCallbackHandler)
                server.oauth_token = None
                server_thread = threading.Thread(target=server.serve_forever)
                server_thread.daemon = True
                server_thread.start()

                # Generate OAuth URL
                scopes = "clips:edit user:read:email channel:read:subscriptions"
                oauth_url = (
                    f"https://id.twitch.tv/oauth2/authorize?"
                    f"client_id={client_id}&"
                    f"redirect_uri=http://localhost:3000&"
                    f"response_type=token&"
                    f"scope={urllib.parse.quote(scopes)}"
                )

                # Show authorization dialog
                auth_dialog = tk.Toplevel(self.root)
                auth_dialog.title("Twitch Authorization")
                auth_dialog.geometry("500x300")
                auth_dialog.transient(self.root)
                auth_dialog.grab_set()

                tk.Label(auth_dialog, text="Step 2: Authorize SmartClip CZ",
                        font=("Arial", 14, "bold")).pack(pady=10)

                tk.Label(auth_dialog,
                        text="1. Click 'Open Authorization Page' below\\n" +
                             "2. In your browser, click 'Authorize' to grant permissions\\n" +
                             "3. Wait for the success message\\n" +
                             "4. Return to this installer",
                        justify=tk.LEFT).pack(pady=10, padx=20)

                def open_auth():
                    try:
                        webbrowser.open(oauth_url)
                    except:
                        messagebox.showerror("Error", f"Could not open browser. Please visit:\\n{oauth_url}")

                tk.Button(auth_dialog, text="Open Authorization Page",
                         command=open_auth, bg="#9146ff", fg="white",
                         font=("Arial", 12, "bold")).pack(pady=10)

                status_label = tk.Label(auth_dialog, text="Waiting for authorization...",
                                       font=("Arial", 10))
                status_label.pack(pady=10)

                def check_token():
                    if server.oauth_token:
                        status_label.config(text="Authorization successful!", fg="green")
                        auth_dialog.after(1000, auth_dialog.destroy)
                    else:
                        auth_dialog.after(1000, check_token)

                # Start checking for token
                auth_dialog.after(1000, check_token)

                # Add skip button to prevent hanging
                def skip_oauth():
                    auth_dialog.destroy()

                tk.Button(auth_dialog, text="Skip OAuth Setup",
                         command=skip_oauth, bg="#e74c3c", fg="white",
                         font=("Arial", 10)).pack(pady=5)

                # Auto-close after 20 seconds to prevent hanging
                auth_dialog.after(20000, auth_dialog.destroy)

                # Wait for dialog with timeout protection
                try:
                    auth_dialog.wait_window()
                except:
                    pass  # Dialog was destroyed

                oauth_token = server.oauth_token if server else None

                if oauth_token:
                    # Get broadcaster ID
                    broadcaster_id = self.get_broadcaster_id(client_id, oauth_token)

            finally:
                # Clean up server with timeout protection
                try:
                    if server:
                        server.shutdown()
                        server.server_close()
                except:
                    pass
                try:
                    if server_thread and server_thread.is_alive():
                        server_thread.join(timeout=2)
                except:
                    pass

            return oauth_token, broadcaster_id

        except Exception as e:
            messagebox.showerror("OAuth Error", f"OAuth setup failed: {str(e)}")
            return None, None

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
            client_id, oauth_token, broadcaster_id = self.setup_twitch_oauth(install_path)

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
                "twitch_oauth_token": oauth_token,
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
    
    def show_completion_dialog(self, install_path):
        """Show installation completion dialog with clickable paths"""
        python_path = os.path.join(install_path, "python", "python.exe")
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

        tk.Label(path_frame, text="Installation path:", font=("Arial", 10, "bold")).pack(anchor=tk.W)

        # Clickable installation path
        path_link = tk.Label(path_frame, text=install_path, fg="blue", cursor="hand2",
                            font=("Arial", 10, "underline"))
        path_link.pack(anchor=tk.W, pady=(2, 0))
        path_link.bind("<Button-1>", lambda e: self.open_folder(install_path))

        # OBS Configuration section
        obs_frame = tk.Frame(main_frame)
        obs_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(obs_frame, text="OBS Python Configuration:",
                font=("Arial", 12, "bold")).pack(anchor=tk.W)

        obs_text = f"""1. Open OBS Studio
2. Go to Tools -> Scripts
3. Click the Python Settings tab
4. Set Python Install Path to:"""

        tk.Label(obs_frame, text=obs_text, justify=tk.LEFT).pack(anchor=tk.W, pady=(5, 2))

        # Clickable Python path
        python_link = tk.Label(obs_frame, text=python_path, fg="blue", cursor="hand2",
                              font=("Arial", 10, "underline"))
        python_link.pack(anchor=tk.W, padx=(20, 0))
        python_folder = os.path.dirname(python_path)  # Get folder path, not executable path
        python_link.bind("<Button-1>", lambda e: self.copy_to_clipboard(python_folder))

        tk.Label(obs_frame, text="5. Click OK to apply settings", justify=tk.LEFT).pack(anchor=tk.W, pady=(2, 0))

        # Script loading section
        script_frame = tk.Frame(main_frame)
        script_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(script_frame, text="Loading the Script:",
                font=("Arial", 12, "bold")).pack(anchor=tk.W)

        script_text = f"""1. In Scripts tab, click '+' (Add Scripts) button
2. Navigate to installation folder (click path above)
3. Select 'smartclip_cz.py' file
4. Click 'Open' to load the script"""

        tk.Label(script_frame, text=script_text, justify=tk.LEFT).pack(anchor=tk.W, pady=(5, 0))

        # Package installation section
        package_frame = tk.Frame(main_frame)
        package_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(package_frame, text="Package Installation:",
                font=("Arial", 12, "bold")).pack(anchor=tk.W)

        package_text = """Core packages have been installed. For full functionality:
1. Double-click 'install_all_packages.bat' in the installation folder
2. Wait for all packages to install to the virtual environment
3. Basic emotion detection works immediately"""

        tk.Label(package_frame, text=package_text, justify=tk.LEFT).pack(anchor=tk.W, pady=(5, 0))

        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        tk.Button(button_frame, text="Install Packages",
                 command=lambda: self.run_package_installer(install_path),
                 bg="#e67e22", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(button_frame, text="Open Installation Folder",
                 command=lambda: self.open_folder(install_path),
                 bg="#3498db", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(button_frame, text="Copy Python Path",
                 command=lambda: self.copy_to_clipboard(os.path.dirname(python_path)),
                 bg="#9b59b6", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))

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
            mb.showinfo("Copied", f"Path copied to clipboard:\\n{text}")
        except Exception:
            pass

    def run_package_installer(self, install_path):
        """Run the package installer batch file"""
        try:
            import os
            batch_file = os.path.join(install_path, "install_all_packages.bat")
            if os.path.exists(batch_file):
                os.startfile(batch_file)
            else:
                import tkinter.messagebox as mb
                mb.showerror("Error", "Package installer not found")
        except Exception as e:
            import tkinter.messagebox as mb
            mb.showerror("Error", f"Could not run package installer: {e}")
    
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
'''

    with open("final_installer.py", "w", encoding="utf-8") as f:
        f.write(installer_code)

    return "final_installer.py"

def build_final_exe():
    """Build the final .exe installer"""
    print("🔨 Building final .exe installer...")
    
    # Create installer script
    installer_script = create_robust_installer()
    
    # Build command without version file to avoid encoding issues
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "SmartClip_CZ_Installer",
        "--clean",
        "--noconfirm",
        installer_script
    ]
    
    # Add icon if available
    if os.path.exists("icon.ico"):
        cmd.extend(["--icon", "icon.ico"])
    
    # Add data files
    data_files = [
        ("smartclip_cz.py", "."),
        ("core", "core"),
        ("detectors", "detectors"),
        ("widgets", "widgets"),
        ("requirements.txt", "."),
        ("README.md", ".")
    ]
    
    for src, dst in data_files:
        if os.path.exists(src):
            cmd.extend(["--add-data", f"{src};{dst}"])
    
    # Add hidden imports - include all required modules
    hidden_imports = [
        "tkinter", "tkinter.ttk", "tkinter.filedialog", "tkinter.messagebox",
        "urllib.request", "urllib.parse", "threading", "json", "subprocess", "shutil",
        "tempfile", "zipfile", "pathlib", "time", "webbrowser",
        "requests", "urllib3", "certifi", "charset_normalizer", "idna",
        "http.server", "http.client"
    ]
    
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])
    
    try:
        print("   Running PyInstaller...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Final .exe built successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout[-1000:]}")
        if e.stderr:
            print(f"STDERR: {e.stderr[-1000:]}")
        return False

def create_final_release():
    """Create final release package"""
    print("📦 Creating final release package...")
    
    # Create release directory
    release_dir = "release_final"
    os.makedirs(release_dir, exist_ok=True)
    
    # Copy installer
    installer_exe = "dist/SmartClip_CZ_Installer.exe"
    if os.path.exists(installer_exe):
        try:
            # Add small delay to ensure file is not locked
            time.sleep(1)
            target_path = os.path.join(release_dir, "SmartClip_CZ_Installer.exe")
            # Remove target if exists
            if os.path.exists(target_path):
                os.remove(target_path)
            shutil.copy2(installer_exe, target_path)
            print("✅ Installer copied to release directory")
        except Exception as e:
            print(f"⚠️ Warning: Could not copy installer: {e}")
            print("   The installer was built successfully in dist/ directory")
    
    # Create release README
    readme_content = """# SmartClip CZ - Standalone Installer

## 🚀 Installation

1. **Download** `SmartClip_CZ_Installer.exe`
2. **Run** the installer (may require admin rights)
3. **Follow** the installation wizard
4. **Open OBS Studio** and load the script

## ✨ Features

- **Emotion Detection** - Automatic detection of laughter, excitement, surprise, joy
- **Speech Recognition** - Czech and English activation phrases
- **Twitch Integration** - Automatic clip creation with smart titles
- **Quality Scoring** - AI-powered clip quality assessment
- **Real-time Visualization** - Confidence displays for streamers

## 🎯 What's Included

- Complete SmartClip CZ plugin for OBS Studio
- Python virtual environment with dependencies
- AI models for emotion and speech recognition
- Professional installer with progress tracking
- Default configuration with optimal settings

## 📋 Requirements

- **Windows 10/11** (64-bit)
- **OBS Studio** (version 27.0 or higher)
- **Internet connection** (for package downloads)
- **Twitch account** (for clip creation)

## 🔧 Troubleshooting

- **Antivirus Warning**: Normal for new executables, add exception if needed
- **Admin Rights**: Some installations require administrator privileges
- **OBS Not Found**: Manually select installation directory in installer
- **Package Errors**: Internet connection required for Python packages

## 📞 Support

- **GitHub**: https://github.com/LordBoos/SmartClip-CZ
- **Issues**: https://github.com/LordBoos/SmartClip-CZ/issues
- **Email**: lordboos@gmail.com

## 📄 License

MIT License - See LICENSE file for details

---

**Author**: Jakub Kolář (LordBoos)  
**Version**: 1.0  
**Build**: Standalone Installer
"""
    
    with open(os.path.join(release_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print(f"✅ Final release package created: {release_dir}")
    return release_dir

def main():
    """Main build function"""
    print("🚀 SmartClip CZ - Final Installer Builder")
    print("=" * 60)
    
    if not check_requirements():
        return False
    
    if not build_final_exe():
        return False
    
    release_dir = create_final_release()
    
    print("\\n🎉 Final installer build completed!")
    print(f"📁 Release directory: {release_dir}")
    print(f"📄 Installer: {release_dir}/SmartClip_CZ_Installer.exe")
    print("\\n📊 Installer Details:")
    
    exe_path = os.path.join(release_dir, "SmartClip_CZ_Installer.exe")
    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path)
        size_mb = size / (1024 * 1024)
        print(f"   File size: {size:,} bytes ({size_mb:.1f} MB)")
        print(f"   Type: Standalone Windows executable")
        print(f"   Dependencies: None (all embedded)")
    
    print("\\n🚀 Ready for distribution!")
    print("   Upload to GitHub releases")
    print("   Users download and run single .exe file")
    print("   Professional installation experience")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
