# Contributing to SmartClip CZ

Thank you for your interest in contributing to SmartClip CZ! This document provides guidelines for contributing to the project.

## 🚀 Getting Started

### Prerequisites
- Python 3.11.9 or higher
- OBS Studio 29.0 or higher
- Git for version control

### Development Setup
1. **Clone the repository**
   ```bash
   git clone https://github.com/LordBoos/SmartClip-CZ.git
   cd SmartClip-CZ
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Test the installation**
   ```bash
   python smartclip_cz.py
   ```

## 🛠️ Development Guidelines

### Code Style
- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and concise

### Project Structure
```
SmartClip-CZ/
├── core/                 # Core functionality modules
├── detectors/           # Detection algorithms (legacy)
├── widgets/             # UI widgets for confidence display
├── models/              # ML models and configurations
├── dist/                # Built installer
├── smartclip_cz.py     # Main OBS script
├── final_installer.py  # Installer source
└── requirements.txt    # Python dependencies
```

### Testing
- Test all changes with OBS Studio
- Verify installer functionality
- Test OAuth token refresh mechanism
- Ensure cross-platform compatibility

## 🐛 Reporting Issues

### Bug Reports
Please include:
- **OBS Studio version**
- **Python version**
- **Operating system**
- **Steps to reproduce**
- **Expected vs actual behavior**
- **Log files** (if applicable)

### Feature Requests
Please include:
- **Clear description** of the feature
- **Use case** and benefits
- **Proposed implementation** (if you have ideas)

## 🔧 Pull Request Process

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
   - Follow coding standards
   - Add appropriate logging
   - Update documentation if needed
4. **Test thoroughly**
   - Test with OBS Studio
   - Verify installer works
   - Check for regressions
5. **Commit with clear messages**
   ```bash
   git commit -m "Add: Brief description of changes"
   ```
6. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

### PR Requirements
- ✅ **Clear description** of changes
- ✅ **Testing performed** and results
- ✅ **No breaking changes** (or clearly documented)
- ✅ **Updated documentation** if needed
- ✅ **Follows project coding style**

## 🎯 Areas for Contribution

### High Priority
- **Cross-platform testing** (macOS, Linux)
- **Performance optimizations**
- **Additional language support**
- **UI/UX improvements**

### Medium Priority
- **Additional emotion detection models**
- **Enhanced quality scoring algorithms**
- **Better error handling and recovery**
- **Documentation improvements**

### Low Priority
- **Code refactoring**
- **Additional activation phrase languages**
- **Advanced configuration options**

## 📝 Documentation

### Code Documentation
- Add docstrings to all public functions
- Include parameter types and return values
- Provide usage examples for complex functions

### User Documentation
- Update README.md for new features
- Add installation instructions for new dependencies
- Include troubleshooting guides

## 🔐 Security

### Sensitive Data
- **Never commit** API keys, tokens, or credentials
- Use environment variables for sensitive configuration
- Follow OAuth 2.0 best practices

### Reporting Security Issues
Please report security vulnerabilities privately to the maintainers rather than creating public issues.

## 📄 License

By contributing to SmartClip CZ, you agree that your contributions will be licensed under the same license as the project (MIT License).

## 🤝 Community

### Communication
- **GitHub Issues** for bugs and feature requests
- **GitHub Discussions** for questions and ideas
- **Pull Requests** for code contributions

### Code of Conduct
- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Maintain a professional environment

## 🙏 Recognition

Contributors will be recognized in:
- **CHANGELOG.md** for significant contributions
- **README.md** contributors section
- **Release notes** for major features

Thank you for contributing to SmartClip CZ! 🎉
