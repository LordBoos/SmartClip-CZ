"""
Emotion Detector for SmartClip CZ
Multi-emotion detection using audio analysis and machine learning

Author: Jakub Kolář (LordBoos)
Email: lordboos@gmail.com
"""

import numpy as np
import logging
from typing import List, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta
import scipy.signal
from scipy.fft import fft
import librosa

class EmotionType(Enum):
    """Emotion types supported by the detector"""
    LAUGHTER = "laughter"
    EXCITEMENT = "excitement"
    SURPRISE = "surprise"
    JOY = "joy"
    ANGER = "anger"
    FEAR = "fear"
    SADNESS = "sadness"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"

class EmotionResult:
    """Result of emotion detection"""
    
    def __init__(self, emotion_type: EmotionType, confidence: float, intensity: float, 
                 features: Dict = None, timestamp: datetime = None):
        self.emotion_type = emotion_type
        self.confidence = confidence
        self.intensity = intensity
        self.features = features or {}
        self.timestamp = timestamp or datetime.now()
        
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'emotion': self.emotion_type.value,
            'confidence': self.confidence,
            'intensity': self.intensity,
            'features': self.features,
            'timestamp': self.timestamp.isoformat(),
            'type': 'emotion'
        }

class AudioFeatureExtractor:
    """Extract audio features for emotion detection"""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.logger = logging.getLogger('SmartClipCZ.FeatureExtractor')
        
    def extract_features(self, audio_data: np.ndarray) -> Dict:
        """Extract comprehensive audio features"""
        try:
            features = {}
            
            # Basic statistics
            features.update(self._extract_basic_features(audio_data))
            
            # Spectral features
            features.update(self._extract_spectral_features(audio_data))
            
            # Prosodic features
            features.update(self._extract_prosodic_features(audio_data))
            
            # Rhythm and timing features
            features.update(self._extract_rhythm_features(audio_data))
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error extracting features: {e}")
            return {}
    
    def _extract_basic_features(self, audio_data: np.ndarray) -> Dict:
        """Extract basic audio features"""
        features = {}
        
        try:
            # Energy and amplitude features
            features['rms_energy'] = float(np.sqrt(np.mean(audio_data ** 2)))
            features['zero_crossing_rate'] = float(np.mean(np.abs(np.diff(np.sign(audio_data)))))
            features['peak_amplitude'] = float(np.max(np.abs(audio_data)))
            features['mean_amplitude'] = float(np.mean(np.abs(audio_data)))
            features['std_amplitude'] = float(np.std(audio_data))
            
            # Dynamic range
            if features['peak_amplitude'] > 0:
                features['dynamic_range'] = features['rms_energy'] / features['peak_amplitude']
            else:
                features['dynamic_range'] = 0.0
                
        except Exception as e:
            self.logger.error(f"Error extracting basic features: {e}")
            
        return features
    
    def _extract_spectral_features(self, audio_data: np.ndarray) -> Dict:
        """Extract spectral features"""
        features = {}
        
        try:
            # FFT analysis
            fft_data = fft(audio_data)
            magnitude = np.abs(fft_data[:len(fft_data)//2])
            freqs = np.fft.fftfreq(len(audio_data), 1/self.sample_rate)[:len(magnitude)]
            
            # Spectral centroid
            if np.sum(magnitude) > 0:
                features['spectral_centroid'] = float(np.sum(freqs * magnitude) / np.sum(magnitude))
            else:
                features['spectral_centroid'] = 0.0
            
            # Spectral rolloff
            cumsum = np.cumsum(magnitude)
            if cumsum[-1] > 0:
                rolloff_idx = np.where(cumsum >= 0.85 * cumsum[-1])[0]
                if len(rolloff_idx) > 0:
                    features['spectral_rolloff'] = float(freqs[rolloff_idx[0]])
                else:
                    features['spectral_rolloff'] = 0.0
            else:
                features['spectral_rolloff'] = 0.0
            
            # Spectral bandwidth
            if features['spectral_centroid'] > 0 and np.sum(magnitude) > 0:
                features['spectral_bandwidth'] = float(
                    np.sqrt(np.sum(((freqs - features['spectral_centroid']) ** 2) * magnitude) / np.sum(magnitude))
                )
            else:
                features['spectral_bandwidth'] = 0.0
            
            # Frequency band energies
            features.update(self._extract_frequency_bands(magnitude, freqs))
            
        except Exception as e:
            self.logger.error(f"Error extracting spectral features: {e}")
            
        return features
    
    def _extract_frequency_bands(self, magnitude: np.ndarray, freqs: np.ndarray) -> Dict:
        """Extract energy in different frequency bands"""
        features = {}
        
        try:
            # Define frequency bands
            bands = {
                'low_freq': (0, 250),      # Low frequencies
                'mid_freq': (250, 2000),   # Mid frequencies (speech)
                'high_freq': (2000, 8000), # High frequencies
                'laughter_freq': (300, 1200), # Typical laughter range
                'excitement_freq': (1000, 4000) # Excitement range
            }
            
            total_energy = np.sum(magnitude ** 2)
            
            for band_name, (low, high) in bands.items():
                band_mask = (freqs >= low) & (freqs <= high)
                band_energy = np.sum(magnitude[band_mask] ** 2)
                
                if total_energy > 0:
                    features[f'{band_name}_ratio'] = float(band_energy / total_energy)
                else:
                    features[f'{band_name}_ratio'] = 0.0
                    
        except Exception as e:
            self.logger.error(f"Error extracting frequency bands: {e}")
            
        return features
    
    def _extract_prosodic_features(self, audio_data: np.ndarray) -> Dict:
        """Extract prosodic features (pitch, rhythm, etc.)"""
        features = {}
        
        try:
            # Simple pitch estimation using autocorrelation
            pitch = self._estimate_pitch(audio_data)
            features['pitch'] = pitch
            
            # Pitch variation
            if len(audio_data) > self.sample_rate // 10:  # At least 100ms
                # Split into segments and estimate pitch variation
                segment_size = len(audio_data) // 10
                pitches = []
                
                for i in range(0, len(audio_data) - segment_size, segment_size):
                    segment = audio_data[i:i + segment_size]
                    segment_pitch = self._estimate_pitch(segment)
                    if segment_pitch > 0:
                        pitches.append(segment_pitch)
                
                if pitches:
                    features['pitch_mean'] = float(np.mean(pitches))
                    features['pitch_std'] = float(np.std(pitches))
                    features['pitch_range'] = float(np.max(pitches) - np.min(pitches))
                else:
                    features['pitch_mean'] = 0.0
                    features['pitch_std'] = 0.0
                    features['pitch_range'] = 0.0
            
        except Exception as e:
            self.logger.error(f"Error extracting prosodic features: {e}")
            
        return features
    
    def _extract_rhythm_features(self, audio_data: np.ndarray) -> Dict:
        """Extract rhythm and timing features"""
        features = {}
        
        try:
            # Onset detection (simplified)
            # Calculate energy in overlapping windows
            window_size = self.sample_rate // 20  # 50ms windows
            hop_size = window_size // 2
            
            energy_curve = []
            for i in range(0, len(audio_data) - window_size, hop_size):
                window = audio_data[i:i + window_size]
                energy = np.sum(window ** 2)
                energy_curve.append(energy)
            
            energy_curve = np.array(energy_curve)
            
            # Find peaks in energy (potential onsets)
            if len(energy_curve) > 3:
                # Simple peak detection
                peaks = []
                threshold = np.mean(energy_curve) + np.std(energy_curve)
                
                for i in range(1, len(energy_curve) - 1):
                    if (energy_curve[i] > energy_curve[i-1] and 
                        energy_curve[i] > energy_curve[i+1] and 
                        energy_curve[i] > threshold):
                        peaks.append(i)
                
                features['onset_count'] = len(peaks)
                
                # Rhythm regularity
                if len(peaks) > 1:
                    intervals = np.diff(peaks)
                    features['rhythm_regularity'] = float(1.0 / (1.0 + np.std(intervals)))
                else:
                    features['rhythm_regularity'] = 0.0
            else:
                features['onset_count'] = 0
                features['rhythm_regularity'] = 0.0
                
        except Exception as e:
            self.logger.error(f"Error extracting rhythm features: {e}")
            
        return features
    
    def _estimate_pitch(self, audio_data: np.ndarray) -> float:
        """Simple pitch estimation using autocorrelation"""
        try:
            # Autocorrelation
            autocorr = np.correlate(audio_data, audio_data, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            
            # Find the first peak after the zero lag
            min_period = self.sample_rate // 800  # Max 800 Hz
            max_period = self.sample_rate // 50   # Min 50 Hz
            
            if len(autocorr) > max_period:
                search_range = autocorr[min_period:max_period]
                if len(search_range) > 0:
                    peak_idx = np.argmax(search_range) + min_period
                    pitch = self.sample_rate / peak_idx
                    return float(pitch)
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Error estimating pitch: {e}")
            return 0.0

class EmotionDetector:
    """Main emotion detection class"""
    
    def __init__(self, enabled_emotions: List[str], sensitivity: float = 0.7):
        self.enabled_emotions = [EmotionType(emotion) for emotion in enabled_emotions if emotion in [e.value for e in EmotionType]]
        self.sensitivity = sensitivity
        self.feature_extractor = AudioFeatureExtractor()
        
        # Detection history for smoothing
        self.detection_history = []
        self.max_history = 10
        
        # Emotion-specific thresholds and patterns
        self.emotion_patterns = self._initialize_emotion_patterns()
        
        self.logger = logging.getLogger('SmartClipCZ.EmotionDetector')
        self.logger.info(f"Emotion detector initialized with {len(self.enabled_emotions)} emotions")
    
    def _initialize_emotion_patterns(self) -> Dict:
        """Initialize emotion detection patterns"""
        return {
            EmotionType.LAUGHTER: {
                'min_frequency_ratio': 0.3,  # High frequency content
                'min_rhythm_regularity': 0.2,  # Irregular rhythm
                'pitch_range_min': 100,  # Wide pitch range
                'energy_threshold': 0.1
            },
            EmotionType.EXCITEMENT: {
                'min_frequency_ratio': 0.25,
                'min_energy': 0.15,
                'pitch_mean_min': 150,  # Higher pitch
                'energy_threshold': 0.12
            },
            EmotionType.SURPRISE: {
                'min_frequency_ratio': 0.2,
                'pitch_range_min': 80,
                'onset_count_min': 2,
                'energy_threshold': 0.08
            },
            EmotionType.JOY: {
                'min_frequency_ratio': 0.2,
                'pitch_mean_min': 120,
                'rhythm_regularity_min': 0.3,
                'energy_threshold': 0.1
            },
            EmotionType.ANGER: {
                'low_freq_ratio_min': 0.3,  # More low frequency
                'energy_threshold': 0.2,
                'pitch_mean_min': 100
            },
            EmotionType.FEAR: {
                'high_freq_ratio_min': 0.25,
                'pitch_std_min': 20,  # Pitch variation
                'energy_threshold': 0.05
            },
            EmotionType.SADNESS: {
                'low_freq_ratio_min': 0.4,
                'pitch_mean_max': 150,  # Lower pitch
                'energy_threshold': 0.03
            }
        }
    
    def detect(self, audio_data: np.ndarray) -> Optional[EmotionResult]:
        """Detect emotions in audio data"""
        try:
            # Extract features
            features = self.feature_extractor.extract_features(audio_data)
            
            if not features:
                return None
            
            # Check each enabled emotion
            best_emotion = None
            best_confidence = 0.0
            
            for emotion_type in self.enabled_emotions:
                confidence = self._calculate_emotion_confidence(emotion_type, features)
                
                if confidence > best_confidence and confidence > self.sensitivity:
                    best_confidence = confidence
                    best_emotion = emotion_type
            
            if best_emotion:
                # Calculate intensity
                intensity = self._calculate_intensity(features)
                
                result = EmotionResult(
                    emotion_type=best_emotion,
                    confidence=best_confidence,
                    intensity=intensity,
                    features=features
                )
                
                # Add to history for smoothing
                self._add_to_history(result)
                
                # Apply smoothing
                smoothed_result = self._apply_smoothing(result)
                
                return smoothed_result
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in emotion detection: {e}")
            return None
    
    def _calculate_emotion_confidence(self, emotion_type: EmotionType, features: Dict) -> float:
        """Calculate confidence for a specific emotion"""
        try:
            if emotion_type not in self.emotion_patterns:
                return 0.0
            
            pattern = self.emotion_patterns[emotion_type]
            confidence_factors = []
            
            # Check energy threshold
            energy = features.get('rms_energy', 0)
            if energy < pattern.get('energy_threshold', 0):
                return 0.0  # Below minimum energy
            
            # Check pattern-specific features
            for feature_name, threshold in pattern.items():
                if feature_name.endswith('_min'):
                    feature_key = feature_name[:-4]
                    if feature_key in features:
                        value = features[feature_key]
                        if value >= threshold:
                            confidence_factors.append(min(1.0, value / threshold))
                        else:
                            confidence_factors.append(0.0)
                
                elif feature_name.endswith('_max'):
                    feature_key = feature_name[:-4]
                    if feature_key in features:
                        value = features[feature_key]
                        if value <= threshold:
                            confidence_factors.append(min(1.0, threshold / max(value, 0.001)))
                        else:
                            confidence_factors.append(0.0)
            
            # Special cases for specific emotions
            if emotion_type == EmotionType.LAUGHTER:
                # Laughter has characteristic frequency patterns
                laughter_ratio = features.get('laughter_freq_ratio', 0)
                high_freq_ratio = features.get('high_freq_ratio', 0)
                confidence_factors.append(laughter_ratio * 2)
                confidence_factors.append(high_freq_ratio)
            
            elif emotion_type == EmotionType.EXCITEMENT:
                # Excitement has high energy and frequency content
                excitement_ratio = features.get('excitement_freq_ratio', 0)
                energy_factor = min(1.0, energy / 0.2)
                confidence_factors.append(excitement_ratio * 1.5)
                confidence_factors.append(energy_factor)
            
            # Calculate overall confidence
            if confidence_factors:
                confidence = np.mean(confidence_factors)
                return float(min(1.0, confidence))
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating emotion confidence: {e}")
            return 0.0
    
    def _calculate_intensity(self, features: Dict) -> float:
        """Calculate emotion intensity based on features"""
        try:
            # Base intensity on energy and spectral characteristics
            energy = features.get('rms_energy', 0)
            spectral_centroid = features.get('spectral_centroid', 0)
            pitch_range = features.get('pitch_range', 0)
            
            # Normalize and combine factors
            energy_factor = min(1.0, energy / 0.3)
            spectral_factor = min(1.0, spectral_centroid / 2000)
            pitch_factor = min(1.0, pitch_range / 200)
            
            intensity = (energy_factor * 0.5 + spectral_factor * 0.3 + pitch_factor * 0.2)
            return float(min(1.0, intensity))
            
        except Exception as e:
            self.logger.error(f"Error calculating intensity: {e}")
            return 0.0
    
    def _add_to_history(self, result: EmotionResult):
        """Add detection result to history"""
        self.detection_history.append(result)
        
        # Keep only recent history
        if len(self.detection_history) > self.max_history:
            self.detection_history.pop(0)
    
    def _apply_smoothing(self, result: EmotionResult) -> EmotionResult:
        """Apply temporal smoothing to reduce false positives"""
        try:
            # If we don't have enough history, return as-is
            if len(self.detection_history) < 3:
                return result
            
            # Check for consistency in recent detections
            recent_emotions = [r.emotion_type for r in self.detection_history[-3:]]
            recent_confidences = [r.confidence for r in self.detection_history[-3:]]
            
            # If the same emotion was detected recently, boost confidence
            same_emotion_count = sum(1 for e in recent_emotions if e == result.emotion_type)
            
            if same_emotion_count >= 2:
                # Boost confidence for consistent detections
                boosted_confidence = min(1.0, result.confidence * 1.2)
                result.confidence = boosted_confidence
            
            # Average confidence with recent detections of same emotion
            same_emotion_confidences = [c for e, c in zip(recent_emotions, recent_confidences) 
                                      if e == result.emotion_type]
            
            if len(same_emotion_confidences) > 1:
                averaged_confidence = np.mean(same_emotion_confidences + [result.confidence])
                result.confidence = float(averaged_confidence)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error applying smoothing: {e}")
            return result
    
    def set_sensitivity(self, sensitivity: float, log_change: bool = True):
        """Update detection sensitivity"""
        old_sensitivity = self.sensitivity
        self.sensitivity = max(0.1, min(1.0, sensitivity))

        if log_change and abs(old_sensitivity - self.sensitivity) > 0.001:
            self.logger.info(f"Emotion sensitivity updated to {self.sensitivity}")
    
    def get_enabled_emotions(self) -> List[str]:
        """Get list of enabled emotions"""
        return [emotion.value for emotion in self.enabled_emotions]
    
    def set_enabled_emotions(self, emotions: List[str]):
        """Update enabled emotions"""
        self.enabled_emotions = [EmotionType(emotion) for emotion in emotions 
                               if emotion in [e.value for e in EmotionType]]
        self.logger.info(f"Enabled emotions updated: {self.get_enabled_emotions()}")
