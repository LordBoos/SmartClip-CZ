# Changelog

All notable changes to SmartClip CZ will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2024-12-07

### Added
- **Complete Python implementation** - Stable, reliable, and crash-free
- **Multi-modal emotion detection** with Basic, OpenSMILE, and Vosk support
- **Real-time confidence widget** for streaming overlays
- **Auto-start/stop detection** that begins when streaming starts
- **Separate sensitivity controls** for each detection type
- **Professional UI** with emoji indicators and clean design
- **Cross-platform support** for Windows, macOS, and Linux
- **Advanced quality scoring** to reduce false positives
- **Comprehensive logging** and debugging capabilities
- **Live activity monitoring** with timestamps and statistics

### Changed
- **Improved emotion detection accuracy** with multiple detection methods
- **Enhanced Czech speech recognition** using Vosk engine
- **Redesigned user interface** with modern, intuitive controls
- **Optimized performance** with better resource management
- **Simplified installation** with automated installer script

### Fixed
- **Eliminated application crashes** through robust error handling
- **Resolved dependency conflicts** with clean Python environment
- **Fixed locale errors** in confidence widget
- **Improved audio source detection** and handling
- **Enhanced error handling** throughout the application
- **Stabilized Twitch API integration** with better rate limiting

### Removed
- **Legacy build dependencies** and complex compilation requirements
- **Dependency conflicts** by using Python tkinter
- **Complex build process** replaced with simple Python installation
- **Unused PowerShell scripts** and build artifacts
- **Legacy configuration files** replaced with JSON format

## [1.x.x] - Previous Versions

### Legacy Features
- Basic emotion detection using OpenSMILE
- Czech phrase recognition with Vosk
- Twitch clip creation
- Native configuration UI
- Windows-focused support

### Previous Known Issues
- Application stability concerns
- Dependency conflicts
- Complex installation process
- Limited cross-platform support
- Difficult debugging and maintenance

---

## Migration Guide

### From Previous Versions

1. **Clean installation recommended:**
   - Remove any old plugin files from OBS
   - Delete old configuration files

2. **Install current version:**
   - Use the automated installer (`SmartClip_CZ_Installer.exe`)
   - Follow the guided setup process

3. **Configuration setup:**
   - Configure your Twitch API credentials
   - Adjust sensitivity settings to match your preferences
   - Test with your usual streaming setup

### Key Improvements

- **Stability:** Robust error handling and crash prevention
- **Installation:** One-click automated installer
- **Configuration:** Streamlined setup process
- **Cross-platform:** Better support for different operating systems

### Benefits of Migration

- **Stability:** No more crashes or memory issues
- **Performance:** Better resource usage and optimization
- **Features:** New confidence widget and auto-start functionality
- **Maintenance:** Easier updates and bug fixes
- **Cross-platform:** Works on Windows, macOS, and Linux

---

## Support

For issues, questions, or feature requests:
- Check the [README.md](README.md) for configuration help
- Review the [troubleshooting section](README.md#troubleshooting)
- Test with the provided test scripts in the `tests/` directory

## Contributors

- SmartClip CZ Development Team
- Czech streaming community feedback and testing
- OpenSMILE and Vosk project contributors
