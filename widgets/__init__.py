"""
SmartClip CZ Widget Components
Confidence visualization and UI widgets

Author: Jakub Kolář (LordBoos)
Email: lordboos@gmail.com
"""

from .confidence_widget import ConfidenceWidget
from .obs_confidence_widget import OBSConfidenceWidget
from .simple_confidence_widget import SimpleConfidenceWidget
from .standalone_confidence_widget import StandaloneConfidenceWidget

__all__ = [
    'ConfidenceWidget',
    'OBSConfidenceWidget',
    'SimpleConfidenceWidget',
    'StandaloneConfidenceWidget'
]
