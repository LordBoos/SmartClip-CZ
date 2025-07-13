"""
SmartClip CZ - Python Edition
Intelligent OBS Plugin for Automated Twitch Clip Creation

Author: Jakub Kolář (LordBoos)
Email: lordboos@gmail.com
"""

__version__ = "2.0.0"
__author__ = "Jakub Kolář (LordBoos)"
__email__ = "lordboos@gmail.com"
__description__ = "Intelligent OBS Plugin for Automated Twitch Clip Creation Based on Emotional Reactions and Czech Speech Recognition"

# Import all widget modules
try:
    from widgets.obs_confidence_widget import main as obs_widget_main
    from widgets.standalone_confidence_widget import main as standalone_widget_main
    from widgets.simple_confidence_widget import main as simple_widget_main
    from widgets.confidence_widget import main as confidence_widget_main
except ImportError:
    # Widgets are optional and may not be available in all environments
    pass

__all__ = ['obs_widget_main', 'standalone_widget_main', 'simple_widget_main', 'confidence_widget_main']
