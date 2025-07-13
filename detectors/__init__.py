"""
SmartClip CZ Detection Components
Emotion and speech detection modules

Author: Jakub Kolář (LordBoos)
Email: lordboos@gmail.com
"""

from .emotion_detector import EmotionDetector, EmotionType
from .opensmile_detector import OpenSMILEDetector
from .vosk_detector import VoskDetector

__all__ = [
    'EmotionDetector',
    'EmotionType',
    'OpenSMILEDetector',
    'VoskDetector'
]
