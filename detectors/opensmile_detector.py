"""
OpenSMILE Emotion Detector for SmartClip CZ
Advanced ML-based emotion detection using OpenSMILE feature extraction

Author: Jakub Kolář (LordBoos)
Email: lordboos@gmail.com
"""

import os
import subprocess
import tempfile
import numpy as np
import logging
import threading
import time
import csv
from typing import Dict, List, Optional, Callable
from datetime import datetime
import wave

# Try to import the Python opensmile package
try:
    import opensmile
    PYTHON_OPENSMILE_AVAILABLE = True
except ImportError:
    PYTHON_OPENSMILE_AVAILABLE = False

class OpenSMILEDetector:
    """OpenSMILE-based emotion detection"""
    
    def __init__(self, config_file: str = "IS09_emotion.conf", sensitivity: float = 0.7, result_callback: Optional[Callable] = None):
        # Initialize logger first to avoid attribute errors
        self.logger = logging.getLogger('SmartClipCZ.OpenSMILE')
        # Don't set level here - respect global logging configuration

        self.config_file = config_file
        self.sensitivity = sensitivity
        self.running = False
        self.result_callback = result_callback  # Callback for detection results

        # OpenSMILE setup - prefer Python package over executable
        self.use_python_opensmile = PYTHON_OPENSMILE_AVAILABLE
        self.opensmile_exe = None
        self.config_path = None
        self.smile = None

        if self.use_python_opensmile:
            self._setup_python_opensmile()
        else:
            # Fallback to executable
            self.opensmile_exe = self._find_opensmile_executable()
            self.config_path = self._find_config_file(config_file)
        
        # Audio processing
        self.sample_rate = 16000
        self.audio_buffer = []
        self.buffer_duration = 2.0  # Process 2-second chunks
        self.buffer_size = int(self.sample_rate * self.buffer_duration)
        
        # Detection thread
        self.detection_thread = None
        self.audio_queue = []
        self.queue_lock = threading.Lock()
        
        # Emotion mapping
        self.emotion_mapping = self._initialize_emotion_mapping()
        
        # Statistics
        self.detection_count = 0
        self.last_detection_time = None

        # Validate setup
        self.is_available = self._validate_setup()
        
        if self.is_available:
            if self.use_python_opensmile:
                self.logger.info("OpenSMILE detector initialized successfully (using Python package)")
            else:
                self.logger.info("OpenSMILE detector initialized successfully (using executable)")
        else:
            self.logger.warning("OpenSMILE detector not available - check installation")

    def _setup_python_opensmile(self):
        """Setup Python OpenSMILE package"""
        try:
            # Initialize OpenSMILE with emotion feature set
            self.smile = opensmile.Smile(
                feature_set=opensmile.FeatureSet.eGeMAPSv02,
                feature_level=opensmile.FeatureLevel.Functionals,
            )
            self.logger.info("Python OpenSMILE initialized with eGeMAPSv02 feature set")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Python OpenSMILE: {e}")
            self.smile = None
            return False

    def _find_opensmile_executable(self) -> Optional[str]:
        """Find OpenSMILE executable"""
        try:
            # Common OpenSMILE executable names and paths
            possible_names = [
                "SMILExtract.exe",
                "SMILExtract",
                "opensmile.exe",
                "opensmile"
            ]
            
            # Check in plugin directory first
            plugin_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Check plugin directory and subdirectories
            for root, dirs, files in os.walk(plugin_dir):
                for filename in files:
                    if filename in possible_names:
                        exe_path = os.path.join(root, filename)
                        if os.path.isfile(exe_path):
                            self.logger.info(f"Found OpenSMILE executable: {exe_path}")
                            return exe_path
            
            # Check system PATH
            for name in possible_names:
                try:
                    result = subprocess.run(['where', name] if os.name == 'nt' else ['which', name], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        exe_path = result.stdout.strip()
                        self.logger.info(f"Found OpenSMILE in PATH: {exe_path}")
                        return exe_path
                except:
                    continue
            
            self.logger.warning("OpenSMILE executable not found")
            return None
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error finding OpenSMILE executable: {e}")
            return None
    
    def _find_config_file(self, config_name: str) -> Optional[str]:
        """Find OpenSMILE configuration file"""
        try:
            plugin_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Common config locations
            possible_paths = [
                os.path.join(plugin_dir, "configs", config_name),
                os.path.join(plugin_dir, "opensmile_configs", config_name),
                os.path.join(plugin_dir, config_name),
                os.path.join(plugin_dir, "..", "resources", "opensmile", config_name),
                os.path.join(plugin_dir, "..", "SmartClip_CZ_v5.0_Installer", config_name)
            ]
            
            for path in possible_paths:
                if os.path.isfile(path):
                    self.logger.info(f"Found OpenSMILE config: {path}")
                    return path
            
            # Create a basic config if none found
            basic_config_path = os.path.join(plugin_dir, "basic_emotion.conf")
            if not os.path.exists(basic_config_path):
                self._create_basic_config(basic_config_path)
            
            return basic_config_path
            
        except Exception as e:
            self.logger.error(f"Error finding config file: {e}")
            return None
    
    def _create_basic_config(self, config_path: str):
        """Create a basic OpenSMILE configuration for emotion detection"""
        try:
            basic_config = """
// Basic emotion detection configuration for SmartClip CZ
[componentInstances:cComponentManager]
instance[dataMemory].type=cDataMemory
instance[waveIn].type=cWaveSource
instance[framer].type=cFramer
instance[windower].type=cWindower
instance[fft].type=cTransformFFT
instance[fftmag].type=cFFTmagphase
instance[melspec].type=cMelspec
instance[mfcc].type=cMfcc
instance[energy].type=cEnergy
instance[csvSink].type=cCsvSink

[waveIn:cWaveSource]
writer.dmLevel=wave
filename=\\cm[inputfile(I){test.wav}:name of input file]
monoMixdown=1

[framer:cFramer]
reader.dmLevel=wave
writer.dmLevel=frames
frameSize = 0.025
frameStep = 0.010
frameCenterSpecial = left

[windower:cWindower]
reader.dmLevel=frames
writer.dmLevel=winframes
winFunc = ham
gain = 1.0

[fft:cTransformFFT]
reader.dmLevel=winframes
writer.dmLevel=fft

[fftmag:cFFTmagphase]
reader.dmLevel=fft
writer.dmLevel=fftmag

[melspec:cMelspec]
reader.dmLevel=fftmag
writer.dmLevel=melspec
htkcompatible = 1
nBands = 26
lofreq = 0
hifreq = 8000

[mfcc:cMfcc]
reader.dmLevel=melspec
writer.dmLevel=mfcc
firstMfcc = 1
lastMfcc = 12
cepLifter = 22.0

[energy:cEnergy]
reader.dmLevel=winframes
writer.dmLevel=energy
rms = 1
log = 1

[csvSink:cCsvSink]
reader.dmLevel=mfcc,energy
filename=\\cm[outputfile(O){output.csv}:name of output file]
delimChar=;
append=0
timestamp=1
number=1
printHeader=1
"""
            
            with open(config_path, 'w') as f:
                f.write(basic_config)
            
            self.logger.info(f"Created basic OpenSMILE config: {config_path}")
            
        except Exception as e:
            self.logger.error(f"Error creating basic config: {e}")
    
    def _initialize_emotion_mapping(self) -> Dict:
        """Initialize emotion mapping from OpenSMILE features"""
        return {
            'arousal_high': ['excitement', 'anger', 'fear', 'surprise'],
            'arousal_low': ['sadness', 'neutral'],
            'valence_positive': ['joy', 'excitement', 'laughter'],
            'valence_negative': ['anger', 'fear', 'sadness'],
            'energy_high': ['laughter', 'excitement', 'anger'],
            'energy_low': ['sadness', 'neutral']
        }
    
    def _validate_setup(self) -> bool:
        """Validate OpenSMILE setup"""
        try:
            if self.use_python_opensmile:
                # Validate Python OpenSMILE
                if self.smile is None:
                    self.logger.warning("Python OpenSMILE not initialized")
                    return False

                # Test with a small dummy signal
                try:
                    import numpy as np
                    dummy_signal = np.random.randn(1000)  # 1000 samples
                    features = self.smile.process_signal(dummy_signal, sampling_rate=16000)
                    if features is not None and len(features) > 0:
                        self.logger.info("Python OpenSMILE validation successful")
                        return True
                    else:
                        self.logger.warning("Python OpenSMILE test returned empty features")
                        return False
                except Exception as e:
                    self.logger.warning(f"Python OpenSMILE validation failed: {e}")
                    return False
            else:
                # Validate executable OpenSMILE
                if not self.opensmile_exe or not os.path.isfile(self.opensmile_exe):
                    self.logger.warning("OpenSMILE executable not found")
                    return False

                if not self.config_path or not os.path.isfile(self.config_path):
                    self.logger.warning("OpenSMILE config file not found")
                    return False

                # Test OpenSMILE execution
                try:
                    result = subprocess.run([self.opensmile_exe, '-h'],
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode != 0:
                        self.logger.warning("OpenSMILE executable test failed")
                        return False
                except subprocess.TimeoutExpired:
                    # Help command might hang, but executable exists
                    pass
                except Exception as e:
                    self.logger.warning(f"OpenSMILE test execution failed: {e}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating OpenSMILE setup: {e}")
            return False
    
    def start_detection(self):
        """Start OpenSMILE detection"""
        if not self.is_available:
            self.logger.warning("Cannot start OpenSMILE detection - not available")
            return False
        
        if self.running:
            return True
        
        try:
            self.running = True
            self.detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
            self.detection_thread.start()
            
            self.logger.info("OpenSMILE detection started")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting OpenSMILE detection: {e}")
            self.running = False
            return False
    
    def stop_detection(self):
        """Stop OpenSMILE detection"""
        if not self.running:
            return
        
        try:
            self.running = False
            
            if self.detection_thread and self.detection_thread.is_alive():
                self.detection_thread.join(timeout=2)
            
            self.logger.info("OpenSMILE detection stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping OpenSMILE detection: {e}")
    
    def process_audio(self, audio_data: np.ndarray) -> Optional[Dict]:
        """Process audio data and add to queue"""
        try:
            if not self.is_available or not self.running:
                return None
            
            # Add to buffer
            self.audio_buffer.extend(audio_data.tolist())
            
            # Check if we have enough data to process
            if len(self.audio_buffer) >= self.buffer_size:
                # Extract chunk for processing
                chunk = np.array(self.audio_buffer[:self.buffer_size], dtype=np.float32)
                self.audio_buffer = self.audio_buffer[self.buffer_size//2:]  # 50% overlap
                
                # Add to processing queue
                with self.queue_lock:
                    self.audio_queue.append(chunk)
                    
                    # Limit queue size
                    if len(self.audio_queue) > 5:
                        self.audio_queue.pop(0)
            
            return None  # Actual results come from detection thread
            
        except Exception as e:
            self.logger.error(f"Error processing audio: {e}")
            return None
    
    def _detection_loop(self):
        """Main detection processing loop"""
        self.logger.info("OpenSMILE detection loop started")
        
        while self.running:
            try:
                # Get audio chunk from queue
                chunk = None
                with self.queue_lock:
                    if self.audio_queue:
                        chunk = self.audio_queue.pop(0)
                
                if chunk is not None:
                    # Process chunk with OpenSMILE
                    result = self._process_chunk_with_opensmile(chunk)
                    
                    if result:
                        self.detection_count += 1
                        self.last_detection_time = datetime.now()

                        # Call the result callback if provided
                        if self.result_callback:
                            try:
                                self.result_callback(result)
                            except Exception as callback_error:
                                self.logger.error(f"Error in OpenSMILE result callback: {callback_error}")

                        # Log the detection
                        emotion = result.get('emotion', 'unknown')
                        confidence = result.get('confidence', 0)
                        self.logger.info(f"OpenSMILE detected: {emotion} ({confidence:.2f})")
                
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
                
            except Exception as e:
                self.logger.error(f"Error in OpenSMILE detection loop: {e}")
                time.sleep(1)
        
        self.logger.info("OpenSMILE detection loop ended")
    
    def _process_chunk_with_opensmile(self, audio_chunk: np.ndarray) -> Optional[Dict]:
        """Process audio chunk with OpenSMILE"""
        try:
            if self.use_python_opensmile and self.smile:
                return self._process_with_python_opensmile(audio_chunk)
            else:
                return self._process_with_executable_opensmile(audio_chunk)
        except Exception as e:
            self.logger.error(f"Error processing chunk with OpenSMILE: {e}")
            return None

    def _process_with_python_opensmile(self, audio_chunk: np.ndarray) -> Optional[Dict]:
        """Process audio chunk with Python OpenSMILE"""
        try:
            # Process the audio chunk directly
            features = self.smile.process_signal(audio_chunk, sampling_rate=self.sample_rate)

            if features is None or len(features) == 0:
                return None

            # Convert features to emotion detection result
            emotion_result = self._analyze_python_features_for_emotion(features)
            return emotion_result

        except Exception as e:
            self.logger.error(f"Error processing with Python OpenSMILE: {e}")
            return None

    def _process_with_executable_opensmile(self, audio_chunk: np.ndarray) -> Optional[Dict]:
        """Process audio chunk with executable OpenSMILE"""
        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_file:
                wav_filename = wav_file.name

            with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as csv_file:
                csv_filename = csv_file.name
            
            try:
                # Save audio to WAV file
                self._save_audio_to_wav(audio_chunk, wav_filename)
                
                # Run OpenSMILE
                cmd = [
                    self.opensmile_exe,
                    '-C', self.config_path,
                    '-I', wav_filename,
                    '-O', csv_filename
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    # Parse results
                    emotion_result = self._parse_opensmile_output(csv_filename)
                    return emotion_result
                else:
                    self.logger.warning(f"OpenSMILE execution failed: {result.stderr}")
                    return None
                    
            finally:
                # Clean up temporary files
                try:
                    os.unlink(wav_filename)
                    os.unlink(csv_filename)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            self.logger.warning("OpenSMILE execution timed out")
            return None
        except Exception as e:
            self.logger.error(f"Error processing chunk with OpenSMILE: {e}")
            return None
    
    def _save_audio_to_wav(self, audio_data: np.ndarray, filename: str):
        """Save audio data to WAV file"""
        try:
            # Normalize audio data
            audio_data = np.clip(audio_data, -1.0, 1.0)
            
            # Convert to 16-bit PCM
            audio_int16 = (audio_data * 32767).astype(np.int16)
            
            # Save as WAV
            with wave.open(filename, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_int16.tobytes())
                
        except Exception as e:
            self.logger.error(f"Error saving audio to WAV: {e}")
            raise
    
    def _parse_opensmile_output(self, csv_filename: str) -> Optional[Dict]:
        """Parse OpenSMILE CSV output"""
        try:
            if not os.path.exists(csv_filename):
                return None
            
            # Read CSV file
            features = {}
            with open(csv_filename, 'r') as f:
                reader = csv.reader(f, delimiter=';')
                
                # Skip header if present
                first_row = next(reader, None)
                if first_row and 'frameTime' in first_row[0]:
                    # This is a header row, read the actual data
                    data_row = next(reader, None)
                    if data_row:
                        # Parse feature values
                        for i, value in enumerate(data_row[1:]):  # Skip timestamp
                            try:
                                features[f'feature_{i}'] = float(value)
                            except ValueError:
                                continue
                else:
                    # First row is data
                    if first_row:
                        for i, value in enumerate(first_row[1:]):  # Skip timestamp
                            try:
                                features[f'feature_{i}'] = float(value)
                            except ValueError:
                                continue
            
            if not features:
                return None
            
            # Analyze features for emotion detection
            emotion_result = self._analyze_features_for_emotion(features)

            if emotion_result:
                detection_threshold = self._map_sensitivity_to_threshold(self.sensitivity)
                raw_confidence = emotion_result.get('confidence', 0)

                if raw_confidence > detection_threshold:
                    # Normalize confidence for consistent reporting
                    emotion_result['confidence'] = self._normalize_confidence_for_sensitivity(raw_confidence, self.sensitivity)
                    return emotion_result

            return None
            
        except Exception as e:
            self.logger.error(f"Error parsing OpenSMILE output: {e}")
            return None
    
    def _analyze_features_for_emotion(self, features: Dict) -> Optional[Dict]:
        """Analyze OpenSMILE features for emotion detection"""
        try:
            # This is a simplified emotion analysis
            # In a real implementation, you would use trained models
            
            # Calculate basic statistics
            feature_values = list(features.values())
            if not feature_values:
                return None
            
            mean_value = np.mean(feature_values)
            std_value = np.std(feature_values)
            max_value = np.max(feature_values)
            
            # Simple heuristic-based emotion detection
            # This should be replaced with proper ML models
            
            detected_emotion = 'neutral'
            confidence = 0.0
            
            # High energy and variation suggests excitement or laughter
            if mean_value > 0.5 and std_value > 0.3:
                if max_value > 1.0:
                    detected_emotion = 'laughter'
                    confidence = min(0.9, mean_value + std_value)
                else:
                    detected_emotion = 'excitement'
                    confidence = min(0.8, mean_value + std_value * 0.5)
            
            # High variation with moderate energy suggests surprise
            elif std_value > 0.4 and mean_value > 0.2:
                detected_emotion = 'surprise'
                confidence = min(0.7, std_value + mean_value * 0.3)
            
            # Low energy suggests sadness or neutral
            elif mean_value < 0.2:
                if std_value < 0.1:
                    detected_emotion = 'sadness'
                    confidence = min(0.6, 0.3 - mean_value)
                else:
                    detected_emotion = 'neutral'
                    confidence = 0.4
            
            # Moderate energy with high variation suggests anger
            elif mean_value > 0.3 and std_value > 0.25:
                detected_emotion = 'anger'
                confidence = min(0.75, mean_value + std_value * 0.3)
            
            detection_threshold = self._map_sensitivity_to_threshold(self.sensitivity)

            if confidence > detection_threshold:
                # Normalize confidence for consistent reporting
                final_confidence = self._normalize_confidence_for_sensitivity(confidence, self.sensitivity)

                return {
                    'emotion': detected_emotion,
                    'confidence': final_confidence,
                    'features': features,
                    'type': 'opensmile',
                    'timestamp': datetime.now().isoformat()
                }

            return None
            
        except Exception as e:
            self.logger.error(f"Error analyzing features for emotion: {e}")
            return None
    
    def get_statistics(self) -> Dict:
        """Get OpenSMILE detector statistics"""
        return {
            'is_available': self.is_available,
            'running': self.running,
            'detection_count': self.detection_count,
            'last_detection_time': self.last_detection_time.isoformat() if self.last_detection_time else None,
            'opensmile_exe': self.opensmile_exe,
            'config_path': self.config_path,
            'sensitivity': self.sensitivity
        }
    
    def set_sensitivity(self, sensitivity: float, log_change: bool = True):
        """Update detection sensitivity"""
        old_sensitivity = self.sensitivity
        self.sensitivity = max(0.1, min(1.0, sensitivity))

        if log_change and abs(old_sensitivity - self.sensitivity) > 0.001:
            threshold = self._map_sensitivity_to_threshold(self.sensitivity)
            self.logger.info(f"OpenSMILE sensitivity updated to {self.sensitivity} (detection threshold: {threshold:.3f})")

    def _map_sensitivity_to_threshold(self, sensitivity: float) -> float:
        """Map UI sensitivity (0.1-1.0) to internal detection threshold"""
        # Much more conservative mapping to reduce false positives
        # Map 0.1 -> 0.9 (very high threshold, almost no detections)
        # Map 0.5 -> 0.6 (high threshold, only strong signals)
        # Map 0.9 -> 0.3 (moderate threshold, clear emotions)
        # Map 1.0 -> 0.2 (lower threshold, more sensitive)

        # More conservative exponential mapping
        inverted_sensitivity = 1.0 - sensitivity  # 0.9 to 0.0

        # Much higher thresholds to reduce false positives
        if sensitivity >= 0.8:
            # Fine control in high sensitivity range
            threshold = 0.2 + (1.0 - sensitivity) * 0.5  # 0.2 to 0.3
        else:
            # Exponential curve for lower sensitivities with much higher thresholds
            threshold = 0.3 + (inverted_sensitivity ** 0.8) * 0.6  # 0.3 to 0.9

        return max(0.2, min(0.9, threshold))

    def _normalize_confidence_for_sensitivity(self, raw_confidence: float, sensitivity: float) -> float:
        """Normalize confidence based on sensitivity for consistent reporting"""
        # Scale confidence to be more meaningful relative to sensitivity
        # Higher sensitivity should report higher confidence values

        if raw_confidence <= 0:
            return 0.0

        # Apply sensitivity-based scaling
        # At high sensitivity (1.0), boost confidence more
        # At low sensitivity (0.1), keep confidence lower
        sensitivity_factor = 0.5 + (sensitivity * 0.5)  # 0.55 to 1.0

        normalized = min(1.0, raw_confidence * sensitivity_factor)

        # Ensure minimum confidence for any detection
        return max(0.3, normalized)

    def _analyze_python_features_for_emotion(self, features) -> Optional[Dict]:
        """Analyze Python OpenSMILE features for emotion detection"""
        try:
            # Convert pandas DataFrame to dictionary if needed
            if hasattr(features, 'iloc'):
                # It's a pandas DataFrame, get the first row as a dictionary
                feature_dict = features.iloc[0].to_dict()
            else:
                feature_dict = features

            # Extract key features for emotion detection
            # eGeMAPSv02 includes features like F0, loudness, spectral features, etc.

            # Get some key features (these are common in eGeMAPSv02)
            f0_mean = feature_dict.get('F0semitoneFrom27.5Hz_sma3nz_amean', 0)
            loudness_mean = feature_dict.get('loudness_sma3_amean', 0)
            spectral_centroid = feature_dict.get('spectralCentroid_sma3_amean', 0)
            hnr_mean = feature_dict.get('HNRdBACF_sma3nz_amean', 0)

            # Additional features for better detection
            jitter = feature_dict.get('jitterLocal_sma3nz_amean', 0)
            shimmer = feature_dict.get('shimmerLocaldB_sma3nz_amean', 0)

            # Debug logging (only log occasionally to avoid spam)
            if hasattr(self, '_debug_counter'):
                self._debug_counter += 1
            else:
                self._debug_counter = 1

            if self._debug_counter % 50 == 0:  # Log every 50th analysis
                self.logger.debug(f"OpenSMILE features - F0: {f0_mean:.3f}, Loudness: {loudness_mean:.3f}, HNR: {hnr_mean:.3f}")

            # Simple emotion classification based on acoustic features
            detected_emotion = 'neutral'
            confidence = 0.0

            # Normalize features to more reasonable ranges for detection
            # eGeMAPSv02 features can have wide ranges, so we need to adapt thresholds

            # For laughter detection - look for high energy and pitch variation
            energy_score = abs(loudness_mean) if loudness_mean != 0 else 0
            pitch_score = abs(f0_mean) if f0_mean != 0 else 0
            voice_quality_score = abs(hnr_mean) if hnr_mean != 0 else 0

            # Much more conservative detection to avoid false positives during normal speech
            # Laughter requires very specific acoustic characteristics

            # Laughter detection: requires high energy AND significant pitch variation AND voice irregularity
            if (energy_score > 0.15 and pitch_score > 0.1 and
                (voice_quality_score > 0.05 or abs(jitter) > 0.01)):
                # Additional check: laughter usually has rapid energy fluctuations
                detected_emotion = 'laughter'
                # Conservative confidence calculation
                confidence = min(0.8, (energy_score + pitch_score + voice_quality_score) * 1.2)

            # Excitement: high energy with moderate pitch variation but good voice quality
            elif (energy_score > 0.2 and pitch_score > 0.08 and
                  voice_quality_score > 0.03 and abs(jitter) < 0.008):
                detected_emotion = 'excitement'
                confidence = min(0.7, (energy_score + pitch_score) * 1.0)

            # Anger: very high energy with low pitch variation and harsh voice quality
            elif (energy_score > 0.25 and pitch_score < 0.05 and
                  voice_quality_score < 0.02):
                detected_emotion = 'anger'
                confidence = min(0.75, energy_score * 2.0)

            # Default: no emotion detected for normal speech patterns
            else:
                detected_emotion = 'neutral'
                confidence = 0.0

            # Apply proper sensitivity mapping instead of aggressive boosting
            # Map sensitivity (0.1-1.0) to detection threshold (0.05-0.8)
            detection_threshold = self._map_sensitivity_to_threshold(self.sensitivity)

            # Apply detection threshold
            if confidence > detection_threshold:
                # Apply final confidence normalization based on sensitivity
                final_confidence = self._normalize_confidence_for_sensitivity(confidence, self.sensitivity)

                self.logger.info(f"OpenSMILE detected {detected_emotion} with confidence {final_confidence:.3f} (raw: {confidence:.3f}, threshold: {detection_threshold:.3f})")
                return {
                    'emotion': detected_emotion,
                    'confidence': final_confidence,
                    'features': feature_dict,
                    'type': 'opensmile_python',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                # Debug logging for failed detections (occasionally)
                if self._debug_counter % 100 == 0:
                    self.logger.debug(f"OpenSMILE: {detected_emotion} confidence {confidence:.3f} below threshold {detection_threshold:.3f} (sensitivity: {self.sensitivity:.3f})")

            return None

        except Exception as e:
            self.logger.error(f"Error analyzing Python OpenSMILE features: {e}")
            return None
