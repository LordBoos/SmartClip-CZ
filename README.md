# SmartClip CZ - Python Edition

**Intelligent OBS Plugin for Automated Twitch Clip Creation Based on Emotional Reactions and Czech Speech Recognition**

[![Python Version](https://img.shields.io/badge/python-3.11.9-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OBS Studio](https://img.shields.io/badge/OBS%20Studio-29.0+-purple.svg)](https://obsproject.com)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-green.svg)](https://github.com/LordBoos/SmartClip-CZ)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/LordBoos/SmartClip-CZ)
[![Contributions Welcome](https://img.shields.io/badge/Contributions-Welcome-brightgreen.svg)](CONTRIBUTING.md)

## 🎯 Overview

SmartClip CZ is a sophisticated OBS Studio plugin that automatically creates Twitch clips when it detects emotional reactions (laughter, excitement, surprise) or specific Czech activation phrases in your stream. The plugin uses advanced AI/ML techniques including OpenSMILE emotion detection and Vosk speech recognition to provide real-time analysis of your streaming content.

## 🎉 Current Status: Production Ready

**Latest Version:** v2.0 - Complete rewrite with professional installer
- ✅ **Fully automated installation** - One-click setup with no manual configuration
- ✅ **Automatic OAuth token refresh** - Never worry about expired tokens
- ✅ **Professional user experience** - Clean UI and comprehensive error handling
- ✅ **Production tested** - Stable and reliable for live streaming
- ✅ **Complete documentation** - Comprehensive setup and usage guides

## ✨ Key Features

### 🎭 **Multi-Modal Emotion Detection**
- **Basic Emotion Detection** - Fast, lightweight emotion recognition
- **OpenSMILE Integration** - Advanced ML-based emotion analysis
- **Real-time Processing** - Live audio analysis during streaming

### 🗣️ **Czech Speech Recognition**
- **Vosk Speech Engine** - Accurate Czech language recognition
- **Custom Activation Phrases** - Configurable trigger words (skvělé, wow, úžasné, etc.)
- **Confidence Scoring** - Adjustable sensitivity for phrase detection

### 🎬 **Intelligent Clip Creation**
- **Automatic Twitch Integration** - Direct API integration for clip creation
- **OAuth Token Auto-Refresh** - Automatic token renewal for uninterrupted service
- **Smart Clip Detection** - Triggers based on emotions and activation phrases
- **Quality Scoring** - AI-powered clip quality assessment
- **Smart Timing** - Optimal clip duration and positioning
- **Cooldown Management** - Prevents spam clip creation

**Note:** Due to Twitch API limitations, clips automatically use your current stream title. Custom title formats are logged for reference but cannot be set programmatically.

### 📊 **Real-time Visualization**
- **Live Confidence Widget** - Streamable overlay showing detection confidence
- **Activity Logging** - Detailed detection history with timestamps
- **Performance Monitoring** - Real-time statistics and diagnostics

### 🚀 **Advanced Features**
- **Auto-start/stop Detection** - Automatically begins when streaming starts
- **Separate Sensitivity Controls** - Individual settings for each detection type
- **Professional UI** - Clean, modern interface with emoji indicators
- **Cross-platform Support** - Works on Windows, macOS, and Linux

## 🛠️ Installation

### 🎯 One-Click Installer (Recommended)

**Professional standalone installer - No Python required!**

1. **Download** `SmartClip_CZ_Installer.exe` from [Releases](https://github.com/LordBoos/SmartClip-CZ/releases)
2. **Run** the installer as administrator
3. **Follow** the installation wizard:
   - ✅ **Automatic Python 3.11.9 detection/installation**
   - ✅ **Virtual environment setup with all dependencies**
   - ✅ **Twitch OAuth setup with guided process**
   - ✅ **Complete OBS integration**
4. **Open OBS Studio** → Tools → Scripts → Python Settings → Set path (copied from installer)
5. **Add Script** → Navigate to installation folder → Select `smartclip_cz.py`
6. **Done!** - Complete automated setup

**✨ Features:**
- 🚀 **No manual Python installation** - Handles everything automatically
- 🔐 **Integrated OAuth setup** - Guided Twitch API configuration
- 📦 **All dependencies included** - numpy, scipy, opensmile, vosk, etc.
- 🎯 **Professional UI** - Clean, user-friendly installation experience
- 🔄 **Automatic token refresh** - Never worry about expired tokens again

### System Requirements
- **OBS Studio** (version 29.0 or higher recommended)
- **Windows 10/11** (primary support), macOS, Linux
- **4GB RAM minimum** (8GB recommended for optimal performance)
- **2GB free disk space** for installation and models
- **Twitch account** with streaming capabilities

### Quick Installation (Python Required)

1. **Download** the latest release or clone this repository:
   ```bash
   git clone https://github.com/smartclip-cz/smartclip-cz-python.git
   cd smartclip-cz-python
   ```

2. **Run the installer:**
   ```bash
   python install_python_plugin.py
   ```

3. **The installer will automatically:**
   - ✅ **Create isolated virtual environment** for dependencies
   - ✅ **Install Python packages** (numpy, scipy, opensmile, vosk, etc.)
   - ✅ **Copy files** to OBS scripts/SmartClip_CZ directory
   - ✅ **Download Vosk models** for speech recognition
   - ✅ **Optionally set up Twitch API credentials** (guided process)
   - ✅ **Create default configuration** with optimal settings

4. **Open OBS Studio** → Tools → Scripts → Click '+' (Add Scripts)
5. **Navigate to** your OBS scripts directory, then to `SmartClip_CZ/` folder:
   - **Windows:** `%APPDATA%\obs-studio\scripts\SmartClip_CZ\`
   - **macOS:** `~/Library/Application Support/obs-studio/scripts/SmartClip_CZ/`
   - **Linux:** `~/.config/obs-studio/scripts/SmartClip_CZ/`
6. **Select** `smartclip_cz.py` file and click 'Open'
7. **Configure** your settings in the plugin interface

### Manual Installation

If the automatic installer doesn't work:

1. **Install dependencies:**
   ```bash
   pip install numpy scipy scikit-learn vosk requests
   ```

2. **Copy plugin files** to your OBS scripts directory:
   - **Windows:** `%APPDATA%\obs-studio\scripts\`
   - **macOS:** `~/Library/Application Support/obs-studio/scripts/`
   - **Linux:** `~/.config/obs-studio/scripts/`

3. **Load the script** in OBS Studio as described above

## 🔑 Twitch API Setup

### 🚀 Automated Setup (Built into Installer)

The SmartClip CZ installer includes **fully automated Twitch OAuth setup with token refresh**:

1. **During installation**, choose "Yes" when prompted for Twitch setup
2. **Follow the guided process:**
   - 🌐 **Browser opens automatically** to Twitch Developer Console
   - 📝 **Create application** with guided instructions
   - 🔑 **Enter Client ID** from your application
   - 🔐 **Enter Client Secret** (recommended for auto-refresh)
   - ⚡ **Automatic OAuth flow** - browser handles authorization
   - 💾 **All credentials saved automatically** to configuration

**✅ Complete automation with automatic token refresh - never worry about expired tokens!**

### 🔄 Automatic Token Refresh

SmartClip CZ now includes **automatic OAuth token refresh**:
- 🔄 **Auto-renewal** - Tokens refresh automatically before expiration (5-minute buffer)
- 🔐 **Secure storage** - Refresh tokens stored safely in configuration
- 📝 **Comprehensive logging** - Full visibility into token management
- ⚡ **Seamless operation** - No interruption to clip creation
- 🎯 **Production ready** - Handles token expiration gracefully

**Why use Client Secret + Refresh Tokens?**
- ✅ **Prevents service interruption** - No more "token expired" errors
- ✅ **Fully automated** - No manual token renewal needed
- ✅ **Professional setup** - Industry standard OAuth 2.0 flow
- ✅ **Long-term reliability** - Works indefinitely without user intervention

### 📋 Manual Setup (Alternative)

If you prefer manual setup or the automated method doesn't work:

### Step 1: Create a Twitch Application

1. **Visit** the [Twitch Developer Console](https://dev.twitch.tv/console)
2. **Log in** with your Twitch account
3. **Click** "Create an App" or "Register Your Application"
4. **Fill in the application details:**
   - **Name:** `SmartClip CZ` (or any name you prefer)
   - **OAuth Redirect URLs:** `http://localhost:3000` (required for token generation)
   - **Category:** `Application Integration`
5. **Click** "Create"
6. **Get your credentials:**
   - **Copy your Client ID** (always visible)
   - **Click "New Secret"** to generate a Client Secret
   - **Copy the Client Secret immediately** (shown only once!)
   - **Save both securely** - you'll need them for automatic token refresh

### Step 2: Generate an OAuth Token

**Method 1: Using Twitch CLI (Recommended)**
1. **Install** [Twitch CLI](https://github.com/twitchdev/twitch-cli/releases)
2. **Open** command prompt/terminal
3. **Run** the following command:
   ```bash
   twitch token -u -s "clips:edit user:read:email channel:read:subscriptions"
   ```
4. **Follow** the browser authentication flow
5. **Copy the access token** from the output

**Method 2: Manual OAuth Flow**
1. **Create** the authorization URL using your Client ID:
   ```
   https://id.twitch.tv/oauth2/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:3000&response_type=token&scope=clips:edit+user:read:email+channel:read:subscriptions
   ```
2. **Replace** `YOUR_CLIENT_ID` with your actual Client ID
3. **Visit** the URL in your browser
4. **Authorize** the application
5. **Copy the access token** from the redirect URL (after `access_token=`)

**Method 3: Third-party Tools**
- [Twitch Token Generator](https://twitchtokengenerator.com/) - Simple web-based generator
- [Streamlabs Token Generator](https://streamlabs.com/dashboard#/settings/api-settings) - If you use Streamlabs

**⚠️ Security Note:** Keep this token secure - treat it like a password!

### Step 3: Get Your Broadcaster ID

1. **Visit** [Twitch Username to User ID Converter](https://www.streamweasels.com/tools/convert-twitch-username-to-user-id/)
2. **Enter your Twitch username**
3. **Copy your User ID** (this is your Broadcaster ID)

### Step 4: Configure in OBS

1. **Open** the SmartClip CZ script properties in OBS
2. **Enter** your credentials:
   - **Twitch Client ID:** Paste the Client ID from Step 1
   - **Twitch Client Secret:** (Optional) For automatic token refresh
   - **OAuth Token:** Paste the token from Step 2 (without "oauth:")
   - **Refresh Token:** (Optional) For automatic token renewal
   - **Broadcaster ID:** Paste the User ID from Step 3

### Required Scopes

The OAuth token needs these scopes for full functionality:
- `clips:edit` - **Required** - Create clips on your channel
- `user:read:email` - **Optional** - Read user information for logging
- `channel:read:subscriptions` - **Optional** - Read channel information

**Minimum Required:** `clips:edit` is the only essential scope for basic clip creation.

### Troubleshooting OAuth

**Common Issues:**
- **"Invalid OAuth token"** - Token may have expired, generate a new one
- **"Insufficient privileges"** - Make sure `clips:edit` scope is included
- **"User not found"** - Check that your Broadcaster ID is correct
- **"Cannot create clip"** - Ensure you're currently streaming live

**Token Validation:**
Test your credentials with the included validator:
```bash
python tests/test_twitch_oauth.py
```

Or manually test at: `https://id.twitch.tv/oauth2/validate`
```bash
curl -H "Authorization: OAuth YOUR_TOKEN" https://id.twitch.tv/oauth2/validate
```

## ⚙️ Configuration

### Detection Settings

#### Sensitivity Controls
- **🎭 Basic Emotion Sensitivity** (0.1-1.0) - Lower = more sensitive
- **🤖 OpenSMILE Sensitivity** (0.1-1.0) - Adjust for your voice/style
- **🗣️ Vosk Speech Sensitivity** (0.1-1.0) - Czech phrase detection threshold

#### Emotions to Detect
- **🤣 Laughter** - Detects genuine laughter and chuckling
- **🎉 Excitement** - High-energy positive emotions
- **😲 Surprise** - Sudden reactions and amazement
- **😊 Joy** - General happiness and positive emotions

#### Czech Activation Phrases
Default phrases include: `skvělé`, `wow`, `úžasné`, `perfektní`, `bomba`, `super`, `fantastické`

### Audio Source Configuration
1. **Select** your audio source (usually "Desktop Audio" or microphone)
2. **Ensure** the source is active and receiving audio
3. **Test** audio levels in OBS mixer

## 🎮 Usage

### Basic Operation
1. **Start OBS** and begin streaming
2. **Enable detection** using the "▶️ Start Detection" button
3. **Stream normally** - the plugin monitors your audio automatically
4. **Check Twitch** for automatically created clips

### 🎬 Clip Titles
SmartClip CZ automatically generates descriptive clip titles using this format:
```
{Stream Title} - SmartClip - {Trigger}
```

**Examples:**
- `Epic Gaming Session - SmartClip - laughter`
- `Road to Victory! - SmartClip - that's amazing`
- `Live Stream - SmartClip - excitement`
- `Playing Awesome Game - SmartClip - neuvěřitelné`

**Features:**
- ✅ **Includes your stream title** for context
- ✅ **Shows the trigger** (emotion or phrase) that created the clip
- ✅ **Smart length management** - automatically truncates long titles
- ✅ **Supports both languages** - Czech and English triggers

### Live Confidence Widget
1. **Click** "📈 Show Live Confidence Widget" in the plugin interface
2. **Add** the widget window as a "Window Capture" source in OBS
3. **Position** on your stream layout for viewers to see live detection confidence
4. **Customize** opacity and size to fit your stream design

### Auto-start Feature
1. **Enable** "🚀 Auto-start/stop Detection with Streaming"
2. **Detection automatically starts** when you begin streaming
3. **Detection automatically stops** when you end streaming
4. **Perfect for** streamers who want complete automation

## 📊 Real-time Visualization

The confidence widget provides viewers with:
- **Live confidence levels** for all detection types
- **Progress bars** showing detection strength
- **Activity history** with timestamps
- **Current emotion/phrase** displays
- **Professional dark theme** optimized for streaming

## 🔧 Advanced Configuration

### OpenSMILE Setup
For enhanced emotion detection using the Python OpenSMILE library:

**Automatic Installation:**
The installer will automatically install the OpenSMILE Python library.

**Manual Installation:**
```bash
pip install opensmile
```

**Features:**
- Advanced ML-based emotion detection
- No external binaries required
- Integrated with Python environment
- Automatic feature extraction

### Vosk Model Setup
For multi-language speech recognition:

**Automatic Download (Recommended):**
The installer automatically downloads both models to the correct location:
- `OBS/scripts/SmartClip_CZ/models/vosk-model-small-cs-0.4-rhasspy/` (Czech)
- `OBS/scripts/SmartClip_CZ/models/vosk-model-small-en-us-0.15/` (English)

**Manual Download (if automatic fails):**
1. Navigate to your OBS scripts/SmartClip_CZ directory
2. Run: `python download_vosk_models.py`
3. Or download manually from [Vosk Models](https://alphacephei.com/vosk/models)

Both models can work simultaneously for bilingual detection.

### Custom Configuration File
Edit `smartclip_cz_config.json` in your OBS scripts directory:
```json
{
  "enabled_emotions": ["laughter", "excitement", "surprise", "joy"],
  "emotion_sensitivity": 0.7,
  "activation_phrases": [
    "skvělé", "wow", "úžasné", "perfektní",
    "bomba", "super", "fantastické"
  ],
  "english_activation_phrases": [
    "that's amazing", "awesome", "incredible", "fantastic",
    "what the hell", "that's insane", "unbelievable"
  ],
  "quality_scoring_enabled": true,
  "auto_start_detection": true
}
```

## 🐛 Troubleshooting

### Common Issues

#### Plugin Not Loading
- **Check Python installation** and version (3.7+)
- **Install required packages:** `pip install numpy scipy scikit-learn vosk requests`
- **Verify file permissions** in OBS scripts directory
- **Review OBS logs** for error messages

#### No Clips Being Created
- **Verify Twitch API credentials** are correct and complete
- **Check detection sensitivity** settings (try lowering them)
- **Ensure audio source** is properly configured and active
- **Test with manual trigger** phrases
- **Confirm you're streaming** (clips can only be created during live streams)

#### High CPU Usage
- **Reduce detection frequency** in Advanced Settings
- **Disable unused detection types** (Basic/OpenSMILE/Vosk)
- **Lower audio quality** if using high sample rates
- **Close other resource-intensive applications**

#### Confidence Widget Not Opening
- **Check for locale errors** in OBS logs
- **Try manual launch:** `python smartclip_cz_python/obs_confidence_widget.py`
- **Verify tkinter installation:** `python -c "import tkinter"`
- **Use alternative widget:** Try simple_confidence_widget.py

### Getting Help
1. **Check the logs** in OBS → Help → Log Files
2. **Review documentation** for configuration details
3. **Test with minimal settings** to isolate issues
4. **Run test scripts** in the `tests/` directory
5. **Use manual widget launch** as backup option

## 🧪 Testing

Run all tests with the test runner:
```bash
python tests/run_all_tests.py
```

Or run specific test categories interactively:
```bash
python tests/run_all_tests.py --interactive
```

Individual tests:
```bash
# Core functionality tests
python tests/test_emotion_detector.py
python tests/test_opensmile_detector.py
python tests/test_vosk_detector.py

# Configuration and setup tests
python tests/test_config_logging.py
python tests/test_venv_setup.py
python tests/test_twitch_oauth.py
python tests/test_oauth_installer.py
python tests/test_clip_title_format.py
python tests/test_installer_instructions.py

# Widget tests
python tests/test_confidence_widget.py
python tests/test_obs_widget_subprocess.py
python tests/test_standalone_widget.py
```

All tests are located in the `tests/` directory and use proper import paths.

## 📈 Performance Optimization

### System Requirements
- **CPU:** Multi-core processor (Intel i5/AMD Ryzen 5 or better)
- **RAM:** 8GB minimum, 16GB recommended
- **Storage:** 2GB free space for models and dependencies

### Optimization Tips
- **Start with basic emotion detection** only
- **Add OpenSMILE** only if needed for better accuracy
- **Monitor CPU usage** and adjust detection frequency
- **Use auto-start feature** to avoid manual management
- **Test settings** before going live

## 🎯 Best Practices

### For Streamers
- **Test thoroughly** before going live
- **Start with higher sensitivity** and adjust down based on results
- **Use auto-start feature** for consistent clip creation
- **Monitor the confidence widget** to understand your emotional patterns
- **Engage with viewers** about the AI detection system

### For Content Creation
- **Review clips regularly** and delete low-quality ones
- **Use clips for highlights** and social media content
- **Adjust phrases** based on your streaming language and style
- **Combine with manual clips** for important moments
- **Create themed collections** based on emotions or games

## 🔄 Updates and Maintenance

### Keeping Updated
- **Check releases** regularly for new features and bug fixes
- **Backup your configuration** before updating
- **Test new versions** with non-critical streams first
- **Review changelog** for breaking changes

### Configuration Backup
Your settings are automatically saved in:
- **Windows:** `%APPDATA%\obs-studio\scripts\smartclip_cz_config.json`
- **macOS:** `~/Library/Application Support/obs-studio/scripts/smartclip_cz_config.json`
- **Linux:** `~/.config/obs-studio/scripts/smartclip_cz_config.json`

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenSMILE** team for emotion recognition technology
- **Vosk** project for speech recognition capabilities
- **OBS Studio** community for plugin development support
- **Twitch** for providing comprehensive API access
- **Czech streaming community** for feedback and testing

## 🚀 Future Development

Planned features include:
- **Multi-language support** beyond Czech
- **Advanced clip editing** with automatic highlights
- **Machine learning improvements** for better detection accuracy
- **Integration with other streaming platforms** (YouTube, Facebook)
- **Enhanced visualization options** for streamers
- **Mobile companion app** for remote monitoring

## 🏗️ Building the Installer

### 🔨 Build Process

To build the SmartClip CZ installer from source:

```bash
# Build the installer
python rebuild_installer.py
```

**Output:** `dist/SmartClip_CZ_Installer.exe`

### 🎯 Installer Features

The installer includes:
- ✅ **Automatic Python 3.11.9 detection/installation**
- ✅ **Virtual environment creation with all dependencies**
- ✅ **Integrated Twitch OAuth setup with auto-refresh**
- ✅ **Professional GUI with progress tracking**
- ✅ **Complete OBS integration setup**
- ✅ **Comprehensive error handling and logging**

### 🧪 Testing

```bash
# Test the built installer
python test_installer.py
```

The installer is built using PyInstaller and includes all necessary dependencies for a complete standalone installation experience.

## 🤝 Contributing

We welcome contributions! Please:
1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Test** thoroughly
5. **Submit** a pull request

## 📞 Support

For support, questions, or feature requests:
- **GitHub Issues:** [Report bugs or request features](https://github.com/smartclip-cz/smartclip-cz-python/issues)
- **Documentation:** Check this README

---

**Made with ❤️ for the Czech streaming community**

*Transform your streaming experience with intelligent, automated clip creation!*