#!/usr/bin/env python3
"""
Rebuild the SmartClip CZ installer with fixes for:
1. Multiple instances issue
2. OAuth hanging issue  
3. Package installation from requirements.txt
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    print("🔧 Rebuilding SmartClip CZ Installer with Fixes")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("final_installer.py"):
        print("❌ Error: final_installer.py not found in current directory")
        print("   Please run this script from the SmartClip CZ root directory")
        return False
    
    # Check if requirements.txt exists
    if not os.path.exists("requirements.txt"):
        print("❌ Error: requirements.txt not found")
        print("   This file is needed for proper package installation")
        return False
    
    print("✅ Found required files")
    
    # Build the installer
    print("\n📦 Building installer with PyInstaller...")
    
    # PyInstaller command with all necessary options including SmartClip files
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=SmartClip_CZ_Installer_Fixed",
        "--icon=icon.ico" if os.path.exists("icon.ico") else "",
        # Add all SmartClip files and directories
        "--add-data=requirements.txt;.",
        "--add-data=smartclip_cz.py;.",
        "--add-data=README.md;.",
        "--add-data=core;core",
        "--add-data=detectors;detectors",
        "--add-data=widgets;widgets",
        "--add-data=models;models",
        # Hidden imports
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.messagebox",
        "--hidden-import=tkinter.filedialog",
        "--hidden-import=multiprocessing",
        "--hidden-import=threading",
        "--hidden-import=http.server",
        "--hidden-import=urllib.request",
        "--hidden-import=urllib.parse",
        "--hidden-import=webbrowser",
        "--hidden-import=requests",
        "--hidden-import=json",
        "--hidden-import=time",
        "--hidden-import=shutil",
        "--hidden-import=zipfile",
        "--hidden-import=tempfile",
        "--hidden-import=pathlib",
        "--hidden-import=subprocess",
        "--collect-all=tkinter",
        "--noconfirm",
        "final_installer.py"
    ]
    
    # Remove empty icon parameter if no icon exists
    cmd = [arg for arg in cmd if arg]
    
    try:
        print("   Running PyInstaller...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Installer built successfully!")
        
        # Check if the exe was created
        temp_exe_path = os.path.join("dist", "SmartClip_CZ_Installer_Fixed.exe")
        final_exe_path = os.path.join("dist", "SmartClip_CZ_Installer.exe")

        if os.path.exists(temp_exe_path):
            # Rename to final name
            if os.path.exists(final_exe_path):
                os.remove(final_exe_path)
            os.rename(temp_exe_path, final_exe_path)

            file_size = os.path.getsize(final_exe_path) / (1024 * 1024)  # MB
            print(f"📁 Installer created: {final_exe_path}")
            print(f"📏 File size: {file_size:.1f} MB")
            
            print("\n🎉 SUCCESS! SmartClip CZ installer is ready to use.")
            print("\n🔧 Features:")
            print("   ✅ Automatic Python 3.11.9 detection and installation")
            print("   ✅ Virtual environment setup with all dependencies")
            print("   ✅ Twitch OAuth setup with automatic token refresh")
            print("   ✅ Professional installation experience")
            print("   ✅ Complete OBS integration")
            print(f"\n🚀 Run: {final_exe_path}")
            
            return True
        else:
            print("❌ Error: Installer exe not found after build")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstaller failed: {e}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False
    except Exception as e:
        print(f"❌ Build error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🚀 You can now test the fixed installer:")
        print("   1. Run SmartClip_CZ_Installer_Fixed.exe")
        print("   2. Verify no multiple instances appear")
        print("   3. Test OAuth setup (should timeout properly)")
        print("   4. Check that packages install from requirements.txt")
    else:
        print("\n❌ Build failed. Please check the errors above.")
        
    input("\nPress Enter to exit...")
