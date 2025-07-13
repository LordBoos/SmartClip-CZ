#!/usr/bin/env python3
"""
Setup script for SmartClip CZ - Python Edition
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "SmartClip CZ - Intelligent OBS Plugin for Automated Twitch Clip Creation"

# Read requirements
def read_requirements():
    req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(req_path):
        with open(req_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return ['numpy', 'scipy', 'scikit-learn', 'vosk', 'requests', 'sounddevice', 'librosa', 'opensmile']

setup(
    name="smartclip-cz",
    version="2.0.0",
    author="Jakub Kolář (LordBoos)",
    author_email="lordboos@gmail.com",
    description="Intelligent OBS Plugin for Automated Twitch Clip Creation Based on Emotional Reactions and Czech Speech Recognition",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/smartclip-cz/smartclip-cz-python",
    packages=find_packages(),
    py_modules=[
        'smartclip_cz',
        'install_python_plugin'
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Video :: Capture",
        "Topic :: Multimedia :: Sound/Audio :: Analysis",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=read_requirements(),
    extras_require={
        'dev': [
            'pytest>=6.0',
            'pytest-cov>=2.0',
            'black>=21.0',
            'flake8>=3.8',
            'mypy>=0.800',
        ],
        'gui': [
            'PyQt6>=6.0.0',  # For advanced GUI widgets
            'matplotlib>=3.0.0',  # For plotting confidence graphs
        ],
    },
    entry_points={
        'console_scripts': [
            'smartclip-cz-install=install_python_plugin:main',
            'smartclip-cz-widget=widgets.obs_confidence_widget:main',
        ],
    },
    include_package_data=True,
    data_files=[
        ('', ['*.conf', '*.json', 'requirements.txt']),
        ('models', ['models/*']),
    ],
    zip_safe=False,
    keywords="obs plugin twitch clips emotion detection speech recognition czech streaming",
    project_urls={
        "Bug Reports": "https://github.com/smartclip-cz/smartclip-cz-python/issues",
        "Source": "https://github.com/smartclip-cz/smartclip-cz-python",
        "Documentation": "https://github.com/smartclip-cz/smartclip-cz-python/wiki",
    },
)
