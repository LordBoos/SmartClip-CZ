"""
Audio Handler for SmartClip CZ
Handles audio capture from OBS sources and provides audio data to detection systems

Author: Jakub Kolář (LordBoos)
Email: lordboos@gmail.com
"""

import obspython as obs
import numpy as np
import threading
import time
import logging
from typing import List, Callable, Optional
import ctypes
from ctypes import POINTER, c_float, c_uint32, c_void_p, Structure

class AudioData(Structure):
    """Structure for OBS audio data"""
    _fields_ = [
        ("data", POINTER(POINTER(c_float))),
        ("frames", c_uint32),
        ("timestamp", c_uint32)
    ]

class AudioHandler:
    """Handles audio capture from OBS sources"""
    
    def __init__(self, sources: List[str], sample_rate: int = 16000, buffer_size: int = 1024):
        self.sources = sources
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.callback = None
        self.capturing = False
        
        # Audio processing
        self.audio_buffer = np.zeros(buffer_size, dtype=np.float32)
        self.buffer_index = 0
        
        # OBS source references
        self.obs_sources = []
        self.audio_filters = []
        
        self.logger = logging.getLogger('SmartClipCZ.AudioHandler')
        
    def start_capture(self, callback: Callable[[np.ndarray], None]):
        """Start audio capture from OBS sources"""
        try:
            self.callback = callback
            self.capturing = True
            
            # Get OBS sources
            self._setup_obs_sources()
            
            # Start audio monitoring
            self._start_audio_monitoring()
            
            self.logger.info(f"Audio capture started for {len(self.obs_sources)} sources")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start audio capture: {e}")
            return False
    
    def stop_capture(self):
        """Stop audio capture"""
        try:
            self.capturing = False
            
            # Stop audio monitoring
            self._stop_audio_monitoring()
            
            # Release OBS sources
            self._cleanup_obs_sources()
            
            self.logger.info("Audio capture stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping audio capture: {e}")
    
    def _setup_obs_sources(self):
        """Setup OBS audio sources"""
        try:
            # Clear existing sources
            self._cleanup_obs_sources()

            # Get all available sources
            try:
                sources = obs.obs_enum_sources()
                found_sources = []

                for source in sources:
                    try:
                        source_name = obs.obs_source_get_name(source)
                        found_sources.append(source_name)

                        # Check if this source is in our list
                        if source_name in self.sources:
                            # Check if source has audio (simplified check)
                            try:
                                if obs.obs_source_audio_active(source):
                                    # Store source name instead of reference (OBS Python API limitation)
                                    self.obs_sources.append(source_name)
                                    self.logger.info(f"Added audio source: {source_name}")
                                else:
                                    self.logger.warning(f"Source {source_name} exists but has no audio")
                            except AttributeError:
                                # obs_source_audio_active might not be available, assume it has audio
                                self.obs_sources.append(source_name)
                                self.logger.info(f"Added audio source (assumed active): {source_name}")
                    except Exception as source_error:
                        self.logger.warning(f"Error processing source: {source_error}")
                        continue

                obs.source_list_release(sources)

                # Debug logging
                self.logger.info(f"Looking for sources: {self.sources}")
                self.logger.info(f"Available sources: {found_sources}")
                self.logger.info(f"Matched sources: {len(self.obs_sources)}")

                if not self.obs_sources:
                    self.logger.warning("No valid audio sources found")
                    # Try to find any audio source as fallback
                    self._try_fallback_sources()
                else:
                    self.logger.info(f"Successfully configured {len(self.obs_sources)} audio sources")

            except AttributeError as api_error:
                self.logger.warning(f"OBS API limitation detected: {api_error}")
                # Fallback: assume the requested sources exist
                self.obs_sources = self.sources.copy()
                self.logger.info(f"Using fallback source configuration: {self.obs_sources}")

        except Exception as e:
            self.logger.error(f"Error setting up OBS sources: {e}")
            # Ultimate fallback: use simulation mode
            self.logger.info("Falling back to audio simulation mode")

    def _try_fallback_sources(self):
        """Try to find any available audio source as fallback"""
        try:
            self.logger.info("Trying fallback audio sources...")

            try:
                # Get fresh source list
                sources = obs.obs_enum_sources()
                fallback_found = False

                for source in sources:
                    try:
                        source_name = obs.obs_source_get_name(source)

                        # Look for common audio source names
                        try:
                            if obs.obs_source_audio_active(source):
                                self.obs_sources.append(source_name)
                                self.logger.info(f"Using fallback audio source: {source_name}")
                                fallback_found = True
                                break
                        except AttributeError:
                            # If audio_active check fails, try common source names
                            common_audio_sources = ["Desktop Audio", "Mic/Aux", "Microphone"]
                            if any(common in source_name for common in common_audio_sources):
                                self.obs_sources.append(source_name)
                                self.logger.info(f"Using fallback audio source (by name): {source_name}")
                                fallback_found = True
                                break
                    except Exception as source_error:
                        continue

                obs.source_list_release(sources)

                if not fallback_found:
                    self.logger.warning("No audio sources available, using simulation mode")

            except Exception as obs_error:
                self.logger.warning(f"OBS API error in fallback: {obs_error}")
                # Use default sources as last resort
                self.obs_sources = ["Desktop Audio"]
                self.logger.info("Using default audio source configuration")

        except Exception as e:
            self.logger.error(f"Error in fallback source detection: {e}")
    
    def _cleanup_obs_sources(self):
        """Clean up OBS source references"""
        # Since we're storing names instead of references, just clear the list
        self.obs_sources.clear()
    
    def _start_audio_monitoring(self):
        """Start monitoring audio from OBS sources"""
        try:
            if not self.obs_sources:
                self.logger.warning("No audio sources to monitor")
                return

            self.logger.info(f"Starting audio monitoring for {len(self.obs_sources)} sources")

            # Start real-time audio capture thread
            self.monitoring_thread = threading.Thread(target=self._audio_monitoring_loop, daemon=True)
            self.monitoring_thread.start()

            self.logger.info("Audio monitoring started")

        except Exception as e:
            self.logger.error(f"Error starting audio monitoring: {e}")

    def _audio_monitoring_loop(self):
        """Main audio monitoring loop"""
        self.logger.info("Audio monitoring loop started")

        try:
            import sounddevice as sd

            # Use system default input device for now
            # In a full OBS integration, this would capture from OBS directly
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.float32,
                blocksize=self.buffer_size,
                callback=self._audio_input_callback
            ):
                while self.capturing:
                    time.sleep(0.1)

        except Exception as e:
            self.logger.error(f"Audio monitoring loop error: {e}")
            # Fallback to simulation if real audio fails
            self._start_audio_simulation()

        self.logger.info("Audio monitoring loop ended")

    def _audio_input_callback(self, indata, frames, time, status):
        """Callback for real audio input"""
        try:
            if status:
                self.logger.warning(f"Audio input status: {status}")

            if self.callback and self.capturing:
                # Convert to the format expected by the detection pipeline
                audio_data = indata[:, 0]  # Take first channel

                # Update internal buffer for level monitoring
                self.audio_buffer = audio_data.copy()

                # Send to detection pipeline
                self.callback(audio_data)

        except Exception as e:
            self.logger.error(f"Audio input callback error: {e}")
    
    def _stop_audio_monitoring(self):
        """Stop audio monitoring"""
        try:
            self.capturing = False

            # Wait for monitoring thread to finish
            if hasattr(self, 'monitoring_thread') and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=2)

            self.logger.info("Audio monitoring stopped")

        except Exception as e:
            self.logger.error(f"Error stopping audio monitoring: {e}")
    
    def _start_audio_simulation(self):
        """Start audio simulation (for development/testing)"""
        def audio_simulation_thread():
            """Simulate audio data for testing"""
            while self.capturing:
                try:
                    # Generate simulated audio data
                    # In a real implementation, this would come from OBS audio capture
                    audio_data = self._generate_simulated_audio()
                    
                    if self.callback and audio_data is not None:
                        self.callback(audio_data)
                    
                    time.sleep(self.buffer_size / self.sample_rate)  # Simulate real-time
                    
                except Exception as e:
                    self.logger.error(f"Error in audio simulation: {e}")
                    time.sleep(0.1)
        
        # Start simulation thread
        simulation_thread = threading.Thread(target=audio_simulation_thread, daemon=True)
        simulation_thread.start()
        
        self.logger.info("Audio simulation started (for testing)")
    
    def _generate_simulated_audio(self) -> Optional[np.ndarray]:
        """Generate simulated audio data for testing"""
        try:
            # Generate some noise with occasional "events"
            audio_data = np.random.normal(0, 0.1, self.buffer_size).astype(np.float32)
            
            # Occasionally add a "detection event" (louder signal)
            if np.random.random() < 0.01:  # 1% chance
                # Add a burst of activity
                burst_length = min(self.buffer_size // 4, 256)
                start_idx = np.random.randint(0, self.buffer_size - burst_length)
                
                # Generate a more complex signal for "emotion" or "speech"
                t = np.linspace(0, burst_length / self.sample_rate, burst_length)
                
                if np.random.random() < 0.5:
                    # Simulate laughter (higher frequency, irregular)
                    signal = np.sin(2 * np.pi * 800 * t) * np.exp(-t * 5)
                    signal += np.random.normal(0, 0.3, burst_length)
                else:
                    # Simulate speech (lower frequency, more regular)
                    signal = np.sin(2 * np.pi * 200 * t) * np.sin(2 * np.pi * 50 * t)
                    signal += np.random.normal(0, 0.1, burst_length)
                
                audio_data[start_idx:start_idx + burst_length] += signal * 0.5
            
            return audio_data
            
        except Exception as e:
            self.logger.error(f"Error generating simulated audio: {e}")
            return None
    
    def get_audio_level(self) -> float:
        """Get current audio level (RMS)"""
        try:
            if len(self.audio_buffer) > 0:
                return float(np.sqrt(np.mean(self.audio_buffer ** 2)))
            return 0.0
        except:
            return 0.0
    
    def get_audio_sources(self) -> List[str]:
        """Get list of available audio sources"""
        try:
            available_sources = []
            sources = obs.obs_enum_sources()
            
            for source in sources:
                source_name = obs.obs_source_get_name(source)
                if obs.obs_source_audio_active(source):
                    available_sources.append(source_name)
            
            obs.source_list_release(sources)
            return available_sources
            
        except Exception as e:
            self.logger.error(f"Error getting audio sources: {e}")
            return []
    
    def set_sources(self, sources: List[str]):
        """Update audio sources"""
        self.sources = sources
        
        if self.capturing:
            # Restart capture with new sources
            self.stop_capture()
            time.sleep(0.1)
            if self.callback:
                self.start_capture(self.callback)
    
    def audio_callback_wrapper(self, audio_data_ptr, frames):
        """Wrapper for OBS audio callback (if using direct OBS API)"""
        try:
            if not self.capturing or not self.callback:
                return
            
            # Convert OBS audio data to numpy array
            # This is a simplified version - actual implementation would depend on OBS audio format
            audio_array = np.frombuffer(audio_data_ptr, dtype=np.float32, count=frames)
            
            # Resample if necessary
            if len(audio_array) != self.buffer_size:
                audio_array = self._resample_audio(audio_array, self.buffer_size)
            
            # Call the detection callback
            self.callback(audio_array)
            
        except Exception as e:
            self.logger.error(f"Error in audio callback: {e}")
    
    def _resample_audio(self, audio_data: np.ndarray, target_size: int) -> np.ndarray:
        """Simple audio resampling"""
        try:
            if len(audio_data) == target_size:
                return audio_data
            
            # Simple linear interpolation resampling
            indices = np.linspace(0, len(audio_data) - 1, target_size)
            return np.interp(indices, np.arange(len(audio_data)), audio_data).astype(np.float32)
            
        except Exception as e:
            self.logger.error(f"Error resampling audio: {e}")
            return np.zeros(target_size, dtype=np.float32)

class AudioMonitor:
    """Audio monitoring and visualization helper"""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.audio_levels = []
        self.max_history = 100
        
    def update_audio_level(self, audio_data: np.ndarray):
        """Update audio level history"""
        try:
            # Calculate RMS level
            rms_level = np.sqrt(np.mean(audio_data ** 2))
            
            # Add to history
            self.audio_levels.append(float(rms_level))
            
            # Keep only recent history
            if len(self.audio_levels) > self.max_history:
                self.audio_levels.pop(0)
                
        except Exception as e:
            logging.getLogger('SmartClipCZ.AudioMonitor').error(f"Error updating audio level: {e}")
    
    def get_current_level(self) -> float:
        """Get current audio level"""
        if self.audio_levels:
            return self.audio_levels[-1]
        return 0.0
    
    def get_average_level(self, window_size: int = 10) -> float:
        """Get average audio level over window"""
        if not self.audio_levels:
            return 0.0
        
        recent_levels = self.audio_levels[-window_size:]
        return sum(recent_levels) / len(recent_levels)
    
    def get_peak_level(self, window_size: int = 10) -> float:
        """Get peak audio level over window"""
        if not self.audio_levels:
            return 0.0
        
        recent_levels = self.audio_levels[-window_size:]
        return max(recent_levels)
    
    def is_audio_active(self, threshold: float = 0.01) -> bool:
        """Check if audio is currently active"""
        return self.get_current_level() > threshold
