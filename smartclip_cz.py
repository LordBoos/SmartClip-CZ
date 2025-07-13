#!/usr/bin/env python3
"""
SmartClip CZ - Python OBS Plugin
Advanced Emotion Detection for Czech Gaming Streamers

Complete Python rewrite with all original features:
- Multi-emotion detection (8 types)
- Czech speech recognition with Vosk
- OpenSMILE ML emotion detection
- Real-time confidence visualization
- Smart clip quality scoring
- Twitch API integration

Author: Jakub Kolář (LordBoos)
Email: lordboos@gmail.com
GitHub: https://github.com/LordBoos
"""

# Setup virtual environment if available
try:
    import os
    import sys

    # Try to import venv setup from the same directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_setup_path = os.path.join(script_dir, "setup_venv.py")

    if os.path.exists(venv_setup_path):
        # Execute the venv setup script
        with open(venv_setup_path, 'r', encoding='utf-8') as f:
            venv_setup_code = f.read()
        exec(venv_setup_code)
except Exception as e:
    # If venv setup fails, continue with system Python
    print(f"⚠️ Virtual environment setup failed, using system Python: {e}")

import obspython as obs
import threading
import time
import json
import traceback
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import queue
import numpy as np

# Add plugin directory to Python path for imports
plugin_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, plugin_dir)

try:
    from core.audio_handler import AudioHandler
    from detectors.emotion_detector import EmotionDetector, EmotionType
    from detectors.opensmile_detector import OpenSMILEDetector
    from detectors.vosk_detector import VoskDetector
    from core.twitch_api import TwitchAPI
    from core.clip_manager import ClipManager
    from core.quality_scorer import QualityScorer
    from core.config_manager import ConfigManager
    from core.ui_manager import UIManager
except ImportError as e:
    print(f"Import error: {e}")
    # We'll define minimal versions inline if imports fail

class SmartClipCZ:
    """Main plugin class coordinating all components"""
    
    def __init__(self):
        self.version = "2.0.0"
        self.running = False
        self.config = {}
        
        # Core components
        self.config_manager = ConfigManager()
        self.audio_handler = None
        self.emotion_detector = None
        self.opensmile_detector = None
        self.vosk_detector = None
        self.twitch_api = None
        self.clip_manager = None
        self.quality_scorer = None
        self.ui_manager = None
        
        # Threading
        self.detection_thread = None
        self.audio_queue = queue.Queue(maxsize=100)
        
        # Detection coordination
        self.last_detection_time = datetime.now() - timedelta(seconds=10)
        self.detection_cooldown = timedelta(seconds=2)

        # Streaming state monitoring
        self.is_streaming = False
        self.stream_check_timer = None

        # Confidence widget data
        self.confidence_data = {
            'basic_emotion': 0.0,
            'opensmile': 0.0,
            'vosk': 0.0,
            'last_emotion': 'neutral',
            'last_phrase': ''
        }
        
        # Statistics
        self.stats = {
            'total_detections': 0,
            'clips_created': 0,
            'clips_rejected': 0,
            'emotions_detected': {},
            'phrases_detected': {},
            'session_start': datetime.now()
        }
        
        # Initialize a basic logger immediately
        self.logger = logging.getLogger('SmartClipCZ')
        self.logger.setLevel(logging.INFO) # Default to INFO level until fully configured

        # Initialize language support
        self.texts = self.get_texts()
        
    def setup_logging(self):
        """Setup logging for the plugin"""
        self._configure_logging()

    def _configure_logging(self):
        """Configure logging based on enable_debug_logging setting"""
        root_logger = logging.getLogger()

        # Remove all existing handlers to prevent duplicates and reconfigure cleanly
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            handler.close() # Close handlers to release file locks

        enable_debug_logging = self.config.get("advanced_settings", {}).get("enable_debug_logging", False)

        if enable_debug_logging:
            # Set root logger level to DEBUG
            root_logger.setLevel(logging.DEBUG)

            # Add FileHandler
            log_file = os.path.join(plugin_dir, 'smartclip_cz.log')
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter('[%(name)s] %(asctime)s - %(levelname)s - %(message)s'))
            root_logger.addHandler(file_handler)

            # Add StreamHandler (for console output)
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(logging.Formatter('[%(name)s] %(asctime)s - %(levelname)s - %(message)s'))
            root_logger.addHandler(stream_handler)

            self.logger.info("Debug logging enabled - full logging active")
        else:
            # Set root logger level to CRITICAL to suppress all output
            root_logger.setLevel(logging.CRITICAL)
            # Add a NullHandler to ensure no output goes anywhere
            root_logger.addHandler(logging.NullHandler())
            # When logging is disabled, show absolutely nothing
            
        # Update all existing loggers to respect the new logging level
        self._update_all_loggers(root_logger.level)

        self.logger = logging.getLogger('SmartClipCZ')

        # Update all existing loggers to respect the new logging level
        self._update_all_loggers(logging.DEBUG if enable_debug_logging else logging.CRITICAL)

        # The logging state message is now handled within the if/else block above

    def _update_all_loggers(self, level):
        """Update logging level for all component loggers"""
        logger_names = [
            'SmartClipCZ',
            'SmartClipCZ.TwitchAPI',
            'SmartClipCZ.AudioHandler',
            'SmartClipCZ.EmotionDetector',
            'SmartClipCZ.OpenSMILEDetector',
            'SmartClipCZ.VoskDetector',
            'SmartClipCZ.ClipManager',
            'SmartClipCZ.QualityScorer',
            'SmartClipCZ.UIManager',
            'SmartClipCZ.ConfigManager'
        ]

        for logger_name in logger_names:
            logger = logging.getLogger(logger_name)
            logger.setLevel(level)

    def get_texts(self):
        """Get text strings for the selected language"""
        language = self.config.get("language", "en")
        texts = {
            "en": {
                # UI Labels
                "twitch_setup": "Twitch Setup",
                "audio_sources": "Audio Sources",
                "detection_settings": "Detection Settings",
                "activation_phrases": "Activation Phrases",
                "advanced_options": "Advanced Options",
                "debugging": "Debugging",
                "tools_testing": "Tools & Testing",

                # Buttons
                "start_detection": "🎬 Start Detection",
                "stop_detection": "⏹️ Stop Detection",
                "reload_config": "🔄 Reload Configuration",
                "show_statistics": "📊 Show Statistics",
                "test_detection": "🧪 Test Detection",
                "force_token_refresh": "🔄 Force Token Refresh (Debug)",
                "show_confidence_widget": "📈 Show Live Confidence Widget (Disabled)",

                # Settings
                "enable_debug_logging": "🐛 Enable Debug Logging",
                "enable_quality_scoring": "⭐ Enable Quality Scoring",
                "auto_start_stop": "🚀 Auto-start/stop Detection with Streaming",
                "language_setting": "🌐 Language / Jazyk",

                # Twitch Setup
                "client_id": "Client ID:",
                "oauth_token": "OAuth Token:",
                "broadcaster_id": "Broadcaster ID:",
                "client_secret": "Client Secret (Optional):",
                "refresh_token": "Refresh Token (Optional):",

                # Audio Sources
                "microphone_source": "Microphone Source:",
                "voice_chat_source": "Voice Chat Source:",

                # Detection Settings
                "basic_emotion_sensitivity": "Basic Emotion Sensitivity:",
                "opensmile_sensitivity": "OpenSMILE Sensitivity:",
                "vosk_sensitivity": "Vosk Sensitivity:",
                "clip_duration": "Clip Duration (seconds):"
            },
            "cs": {
                # UI Labels
                "twitch_setup": "Nastavení Twitch",
                "audio_sources": "Zdroje zvuku",
                "detection_settings": "Nastavení detekce",
                "activation_phrases": "Aktivační fráze",
                "advanced_options": "Pokročilé možnosti",
                "debugging": "Ladění",
                "tools_testing": "Nástroje a testování",

                # Buttons
                "start_detection": "🎬 Spustit detekci",
                "stop_detection": "⏹️ Zastavit detekci",
                "reload_config": "🔄 Znovu načíst konfiguraci",
                "show_statistics": "📊 Zobrazit statistiky",
                "test_detection": "🧪 Test detekce",
                "force_token_refresh": "🔄 Vynutit obnovení tokenu (Debug)",
                "show_confidence_widget": "📈 Zobrazit widget spolehlivosti (Zakázáno)",

                # Settings
                "enable_debug_logging": "🐛 Povolit debug logování",
                "enable_quality_scoring": "⭐ Povolit hodnocení kvality",
                "auto_start_stop": "🚀 Auto-start/stop detekce se streamováním",
                "language_setting": "🌐 Language / Jazyk",

                # Twitch Setup
                "client_id": "Client ID:",
                "oauth_token": "OAuth Token:",
                "broadcaster_id": "Broadcaster ID:",
                "client_secret": "Client Secret (Volitelné):",
                "refresh_token": "Refresh Token (Volitelné):",

                # Audio Sources
                "microphone_source": "Zdroj mikrofonu:",
                "voice_chat_source": "Zdroj hlasového chatu:",

                # Detection Settings
                "basic_emotion_sensitivity": "Citlivost základní detekce emocí:",
                "opensmile_sensitivity": "Citlivost OpenSMILE:",
                "vosk_sensitivity": "Citlivost Vosk:",
                "clip_duration": "Délka klipu (sekundy):"
            }
        }
        return texts.get(language, texts["en"])

    def _log_to_obs(self, level, message):
        """Log to OBS only if logging is enabled or if it's a critical message"""
        enable_debug_logging = self.config.get("advanced_settings", {}).get("enable_debug_logging", False)

        # Always show critical errors and warnings
        if level in [obs.LOG_ERROR, obs.LOG_WARNING]:
            obs.script_log(level, message)
        # Only show info messages if logging is enabled
        elif level == obs.LOG_INFO and enable_debug_logging:
            obs.script_log(level, message)
        
    def load_config(self):
        """Load configuration from JSON file"""
        try:
            config_path = os.path.join(plugin_dir, 'smartclip_cz_config.json')
            self.config = self.config_manager.load_config(config_path)
            self.logger.info("Configuration loaded successfully")
            self._log_to_obs(obs.LOG_INFO, "[SmartClip CZ] Configuration loaded")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] Config load failed: {e}")
            self.config = self.get_default_config()
            return False
    
    def get_default_config(self):
        """Get default configuration"""
        return {
            "enabled_emotions": ["laughter", "excitement", "surprise", "joy", "anger", "fear", "sadness", "neutral"],
            "emotion_sensitivity": 0.7,  # Legacy setting for backward compatibility
            "basic_emotion_sensitivity": 0.7,
            "opensmile_sensitivity": 0.5,
            "vosk_sensitivity": 0.6,
            "activation_phrases": [
                "to je skvělé", "wow", "úžasné", "perfektní", "super", "bomba",
                "co to bylo", "to je šílené", "neuvěřitelné", "holy shit"
            ],
            "english_activation_phrases": [
                "that's amazing", "awesome", "incredible", "fantastic", "wow",
                "what the hell", "that's insane", "unbelievable", "holy shit",
                "that's crazy", "amazing", "perfect", "excellent"
            ],
            "microphone_source": "Desktop Audio",
            "microphone_enabled": True,
            "voice_chat_source": "",
            "voice_chat_enabled": False,
            "twitch_client_id": "",
            "twitch_oauth_token": "",
            "twitch_broadcaster_id": "",
            "clip_duration": 30,
            "language": "en",
            "quality_scoring_enabled": True,
            "basic_emotion_enabled": True,
            "opensmile_enabled": True,
            "vosk_enabled": True,
            "auto_start_on_stream": False,

        }

    def _detect_best_audio_source(self):
        """Auto-detect the best audio source based on common names"""
        try:
            # Get available sources
            sources = obs.obs_enum_sources()
            available_sources = []

            for source in sources:
                try:
                    source_name = obs.obs_source_get_name(source)
                    if obs.obs_source_audio_active(source):
                        available_sources.append(source_name)
                except:
                    continue

            obs.source_list_release(sources)

            # Priority list for different languages
            priority_sources = [
                # Czech
                "Zvuk plochy", "Mikrofon", "Mikrofon / AUX",
                # English
                "Desktop Audio", "Microphone", "Mic/Aux",
                # German
                "Desktop-Audio", "Mikrofon",
                # French
                "Audio du bureau", "Microphone",
                # Spanish
                "Audio de escritorio", "Micrófono"
            ]

            # Find the first priority source that exists
            for priority_source in priority_sources:
                if priority_source in available_sources:
                    self.logger.info(f"Auto-detected audio source: {priority_source}")
                    return priority_source

            # If no priority source found, use the first available audio source
            if available_sources:
                best_source = available_sources[0]
                self.logger.info(f"Using first available audio source: {best_source}")
                return best_source

            self.logger.warning("No audio sources detected")
            return None

        except Exception as e:
            self.logger.error(f"Error detecting audio source: {e}")
            return None

    def initialize_components(self):
        """Initialize all plugin components"""
        try:
            self.logger.info("Initializing SmartClip CZ components...")

            # Initialize audio handler with multiple sources
            audio_sources = []
            if self.config.get("microphone_enabled", True):
                mic_source = self.config.get("microphone_source", "")
                if mic_source:
                    audio_sources.append(mic_source)
                    self.logger.info(f"Microphone source enabled: {mic_source}")
                else:
                    # Auto-detect best audio source
                    best_source = self._detect_best_audio_source()
                    if best_source:
                        audio_sources.append(best_source)
                        self.logger.info(f"Auto-detected microphone source: {best_source}")
                        # Save the detected source to config
                        self.config["microphone_source"] = best_source

            if self.config.get("voice_chat_enabled", False):
                voice_chat_source = self.config.get("voice_chat_source", "")
                if voice_chat_source:
                    audio_sources.append(voice_chat_source)
                    self.logger.info(f"Voice chat source enabled: {voice_chat_source}")

            # Fallback to auto-detection if no sources enabled
            if not audio_sources:
                best_source = self._detect_best_audio_source()
                if best_source:
                    audio_sources = [best_source]
                    self.logger.info(f"No sources configured, auto-detected: {best_source}")
                else:
                    audio_sources = ["Desktop Audio"]  # Last resort
                    self.logger.warning("No audio sources detected, using fallback")

            self.logger.info(f"Initializing audio handler with sources: {audio_sources}")
            self.audio_handler = AudioHandler(
                sources=audio_sources,
                sample_rate=16000,
                buffer_size=1024
            )
            
            # Initialize basic emotion detector if enabled
            if self.config.get("basic_emotion_enabled", True):
                basic_sensitivity = self.config.get("basic_emotion_sensitivity",
                                                   self.config.get("emotion_sensitivity", 0.7))
                self.emotion_detector = EmotionDetector(
                    enabled_emotions=self.config.get("enabled_emotions", []),
                    sensitivity=basic_sensitivity
                )
                self.logger.info(f"Basic emotion detector initialized (sensitivity: {basic_sensitivity})")
            else:
                self.emotion_detector = None
                self.logger.info("Basic emotion detector disabled")
            
            # Initialize OpenSMILE detector if enabled
            if self.config.get("opensmile_enabled", True):
                try:
                    opensmile_sensitivity = self.config.get("opensmile_sensitivity",
                                                          self.config.get("emotion_sensitivity", 0.7))
                    self.opensmile_detector = OpenSMILEDetector(
                        config_file="IS09_emotion.conf",
                        sensitivity=opensmile_sensitivity,
                        result_callback=self._handle_opensmile_detection
                    )
                    self.logger.info(f"OpenSMILE detector initialized (sensitivity: {opensmile_sensitivity})")
                except Exception as e:
                    self.logger.warning(f"OpenSMILE initialization failed: {e}")
                    self.opensmile_detector = None
            
            # Initialize Vosk detector if enabled
            if self.config.get("vosk_enabled", True):
                try:
                    vosk_sensitivity = self.config.get("vosk_sensitivity",
                                                     self.config.get("emotion_sensitivity", 0.7))

                    # Model paths
                    czech_model_path = os.path.join(os.path.dirname(__file__), "models", "vosk-model-small-cs-0.4-rhasspy")
                    english_model_path = os.path.join(os.path.dirname(__file__), "models", "vosk-model-small-en-us-0.15")

                    # Get phrases
                    czech_phrases = self.config.get("activation_phrases", [])
                    english_phrases = self.config.get("english_activation_phrases", [])

                    self.vosk_detector = VoskDetector(
                        czech_model_path=czech_model_path if os.path.exists(czech_model_path) else None,
                        english_model_path=english_model_path if os.path.exists(english_model_path) else None,
                        czech_phrases=czech_phrases,
                        english_phrases=english_phrases,
                        confidence_threshold=vosk_sensitivity
                    )
                    self.logger.info(f"Vosk detector initialized (sensitivity: {vosk_sensitivity})")
                except Exception as e:
                    self.logger.warning(f"Vosk initialization failed: {e}")
                    self.vosk_detector = None
            
            # Initialize Twitch API (without automatic token refresh during init)
            self.twitch_api = TwitchAPI(
                client_id=self.config.get("twitch_client_id", ""),
                oauth_token=self.config.get("twitch_oauth_token", ""),
                broadcaster_id=self.config.get("twitch_broadcaster_id", ""),
                client_secret=self.config.get("twitch_client_secret", ""),
                refresh_token=self.config.get("twitch_refresh_token", ""),
                skip_init_refresh=True  # Skip automatic refresh during initialization
            )

            # Set up token refresh callback BEFORE any refresh attempts
            self.twitch_api.set_token_refresh_callback(self._save_refreshed_tokens)

            # Now perform initial validation and refresh if needed
            self.twitch_api.perform_initial_validation()

            # Log OAuth setup status and provide guidance
            self._log_oauth_setup_status()
            
            # Initialize clip manager
            self.clip_manager = ClipManager()
            
            # Initialize quality scorer
            if self.config.get("quality_scoring_enabled", True):
                self.quality_scorer = QualityScorer(
                    min_confidence=self.config.get("emotion_sensitivity", 0.7) * 0.8,
                    min_time_between_clips=30,
                    max_clips_per_hour=12
                )
            
            # Initialize UI manager
            self.ui_manager = UIManager(self)
            
            self.logger.info("All components initialized successfully")
            self._log_to_obs(obs.LOG_INFO, "[SmartClip CZ] Components initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Component initialization failed: {e}")
            obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] Initialization failed: {e}")
            return False
    
    def start_detection(self):
        """Start audio detection and processing"""
        if self.running:
            self.logger.warning("Detection already running")
            return False
            
        try:
            self.running = True
            
            # Start audio capture
            if self.audio_handler:
                self.audio_handler.start_capture(self.audio_callback)
            
            # Start detection thread
            self.detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
            self.detection_thread.start()
            
            # Start component-specific detection
            if self.opensmile_detector:
                self.opensmile_detector.start_detection()
            
            if self.vosk_detector:
                self.vosk_detector.start_detection()
            
            # Start stream monitoring if auto-start is enabled
            self.start_stream_monitoring()

            self.logger.info("Detection started successfully")
            self._log_to_obs(obs.LOG_INFO, "[SmartClip CZ] Detection started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start detection: {e}")
            obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] Start failed: {e}")
            self.running = False
            return False
    
    def stop_detection(self):
        """Stop audio detection and processing"""
        if not self.running:
            return
            
        try:
            self.running = False
            
            # Stop audio capture
            if self.audio_handler:
                self.audio_handler.stop_capture()
            
            # Stop component detection
            if self.opensmile_detector:
                self.opensmile_detector.stop_detection()
            
            if self.vosk_detector:
                self.vosk_detector.stop_detection()
            
            # Wait for detection thread to finish
            if self.detection_thread and self.detection_thread.is_alive():
                self.detection_thread.join(timeout=2)

            # Stop stream monitoring
            self.stop_stream_monitoring()

            self.logger.info("Detection stopped")
            self._log_to_obs(obs.LOG_INFO, "[SmartClip CZ] Detection stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping detection: {e}")
            obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] Stop error: {e}")

    def _save_refreshed_tokens(self, new_oauth_token: str, new_refresh_token: str):
        """Callback to save refreshed OAuth tokens"""
        try:
            self.logger.info("=== TOKEN REFRESH CALLBACK STARTED ===")
            self.logger.info(f"New OAuth token received: {'[PRESENT]' if new_oauth_token else '[MISSING]'}")
            self.logger.info(f"New refresh token received: {'[PRESENT]' if new_refresh_token else '[MISSING]'}")

            # Log current config state
            current_oauth = self.config.get("twitch_oauth_token", "")
            current_refresh = self.config.get("twitch_refresh_token", "")
            self.logger.info(f"Current OAuth token in config: {'[PRESENT]' if current_oauth else '[MISSING]'}")
            self.logger.info(f"Current refresh token in config: {'[PRESENT]' if current_refresh else '[MISSING]'}")

            # Update config in memory
            old_oauth_token = self.config.get("twitch_oauth_token", "")
            self.config["twitch_oauth_token"] = new_oauth_token
            if new_refresh_token:
                self.config["twitch_refresh_token"] = new_refresh_token
                self.logger.info("Refresh token updated in memory")
            else:
                self.logger.warning("No new refresh token provided, keeping existing one")

            # Log token changes
            token_changed = old_oauth_token != new_oauth_token
            self.logger.info(f"OAuth token changed: {token_changed}")
            if token_changed:
                self.logger.info(f"Old token length: {len(old_oauth_token) if old_oauth_token else 0}")
                self.logger.info(f"New token length: {len(new_oauth_token) if new_oauth_token else 0}")

            # Save to file with proper path
            config_path = os.path.join(plugin_dir, 'smartclip_cz_config.json')
            self.logger.info(f"Saving config to: {config_path}")

            save_success = self.config_manager.save_config(config_path, self.config)
            if save_success:
                self.logger.info("Refreshed tokens saved to file successfully")

                # Verify the save by reading back
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        saved_config = json.load(f)
                    saved_oauth = saved_config.get("twitch_oauth_token", "")
                    saved_refresh = saved_config.get("twitch_refresh_token", "")
                    self.logger.info(f"Verification - OAuth token in file: {'[PRESENT]' if saved_oauth else '[MISSING]'}")
                    self.logger.info(f"Verification - Refresh token in file: {'[PRESENT]' if saved_refresh else '[MISSING]'}")

                    if saved_oauth == new_oauth_token:
                        self.logger.info("OAuth token verification successful")
                    else:
                        self.logger.error("OAuth token verification failed - mismatch")

                except Exception as verify_error:
                    self.logger.error(f"Token save verification failed: {verify_error}")
            else:
                self.logger.error("Failed to save refreshed tokens to file")

            self.logger.info("=== TOKEN REFRESH CALLBACK COMPLETED ===")

        except Exception as e:
            self.logger.error(f"CRITICAL ERROR in token refresh callback: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")

    def _log_oauth_setup_status(self):
        """Log OAuth setup status and provide guidance for optimal configuration"""
        try:
            client_id = self.config.get("twitch_client_id", "")
            client_secret = self.config.get("twitch_client_secret", "")
            oauth_token = self.config.get("twitch_oauth_token", "")
            refresh_token = self.config.get("twitch_refresh_token", "")
            broadcaster_id = self.config.get("twitch_broadcaster_id", "")

            self.logger.info("=== TWITCH OAUTH SETUP STATUS ===")
            self.logger.info(f"Client ID: {'PRESENT' if client_id else 'MISSING'}")
            self.logger.info(f"OAuth Token: {'PRESENT' if oauth_token else 'MISSING'}")
            self.logger.info(f"Broadcaster ID: {'PRESENT' if broadcaster_id else 'MISSING'}")
            self.logger.info(f"Client Secret: {'PRESENT' if client_secret else 'MISSING'}")
            self.logger.info(f"Refresh Token: {'PRESENT' if refresh_token else 'MISSING'}")

            # Show token lengths for debugging (without exposing actual tokens)
            if oauth_token:
                self.logger.info(f"OAuth Token length: {len(oauth_token)} characters")
            if refresh_token:
                self.logger.info(f"Refresh Token length: {len(refresh_token)} characters")
            if client_secret:
                self.logger.info(f"Client Secret length: {len(client_secret)} characters")

            # Check basic configuration
            if not client_id or not oauth_token or not broadcaster_id:
                self.logger.warning("Twitch API not fully configured - clips cannot be created")
                self.logger.info("To set up Twitch API:")
                self.logger.info("   1. Run SmartClip_CZ_Installer.exe for automatic setup")
                self.logger.info("   2. Or manually configure in OBS Scripts settings")
                return

            # Check for automatic token refresh capability
            can_refresh = bool(client_secret and refresh_token)
            self.logger.info(f"Automatic token refresh: {'ENABLED' if can_refresh else 'DISABLED'}")

            if not can_refresh:
                self.logger.warning("Automatic token refresh not configured")
                self.logger.info("For automatic token refresh (recommended):")
                self.logger.info("   1. Re-run SmartClip_CZ_Installer.exe")
                self.logger.info("   2. Choose 'Yes' for Twitch OAuth setup")
                self.logger.info("   3. Follow the guided process to get refresh tokens")
                self.logger.info("   4. This prevents token expiration issues")

                if not client_secret:
                    self.logger.warning("   Missing client_secret (needed for token refresh)")
                if not refresh_token:
                    self.logger.warning("   Missing refresh_token (needed for token refresh)")
            else:
                self.logger.info("Twitch API fully configured with automatic token refresh")

            # Check if Twitch API is actually working
            if self.twitch_api:
                api_configured = self.twitch_api.is_configured()
                self.logger.info(f"Twitch API status: {'WORKING' if api_configured else 'NOT WORKING'}")
                if not api_configured:
                    self.logger.warning("  API validation failed - check token validity")

            self.logger.info("=== END OAUTH SETUP STATUS ===")

        except Exception as e:
            self.logger.error(f"Error checking OAuth setup status: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")

    def audio_callback(self, audio_data: np.ndarray):
        """Callback for incoming audio data"""
        try:
            if not self.audio_queue.full():
                self.audio_queue.put(audio_data, block=False)
        except queue.Full:
            pass  # Drop audio if queue is full
    
    def _detection_loop(self):
        """Main detection processing loop"""
        self.logger.info("Detection loop started")
        
        while self.running:
            try:
                # Get audio data with timeout
                try:
                    audio_data = self.audio_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # Process audio for emotions
                if self.emotion_detector:
                    emotion_result = self.emotion_detector.detect(audio_data)
                    if emotion_result:
                        self._handle_emotion_detection(emotion_result)
                
                # Process audio with OpenSMILE (results handled via callback)
                if self.opensmile_detector and self.config.get("opensmile_enabled", True):
                    self.opensmile_detector.process_audio(audio_data)
                
                # Process audio with Vosk
                vosk_result = None
                if self.vosk_detector:
                    vosk_result = self.vosk_detector.process_audio(audio_data)

                    # Phrase detection debugging
                    if vosk_result:
                        self.logger.info(f"Vosk result received: {vosk_result}")
                        if isinstance(vosk_result, dict):
                            phrase = vosk_result.get('matched_phrase', 'unknown')
                            confidence = vosk_result.get('confidence', 0)
                            self.logger.info(f"Matched phrase: '{phrase}' (confidence: {confidence:.2f})")

                        self._handle_vosk_detection(vosk_result)
                
                # Mark task as done
                self.audio_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error in detection loop: {e}")
                time.sleep(0.1)
        
        self.logger.info("Detection loop ended")
    
    def _handle_emotion_detection(self, result):
        """Handle emotion detection result"""
        try:
            now = datetime.now()
            time_since_last = now - self.last_detection_time
            
            if time_since_last < self.detection_cooldown:
                return
            
            # Update statistics
            self.stats['total_detections'] += 1
            emotion_name = result.emotion_type.value if hasattr(result, 'emotion_type') else 'unknown'
            self.stats['emotions_detected'][emotion_name] = self.stats['emotions_detected'].get(emotion_name, 0) + 1
            
            # Check quality if scorer is available
            should_create_clip = True
            quality_score = None
            
            if self.quality_scorer:
                quality_score = self.quality_scorer.score_detection(result, 'emotion')
                should_create_clip = quality_score.should_create_clip
            
            if should_create_clip:
                self.last_detection_time = now

                # Create clip with emotion name as trigger
                success = self._create_clip(emotion_name, result)
                
                if success:
                    self.stats['clips_created'] += 1
                    if self.quality_scorer:
                        self.quality_scorer.record_clip_decision(quality_score, True)
                else:
                    self.stats['clips_rejected'] += 1
                    if self.quality_scorer:
                        self.quality_scorer.record_clip_decision(quality_score, False)
                
                # Log detection
                label = self._get_emotion_label(emotion_name)
                confidence = result.confidence if hasattr(result, 'confidence') else 0
                self.logger.info(f"[{label}] Emotion detected: {emotion_name} ({confidence:.2f}) - Clip {'created' if success else 'failed'}")
                self._log_to_obs(obs.LOG_INFO, f"[SmartClip CZ] [{label}] {emotion_name}: {confidence:.2f}")

                # Update confidence data for widget
                self.update_confidence_data("basic_emotion", confidence, emotion_name)
            
        except Exception as e:
            self.logger.error(f"Error handling emotion detection: {e}")
    
    def _handle_opensmile_detection(self, result):
        """Handle OpenSMILE detection result"""
        try:
            now = datetime.now()
            time_since_last = now - self.last_detection_time
            
            if time_since_last < self.detection_cooldown:
                return
            
            self.last_detection_time = now
            emotion_name = result.get('emotion', 'unknown')
            confidence = result.get('confidence', 0)

            # Create clip with emotion name as trigger
            success = self._create_clip(emotion_name, result)
            
            self.logger.info(f"[AI] OpenSMILE detected: {emotion_name} ({confidence:.2f}) - Clip {'created' if success else 'failed'}")
            self._log_to_obs(obs.LOG_INFO, f"[SmartClip CZ] [AI] OpenSMILE: {emotion_name} ({confidence:.2f})")

            # Update confidence data for widget
            self.update_confidence_data("opensmile", confidence, emotion_name)
            
        except Exception as e:
            self.logger.error(f"Error handling OpenSMILE detection: {e}")
    
    def _handle_vosk_detection(self, result):
        """Handle Vosk speech detection result"""
        try:
            now = datetime.now()
            time_since_last = now - self.last_detection_time
            
            if time_since_last < self.detection_cooldown:
                return
            
            text = result.get('text', '')
            matched_phrase = result.get('matched_phrase', '')
            confidence = result.get('confidence', 0)
            
            # Update statistics
            self.stats['phrases_detected'][matched_phrase] = self.stats['phrases_detected'].get(matched_phrase, 0) + 1
            
            self.last_detection_time = now

            # Create clip with matched phrase as trigger
            success = self._create_clip(matched_phrase, result)
            
            self.logger.info(f"[SPEECH] Vosk detected: '{text}' -> '{matched_phrase}' ({confidence:.2f}) - Clip {'created' if success else 'failed'}")
            self._log_to_obs(obs.LOG_INFO, f"[SmartClip CZ] [SPEECH] Phrase: {matched_phrase}")

            # Update confidence data for widget
            self.update_confidence_data("vosk", confidence, matched_phrase)
            
        except Exception as e:
            self.logger.error(f"Error handling Vosk detection: {e}")

    def _generate_clip_title(self, trigger: str) -> str:
        """Generate clip title in format: {Stream title} - SmartClip - {trigger}"""
        try:
            # Get stream information
            stream_info = self.twitch_api.get_stream_info() if self.twitch_api else None

            # Extract stream title
            if stream_info:
                stream_title = stream_info.get('title', 'Live Stream')
                # Clean up stream title (remove extra whitespace, limit length)
                stream_title = ' '.join(stream_title.split())  # Remove extra whitespace
                if len(stream_title) > 50:  # Limit length to keep clip title reasonable
                    stream_title = stream_title[:47] + "..."
            else:
                stream_title = "Live Stream"

            # Format the clip title
            clip_title = f"{stream_title} - SmartClip - {trigger}"

            # Ensure total length doesn't exceed Twitch's limit (100 characters)
            if len(clip_title) > 100:
                # Truncate stream title to fit
                max_stream_title_length = 100 - len(" - SmartClip - ") - len(trigger)
                if max_stream_title_length > 10:  # Ensure minimum readable length
                    stream_title = stream_title[:max_stream_title_length-3] + "..."
                    clip_title = f"{stream_title} - SmartClip - {trigger}"
                else:
                    # If trigger is too long, use simplified format
                    clip_title = f"SmartClip - {trigger}"
                    if len(clip_title) > 100:
                        clip_title = clip_title[:97] + "..."

            return clip_title

        except Exception as e:
            self.logger.error(f"Error generating clip title: {e}")
            # Fallback to simple format
            return f"SmartClip - {trigger}"

    def _create_clip(self, trigger: str, detection_result: dict) -> bool:
        """Create a Twitch clip"""
        try:
            if not self.twitch_api or not self.twitch_api.is_configured():
                self.logger.warning("Twitch API not configured, cannot create clip")
                return False

            # Generate clip title with new format
            clip_title = self._generate_clip_title(trigger)

            # Record clip attempt
            if self.clip_manager:
                # Determine which audio sources are active
                active_sources = []
                if self.config.get("microphone_enabled", True):
                    mic_source = self.config.get("microphone_source", "Desktop Audio")
                    if mic_source:
                        active_sources.append(f"Microphone: {mic_source}")

                if self.config.get("voice_chat_enabled", False):
                    voice_chat_source = self.config.get("voice_chat_source", "")
                    if voice_chat_source:
                        active_sources.append(f"Voice Chat: {voice_chat_source}")

                audio_source = ", ".join(active_sources) if active_sources else "unknown"

                self.clip_manager.record_clip_attempt(
                    detection_type=detection_result.get('type', 'unknown'),
                    trigger_value=detection_result.get('emotion', detection_result.get('matched_phrase', 'unknown')),
                    confidence=detection_result.get('confidence', 0),
                    audio_source=audio_source,
                    clip_title=clip_title
                )

            # Create the clip with configured duration
            clip_duration = self.config.get("clip_duration", 30)
            self.logger.info(f"Creating clip with intended title: {clip_title}")
            self.logger.info("Note: Twitch API will use current stream title, not custom title")
            clip_id = self.twitch_api.create_clip(clip_title, duration=clip_duration)
            
            if clip_id:
                # Update clip manager with success
                if self.clip_manager:
                    self.clip_manager.update_clip_result(clip_id, True, "Clip created successfully")
                
                self.logger.info(f"[OK] Clip created successfully: {clip_id}")
                self.logger.info(f"[OK] Clip title: {clip_title}")
                self._log_to_obs(obs.LOG_INFO, f"[SmartClip CZ] [OK] Clip created: {clip_id}")
                return True
            else:
                # Update clip manager with failure
                if self.clip_manager:
                    self.clip_manager.update_clip_result("", False, "Clip creation failed")
                
                self.logger.warning("[ERROR] Clip creation failed")
                obs.script_log(obs.LOG_WARNING, "[SmartClip CZ] [ERROR] Clip creation failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error creating clip: {e}")
            obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] Clip error: {e}")
            return False
    
    def _get_emotion_label(self, emotion: str) -> str:
        """Get text label for emotion type"""
        label_map = {
            'laughter': 'LAUGHTER',
            'excitement': 'EXCITEMENT',
            'surprise': 'SURPRISE',
            'joy': 'JOY',
            'anger': 'ANGER',
            'fear': 'FEAR',
            'sadness': 'SADNESS',
            'neutral': 'NEUTRAL'
        }
        return label_map.get(emotion.lower(), 'EMOTION')
    
    def get_statistics(self) -> dict:
        """Get plugin statistics"""
        runtime = datetime.now() - self.stats['session_start']
        
        return {
            **self.stats,
            'session_runtime': str(runtime),
            'success_rate': self.stats['clips_created'] / max(1, self.stats['total_detections']),
            'running': self.running
        }
    
    def reload_config(self):
        """Reload configuration and restart detection"""
        self.logger.info("Reloading configuration...")
        
        was_running = self.running
        if was_running:
            self.stop_detection()
        
        self.load_config()
        
        if was_running:
            self.start_detection()
        
        self._log_to_obs(obs.LOG_INFO, "[SmartClip CZ] Configuration reloaded")

    def start_stream_monitoring(self):
        """Start monitoring streaming state for auto-start/stop functionality"""
        if not self.config.get("auto_start_on_stream", False):
            return

        if self.stream_check_timer is None:
            # Check streaming state every 2 seconds
            self.stream_check_timer = threading.Timer(2.0, self._check_streaming_state)
            self.stream_check_timer.daemon = True
            self.stream_check_timer.start()

    def stop_stream_monitoring(self):
        """Stop monitoring streaming state"""
        if self.stream_check_timer:
            self.stream_check_timer.cancel()
            self.stream_check_timer = None

    def _check_streaming_state(self):
        """Check if streaming is active and handle auto-start/stop"""
        try:
            # Check if OBS is currently streaming
            streaming = obs.obs_frontend_streaming_active()

            # If streaming state changed
            if streaming != self.is_streaming:
                self.is_streaming = streaming

                if streaming and self.config.get("auto_start_on_stream", False):
                    # Stream started and auto-start is enabled
                    if not self.detection_thread or not self.detection_thread.is_alive():
                        self.logger.info("Stream started - Auto-starting detection")
                        self._log_to_obs(obs.LOG_INFO, "[SmartClip CZ] Stream started - Auto-starting detection")
                        self.start_detection()
                elif not streaming:
                    # Stream stopped - auto-stop detection if it was auto-started
                    if self.detection_thread and self.detection_thread.is_alive():
                        self.logger.info("Stream stopped - Auto-stopping detection")
                        self._log_to_obs(obs.LOG_INFO, "[SmartClip CZ] Stream stopped - Auto-stopping detection")
                        self.stop_detection()
                    else:
                        self.logger.info("Stream stopped")
                        self._log_to_obs(obs.LOG_INFO, "[SmartClip CZ] Stream stopped")

            # Schedule next check if auto-start is still enabled
            if self.config.get("auto_start_on_stream", False):
                self.stream_check_timer = threading.Timer(2.0, self._check_streaming_state)
                self.stream_check_timer.daemon = True
                self.stream_check_timer.start()
            else:
                self.stream_check_timer = None

        except Exception as e:
            self.logger.error(f"Error checking streaming state: {e}")
            # Reschedule check even on error
            if self.config.get("auto_start_on_stream", False):
                self.stream_check_timer = threading.Timer(5.0, self._check_streaming_state)
                self.stream_check_timer.daemon = True
                self.stream_check_timer.start()

    def update_confidence_data(self, detector_type: str, confidence: float, extra_info: str = ""):
        """Update confidence data for the widget"""
        try:
            if detector_type == "basic_emotion":
                self.confidence_data['basic_emotion'] = confidence
                if extra_info:
                    self.confidence_data['last_emotion'] = extra_info
            elif detector_type == "opensmile":
                self.confidence_data['opensmile'] = confidence
                if extra_info:
                    self.confidence_data['last_emotion'] = extra_info
            elif detector_type == "vosk":
                self.confidence_data['vosk'] = confidence
                if extra_info:
                    self.confidence_data['last_phrase'] = extra_info

            # Save to file for widget
            self._save_confidence_data()

        except Exception as e:
            self.logger.error(f"Error updating confidence data: {e}")

    def _save_confidence_data(self):
        """Save confidence data to file for widget"""
        try:
            import json
            import os

            # Try multiple locations to ensure widget can find the data
            possible_locations = [
                # Same directory as script
                os.path.join(os.path.dirname(__file__), "confidence_data.json"),
                # User home directory (fallback for standalone widget)
                os.path.join(os.path.expanduser("~"), "smartclip_confidence_data.json"),
            ]

            # Save to all possible locations
            for data_file in possible_locations:
                try:
                    with open(data_file, 'w') as f:
                        json.dump(self.confidence_data, f)
                except Exception as e:
                    self.logger.debug(f"Could not save to {data_file}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error saving confidence data: {e}")

# Global plugin instance
smartclip = SmartClipCZ()

# OBS Script Interface Functions
def script_description():
    return """
    <center><h2>🎭 SmartClip CZ - Python Edition v2.0.0</h2></center>
    <p><b>Advanced emotion detection and automatic Twitch clip creation for Czech streamers.</b></p>

    <h3>🌟 Features:</h3>
    <ul>
        <li>🎭 <b>Multi-emotion detection</b> (8 emotion types)</li>
        <li>🗣️ <b>Czech speech recognition</b> with Vosk</li>
        <li>🤖 <b>OpenSMILE ML integration</b> for advanced emotion detection</li>
        <li>⭐ <b>Smart clip quality scoring</b></li>
        <li>📊 <b>Real-time confidence visualization</b></li>

        <li>📈 <b>Advanced statistics and analytics</b></li>
    </ul>

    <h3>🚀 Quick Start:</h3>
    <ol>
        <li>Configure your Twitch API credentials below</li>
        <li>Select your audio source</li>
        <li>Adjust emotion sensitivity</li>
        <li>Click "Start Detection"</li>
    </ol>

    <p><i>Python rewrite - No more crashes, better performance!</i></p>
    """

def get_ui_texts(language):
    """Get UI text strings for the specified language"""
    texts = {
        "en": {
            # UI Labels
            "twitch_setup": "Twitch Setup",
            "audio_sources": "Audio Sources",
            "detection_settings": "Detection Settings",
            "activation_phrases": "Activation Phrases",
            "advanced_options": "Advanced Options",
            "debugging": "Debugging",
            "tools_testing": "Tools & Testing",

            # Buttons
            "start_detection": "🎬 Start Detection",
            "stop_detection": "⏹️ Stop Detection",
            "reload_config": "🔄 Reload Configuration",
            "show_statistics": "📊 Show Statistics",
            "test_detection": "🧪 Test Detection",
            "force_token_refresh": "🔄 Force Token Refresh (Debug)",
            "show_confidence_widget": "📈 Show Live Confidence Widget (Disabled)",

            # Settings
            "enable_debug_logging": "🐛 Enable Debug Logging",
            "enable_quality_scoring": "⭐ Enable Quality Scoring",
            "auto_start_stop": "🚀 Auto-start/stop Detection with Streaming",

            # Twitch Setup
            "client_id": "Client ID:",
            "oauth_token": "OAuth Token:",
            "broadcaster_id": "Broadcaster ID:",
            "client_secret": "Client Secret (Optional):",
            "refresh_token": "Refresh Token (Optional):",

            # Audio Sources
            "microphone_source": "Microphone Source:",
            "voice_chat_source": "Voice Chat Source:",

            # Detection Settings
            "basic_emotion_sensitivity": "Basic Emotion Sensitivity:",
            "opensmile_sensitivity": "OpenSMILE Sensitivity:",
            "vosk_sensitivity": "Vosk Sensitivity:",
            "clip_duration": "Clip Duration (seconds):",

            # Detection Modules
            "enable_basic_emotion": "🎭 Enable Basic Emotion Detection",
            "enable_opensmile": "🤖 Enable OpenSMILE Detection",
            "enable_vosk": "🗣️ Enable Vosk Speech Recognition",

            # Activation Phrases
            "czech_activation_phrases": "🇨🇿 Czech Activation Phrases (comma-separated)",
            "english_activation_phrases": "🇺🇸 English Activation Phrases (comma-separated)",

            # Emotion Detection
            "detect_laughter": "😂 Detect Laughter",
            "detect_excitement": "🎉 Detect Excitement",
            "detect_surprise": "😲 Detect Surprise",
            "detect_joy": "😊 Detect Joy",
            "detect_anger": "😠 Detect Anger",
            "detect_fear": "😨 Detect Fear",
            "detect_sadness": "😢 Detect Sadness"
        },
        "cs": {
            # UI Labels
            "twitch_setup": "Nastavení Twitch",
            "audio_sources": "Zdroje zvuku",
            "detection_settings": "Nastavení detekce",
            "activation_phrases": "Aktivační fráze",
            "advanced_options": "Pokročilé možnosti",
            "debugging": "Ladění",
            "tools_testing": "Nástroje a testování",

            # Buttons
            "start_detection": "🎬 Spustit detekci",
            "stop_detection": "⏹️ Zastavit detekci",
            "reload_config": "🔄 Znovu načíst konfiguraci",
            "show_statistics": "📊 Zobrazit statistiky",
            "test_detection": "🧪 Test detekce",
            "force_token_refresh": "🔄 Vynutit obnovení tokenu (Debug)",
            "show_confidence_widget": "📈 Zobrazit widget spolehlivosti (Zakázáno)",

            # Settings
            "enable_debug_logging": "🐛 Povolit debug logování",
            "enable_quality_scoring": "⭐ Povolit hodnocení kvality",
            "auto_start_stop": "🚀 Auto-start/stop detekce se streamováním",

            # Twitch Setup
            "client_id": "Client ID:",
            "oauth_token": "OAuth Token:",
            "broadcaster_id": "Broadcaster ID:",
            "client_secret": "Client Secret (Volitelné):",
            "refresh_token": "Refresh Token (Volitelné):",

            # Audio Sources
            "microphone_source": "Zdroj mikrofonu:",
            "voice_chat_source": "Zdroj hlasového chatu:",

            # Detection Settings
            "basic_emotion_sensitivity": "Citlivost základní detekce emocí:",
            "opensmile_sensitivity": "Citlivost OpenSMILE:",
            "vosk_sensitivity": "Citlivost Vosk:",
            "clip_duration": "Délka klipu (sekundy):",

            # Detection Modules
            "enable_basic_emotion": "🎭 Povolit základní detekci emocí",
            "enable_opensmile": "🤖 Povolit OpenSMILE detekci",
            "enable_vosk": "🗣️ Povolit rozpoznávání řeči Vosk",

            # Activation Phrases
            "czech_activation_phrases": "🇨🇿 České aktivační fráze (oddělené čárkami)",
            "english_activation_phrases": "🇺🇸 Anglické aktivační fráze (oddělené čárkami)",

            # Emotion Detection
            "detect_laughter": "😂 Detekovat smích",
            "detect_excitement": "🎉 Detekovat vzrušení",
            "detect_surprise": "😲 Detekovat překvapení",
            "detect_joy": "😊 Detekovat radost",
            "detect_anger": "😠 Detekovat hněv",
            "detect_fear": "😨 Detekovat strach",
            "detect_sadness": "😢 Detekovat smutek"
        }
    }
    return texts.get(language, texts["en"])

def script_properties():
    """Define script properties for OBS UI"""
    props = obs.obs_properties_create()

    # Get current language for UI
    try:
        current_language = smartclip.config.get("language", "en") if 'smartclip' in globals() and smartclip else "en"
        texts = get_ui_texts(current_language)
    except:
        texts = get_ui_texts("en")  # Fallback to English

    # === LANGUAGE ===
    language_list = obs.obs_properties_add_list(props, "language", "🌐 Language / Jazyk",
                                               obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(language_list, "English", "en")
    obs.obs_property_list_add_string(language_list, "Čeština", "cs")
    obs.obs_property_set_modified_callback(language_list, language_changed_callback)

    # === MAIN CONTROLS ===
    obs.obs_properties_add_button(props, "start_detection", texts["start_detection"], start_detection_callback)
    obs.obs_properties_add_button(props, "stop_detection", texts["stop_detection"], stop_detection_callback)
    obs.obs_properties_add_button(props, "reload_config", texts["reload_config"], reload_config_callback)

    # === AUDIO SOURCES ===
    # Microphone source
    obs.obs_properties_add_bool(props, "microphone_enabled", "🎤 Enable Microphone Monitoring")
    microphone_sources = obs.obs_properties_add_list(props, "microphone_source", f"🎤 {texts['microphone_source']}",
                                                     obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)

    # Voice chat source
    obs.obs_properties_add_bool(props, "voice_chat_enabled", "💬 Enable Voice Chat Monitoring")
    voice_chat_sources = obs.obs_properties_add_list(props, "voice_chat_source", f"💬 {texts['voice_chat_source']}",
                                                     obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)

    # Add available audio sources to both dropdowns
    sources = obs.obs_enum_sources()
    for source in sources:
        name = obs.obs_source_get_name(source)
        if obs.obs_source_audio_active(source):
            obs.obs_property_list_add_string(microphone_sources, name, name)
            obs.obs_property_list_add_string(voice_chat_sources, name, name)
    obs.source_list_release(sources)

    # === DETECTION MODULES ===
    obs.obs_properties_add_bool(props, "basic_emotion_enabled", texts["enable_basic_emotion"])
    obs.obs_properties_add_bool(props, "opensmile_enabled", texts["enable_opensmile"])
    obs.obs_properties_add_bool(props, "vosk_enabled", texts["enable_vosk"])

    # === DETECTION SENSITIVITIES ===
    obs.obs_properties_add_float_slider(props, "basic_emotion_sensitivity", f"🎭 {texts['basic_emotion_sensitivity']}",
                                       0.1, 1.0, 0.1)
    obs.obs_properties_add_float_slider(props, "opensmile_sensitivity", f"🤖 {texts['opensmile_sensitivity']}",
                                       0.1, 1.0, 0.1)
    obs.obs_properties_add_float_slider(props, "vosk_sensitivity", f"🗣️ {texts['vosk_sensitivity']}",
                                       0.1, 1.0, 0.1)

    # === EMOTION TYPES ===
    obs.obs_properties_add_bool(props, "emotion_laughter", texts["detect_laughter"])
    obs.obs_properties_add_bool(props, "emotion_excitement", texts["detect_excitement"])
    obs.obs_properties_add_bool(props, "emotion_surprise", texts["detect_surprise"])
    obs.obs_properties_add_bool(props, "emotion_joy", texts["detect_joy"])
    obs.obs_properties_add_bool(props, "emotion_anger", texts["detect_anger"])
    obs.obs_properties_add_bool(props, "emotion_fear", texts["detect_fear"])
    obs.obs_properties_add_bool(props, "emotion_sadness", texts["detect_sadness"])

    # === ACTIVATION PHRASES ===
    obs.obs_properties_add_text(props, "activation_phrases", texts["czech_activation_phrases"],
                               obs.OBS_TEXT_MULTILINE)
    obs.obs_properties_add_text(props, "english_activation_phrases", texts["english_activation_phrases"],
                               obs.OBS_TEXT_MULTILINE)

    # === CLIP SETTINGS ===
    obs.obs_properties_add_int_slider(props, "clip_duration", f"🎬 {texts['clip_duration']}",
                                     15, 60, 1)





    # === TWITCH API CREDENTIALS ===
    obs.obs_properties_add_text(props, "twitch_client_id", f"🔑 {texts['client_id']}", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "twitch_client_secret", f"🔐 {texts['client_secret']}", obs.OBS_TEXT_PASSWORD)
    obs.obs_properties_add_text(props, "twitch_oauth_token", f"🎫 {texts['oauth_token']}", obs.OBS_TEXT_PASSWORD)
    obs.obs_properties_add_text(props, "twitch_refresh_token", f"🔄 {texts['refresh_token']}", obs.OBS_TEXT_PASSWORD)
    obs.obs_properties_add_text(props, "twitch_broadcaster_id", f"👤 {texts['broadcaster_id']}", obs.OBS_TEXT_DEFAULT)

    # === ADVANCED OPTIONS ===
    obs.obs_properties_add_bool(props, "quality_scoring_enabled", texts["enable_quality_scoring"])
    obs.obs_properties_add_bool(props, "auto_start_on_stream", texts["auto_start_stop"])

    # === DEBUGGING ===
    obs.obs_properties_add_bool(props, "enable_debug_logging", texts["enable_debug_logging"])
    obs.obs_properties_add_text(props, "logging_info", "", obs.OBS_TEXT_INFO)
    obs.obs_property_set_long_description(obs.obs_properties_get(props, "logging_info"),
                                        "Debug logging creates detailed log files for troubleshooting. "
                                        "Keep disabled for normal use to improve performance.")

    # === TOOLS & TESTING ===
    obs.obs_properties_add_button(props, "show_statistics", texts["show_statistics"], show_statistics_callback)
    obs.obs_properties_add_button(props, "test_detection", texts["test_detection"], test_detection_callback)
    obs.obs_properties_add_button(props, "force_token_refresh", texts["force_token_refresh"], force_token_refresh_callback)
    # Temporarily disabled - widget needs fixes
    obs.obs_properties_add_button(props, "show_confidence_widget", texts["show_confidence_widget"], show_confidence_widget_disabled_callback)

    return props

def script_defaults(settings):
    """Set default values from saved configuration or fallback defaults"""
    try:
        # Load saved configuration if available
        config = {}
        if smartclip and smartclip.config:
            config = smartclip.config

        # Legacy sensitivity for backward compatibility
        obs.obs_data_set_default_double(settings, "emotion_sensitivity",
                                       config.get("emotion_sensitivity", 0.7))

        # Separate detector sensitivities
        obs.obs_data_set_default_double(settings, "basic_emotion_sensitivity",
                                       config.get("basic_emotion_sensitivity",
                                                 config.get("emotion_sensitivity", 0.7)))
        obs.obs_data_set_default_double(settings, "opensmile_sensitivity",
                                       config.get("opensmile_sensitivity", 0.5))
        obs.obs_data_set_default_double(settings, "vosk_sensitivity",
                                       config.get("vosk_sensitivity", 0.6))

        # Clip settings
        obs.obs_data_set_default_int(settings, "clip_duration",
                                    config.get("clip_duration", 30))

        # Audio source defaults
        obs.obs_data_set_default_bool(settings, "microphone_enabled", True)
        obs.obs_data_set_default_string(settings, "microphone_source", "Desktop Audio")
        obs.obs_data_set_default_bool(settings, "voice_chat_enabled", False)
        obs.obs_data_set_default_string(settings, "voice_chat_source", "")

        # Language defaults
        obs.obs_data_set_default_string(settings, "language",
                                       config.get("language", "en"))

        # Debugging defaults
        obs.obs_data_set_default_bool(settings, "enable_debug_logging",
                                     config.get("advanced_settings", {}).get("enable_debug_logging", False))

        # Default emotions enabled - load from config
        enabled_emotions = config.get("enabled_emotions", ["laughter", "excitement", "surprise", "joy"])
        obs.obs_data_set_default_bool(settings, "emotion_laughter", "laughter" in enabled_emotions)
        obs.obs_data_set_default_bool(settings, "emotion_excitement", "excitement" in enabled_emotions)
        obs.obs_data_set_default_bool(settings, "emotion_surprise", "surprise" in enabled_emotions)
        obs.obs_data_set_default_bool(settings, "emotion_joy", "joy" in enabled_emotions)
        obs.obs_data_set_default_bool(settings, "emotion_anger", "anger" in enabled_emotions)
        obs.obs_data_set_default_bool(settings, "emotion_fear", "fear" in enabled_emotions)
        obs.obs_data_set_default_bool(settings, "emotion_sadness", "sadness" in enabled_emotions)

        # Load activation phrases from config or use fallback defaults
        saved_phrases = config.get("activation_phrases", [])
        if saved_phrases:
            phrases_text = ", ".join(saved_phrases)
        else:
            phrases_text = "to je skvělé, wow, úžasné, perfektní, super, bomba, co to bylo, to je šílené, neuvěřitelné, holy shit, parádní, skvělý, výborný"
        obs.obs_data_set_default_string(settings, "activation_phrases", phrases_text)

        # Load English activation phrases from config or use fallback defaults
        saved_english_phrases = config.get("english_activation_phrases", [])
        if saved_english_phrases:
            english_phrases_text = ", ".join(saved_english_phrases)
        else:
            english_phrases_text = "that's amazing, awesome, incredible, fantastic, wow, what the hell, that's insane, unbelievable, holy shit, that's crazy, amazing, perfect, excellent"
        obs.obs_data_set_default_string(settings, "english_activation_phrases", english_phrases_text)

        # Component settings - load from config
        obs.obs_data_set_default_bool(settings, "basic_emotion_enabled",
                                     config.get("basic_emotion_enabled", True))
        obs.obs_data_set_default_bool(settings, "opensmile_enabled",
                                     config.get("opensmile_enabled", True))
        obs.obs_data_set_default_bool(settings, "vosk_enabled",
                                     config.get("vosk_enabled", True))
        obs.obs_data_set_default_bool(settings, "quality_scoring_enabled",
                                     config.get("quality_scoring_enabled", True))
        obs.obs_data_set_default_bool(settings, "auto_start_on_stream",
                                     config.get("auto_start_on_stream", False))

    except Exception as e:
        obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] Error in script_defaults: {e}")
        # Fallback to hardcoded defaults if config loading fails
        obs.obs_data_set_default_double(settings, "emotion_sensitivity", 0.7)
        obs.obs_data_set_default_double(settings, "basic_emotion_sensitivity", 0.7)
        obs.obs_data_set_default_double(settings, "opensmile_sensitivity", 0.5)
        obs.obs_data_set_default_double(settings, "vosk_sensitivity", 0.6)
        obs.obs_data_set_default_int(settings, "clip_duration", 30)
        obs.obs_data_set_default_string(settings, "language", "en")
        obs.obs_data_set_default_bool(settings, "enable_debug_logging", False)

    # Load Twitch credentials from config file into OBS UI
    if smartclip and smartclip.config:
        client_id = smartclip.config.get("twitch_client_id", "")
        client_secret = smartclip.config.get("twitch_client_secret", "")
        oauth_token = smartclip.config.get("twitch_oauth_token", "")
        refresh_token = smartclip.config.get("twitch_refresh_token", "")
        broadcaster_id = smartclip.config.get("twitch_broadcaster_id", "")

        obs.obs_data_set_default_string(settings, "twitch_client_id", client_id)
        obs.obs_data_set_default_string(settings, "twitch_client_secret", client_secret)
        obs.obs_data_set_default_string(settings, "twitch_oauth_token", oauth_token)
        obs.obs_data_set_default_string(settings, "twitch_refresh_token", refresh_token)
        obs.obs_data_set_default_string(settings, "twitch_broadcaster_id", broadcaster_id)

        # Debug logging to verify credentials are loaded
        if client_id or oauth_token or broadcaster_id:
            smartclip.logger.info("Loading Twitch credentials into OBS UI defaults")
            if client_id:
                smartclip.logger.info(f"Client ID loaded: {client_id[:8]}...")
            if oauth_token:
                smartclip.logger.info(f"OAuth token loaded: {oauth_token[:8]}...")
            if broadcaster_id:
                smartclip.logger.info(f"Broadcaster ID loaded: {broadcaster_id}")

def script_update(settings):
    """Update settings"""
    try:
        # Store previous values for change detection
        prev_config = smartclip.config.copy()

        # Legacy sensitivity for backward compatibility
        smartclip.config["emotion_sensitivity"] = obs.obs_data_get_double(settings, "emotion_sensitivity")

        # Separate detector sensitivities
        smartclip.config["basic_emotion_sensitivity"] = obs.obs_data_get_double(settings, "basic_emotion_sensitivity")
        smartclip.config["opensmile_sensitivity"] = obs.obs_data_get_double(settings, "opensmile_sensitivity")
        smartclip.config["vosk_sensitivity"] = obs.obs_data_get_double(settings, "vosk_sensitivity")

        # Update audio sources
        new_microphone_enabled = obs.obs_data_get_bool(settings, "microphone_enabled")
        new_microphone_source = obs.obs_data_get_string(settings, "microphone_source")
        new_voice_chat_enabled = obs.obs_data_get_bool(settings, "voice_chat_enabled")
        new_voice_chat_source = obs.obs_data_get_string(settings, "voice_chat_source")

        # Log changes
        if new_microphone_enabled != prev_config.get("microphone_enabled", True):
            smartclip.logger.info(f"Microphone monitoring {'enabled' if new_microphone_enabled else 'disabled'}")
        if new_microphone_source != prev_config.get("microphone_source", "Desktop Audio"):
            smartclip.logger.info(f"Microphone source updated: {new_microphone_source}")
        if new_voice_chat_enabled != prev_config.get("voice_chat_enabled", False):
            smartclip.logger.info(f"Voice chat monitoring {'enabled' if new_voice_chat_enabled else 'disabled'}")
        if new_voice_chat_source != prev_config.get("voice_chat_source", ""):
            smartclip.logger.info(f"Voice chat source updated: {new_voice_chat_source}")

        smartclip.config["microphone_enabled"] = new_microphone_enabled
        smartclip.config["microphone_source"] = new_microphone_source
        smartclip.config["voice_chat_enabled"] = new_voice_chat_enabled
        smartclip.config["voice_chat_source"] = new_voice_chat_source

        # Check if audio configuration changed and restart audio handler if needed
        audio_config_changed = (
            new_microphone_enabled != prev_config.get("microphone_enabled", True) or
            new_microphone_source != prev_config.get("microphone_source", "Desktop Audio") or
            new_voice_chat_enabled != prev_config.get("voice_chat_enabled", False) or
            new_voice_chat_source != prev_config.get("voice_chat_source", "")
        )

        if audio_config_changed and smartclip.running:
            smartclip.logger.info("Audio configuration changed, restarting audio handler...")
            # Stop current audio capture
            if smartclip.audio_handler:
                smartclip.audio_handler.stop_capture()

            # Reinitialize audio handler with new configuration
            audio_sources = []
            if smartclip.config.get("microphone_enabled", True):
                mic_source = smartclip.config.get("microphone_source", "")
                if mic_source:
                    audio_sources.append(mic_source)
                else:
                    # Auto-detect best audio source
                    best_source = smartclip._detect_best_audio_source()
                    if best_source:
                        audio_sources.append(best_source)
                        smartclip.config["microphone_source"] = best_source
                        smartclip.logger.info(f"Auto-detected microphone source: {best_source}")

            if smartclip.config.get("voice_chat_enabled", False):
                voice_chat_source = smartclip.config.get("voice_chat_source", "")
                if voice_chat_source:
                    audio_sources.append(voice_chat_source)

            # Fallback to auto-detection if no sources enabled
            if not audio_sources:
                best_source = smartclip._detect_best_audio_source()
                if best_source:
                    audio_sources = [best_source]
                    smartclip.logger.info(f"No sources configured, auto-detected: {best_source}")
                else:
                    # Last resort fallback
                    audio_sources = ["Zvuk plochy"]  # Czech default
                    smartclip.logger.warning("No audio sources detected, using Czech fallback")

            smartclip.audio_handler = AudioHandler(
                sources=audio_sources,
                sample_rate=16000,
                buffer_size=1024
            )

            # Restart audio capture
            smartclip.audio_handler.start_capture(smartclip.audio_callback)
            smartclip.logger.info(f"Audio handler restarted with sources: {audio_sources}")

        # Update enabled emotions
        enabled_emotions = []
        emotion_mapping = {
            "emotion_laughter": "laughter",
            "emotion_excitement": "excitement",
            "emotion_surprise": "surprise",
            "emotion_joy": "joy",
            "emotion_anger": "anger",
            "emotion_fear": "fear",
            "emotion_sadness": "sadness"
        }

        for ui_name, emotion_name in emotion_mapping.items():
            if obs.obs_data_get_bool(settings, ui_name):
                enabled_emotions.append(emotion_name)

        # Log changes in enabled emotions
        prev_enabled_emotions = prev_config.get("enabled_emotions", [])
        if set(enabled_emotions) != set(prev_enabled_emotions):
            smartclip.logger.info(f"Enabled emotions updated: {', '.join(enabled_emotions) if enabled_emotions else 'none'}")

        smartclip.config["enabled_emotions"] = enabled_emotions

        # Update Czech activation phrases
        phrases_text = obs.obs_data_get_string(settings, "activation_phrases")
        if phrases_text:
            # Split by comma and clean up
            phrases = [phrase.strip() for phrase in phrases_text.split(",") if phrase.strip()]
            prev_phrases = prev_config.get("activation_phrases", [])
            if phrases != prev_phrases:
                smartclip.config["activation_phrases"] = phrases
                smartclip.logger.info(f"Czech activation phrases updated: {len(phrases)} phrases")
            else:
                smartclip.config["activation_phrases"] = phrases
        else:
            prev_phrases = prev_config.get("activation_phrases", [])
            if prev_phrases:  # Only log if we had phrases before
                smartclip.logger.info("Czech activation phrases cleared")
            smartclip.config["activation_phrases"] = []

        # Update English activation phrases
        english_phrases_text = obs.obs_data_get_string(settings, "english_activation_phrases")
        if english_phrases_text:
            # Split by comma and clean up
            english_phrases = [phrase.strip() for phrase in english_phrases_text.split(",") if phrase.strip()]
            prev_english_phrases = prev_config.get("english_activation_phrases", [])
            if english_phrases != prev_english_phrases:
                smartclip.config["english_activation_phrases"] = english_phrases
                smartclip.logger.info(f"English activation phrases updated: {len(english_phrases)} phrases")
            else:
                smartclip.config["english_activation_phrases"] = english_phrases
        else:
            prev_english_phrases = prev_config.get("english_activation_phrases", [])
            if prev_english_phrases:  # Only log if we had phrases before
                smartclip.logger.info("English activation phrases cleared")
            smartclip.config["english_activation_phrases"] = []

        # Update Twitch settings (preserve existing values if UI is empty)
        new_client_id = obs.obs_data_get_string(settings, "twitch_client_id")
        prev_client_id = prev_config.get("twitch_client_id", "")

        # Only update if UI has a value OR if we're explicitly clearing a previously set value
        if new_client_id or not prev_client_id:
            if new_client_id != prev_client_id:
                if new_client_id:
                    smartclip.logger.info("Twitch Client ID updated")
                elif prev_client_id:
                    smartclip.logger.info("Twitch Client ID cleared")
            smartclip.config["twitch_client_id"] = new_client_id
        else:
            # UI is empty but we have a previous value - preserve it
            smartclip.config["twitch_client_id"] = prev_client_id
            smartclip.logger.debug("Preserving existing Client ID (UI empty)")

        new_oauth_token = obs.obs_data_get_string(settings, "twitch_oauth_token")
        prev_oauth_token = prev_config.get("twitch_oauth_token", "")

        # Only update if UI has a value OR if we're explicitly clearing a previously set value
        if new_oauth_token or not prev_oauth_token:
            if new_oauth_token != prev_oauth_token:
                if new_oauth_token:
                    smartclip.logger.info("Twitch OAuth token updated")
                elif prev_oauth_token:
                    smartclip.logger.info("Twitch OAuth token cleared")
            smartclip.config["twitch_oauth_token"] = new_oauth_token
        else:
            # UI is empty but we have a previous value - preserve it
            smartclip.config["twitch_oauth_token"] = prev_oauth_token
            smartclip.logger.debug("Preserving existing OAuth token (UI empty)")

        new_client_secret = obs.obs_data_get_string(settings, "twitch_client_secret")
        prev_client_secret = prev_config.get("twitch_client_secret", "")

        # Only update if UI has a value OR if we're explicitly clearing a previously set value
        if new_client_secret or not prev_client_secret:
            if new_client_secret != prev_client_secret:
                if new_client_secret:
                    smartclip.logger.info("Twitch Client Secret updated")
                elif prev_client_secret:
                    smartclip.logger.info("Twitch Client Secret cleared")
            smartclip.config["twitch_client_secret"] = new_client_secret
        else:
            # UI is empty but we have a previous value - preserve it
            smartclip.config["twitch_client_secret"] = prev_client_secret
            smartclip.logger.debug("Preserving existing Client Secret (UI empty)")

        new_refresh_token = obs.obs_data_get_string(settings, "twitch_refresh_token")
        prev_refresh_token = prev_config.get("twitch_refresh_token", "")

        # Only update if UI has a value OR if we're explicitly clearing a previously set value
        if new_refresh_token or not prev_refresh_token:
            if new_refresh_token != prev_refresh_token:
                if new_refresh_token:
                    smartclip.logger.info("Twitch Refresh Token updated")
                elif prev_refresh_token:
                    smartclip.logger.info("Twitch Refresh Token cleared")
            smartclip.config["twitch_refresh_token"] = new_refresh_token
        else:
            # UI is empty but we have a previous value - preserve it
            smartclip.config["twitch_refresh_token"] = prev_refresh_token
            smartclip.logger.debug("Preserving existing Refresh Token (UI empty)")

        new_broadcaster_id = obs.obs_data_get_string(settings, "twitch_broadcaster_id")
        prev_broadcaster_id = prev_config.get("twitch_broadcaster_id", "")

        # Only update if UI has a value OR if we're explicitly clearing a previously set value
        if new_broadcaster_id or not prev_broadcaster_id:
            if new_broadcaster_id != prev_broadcaster_id:
                if new_broadcaster_id:
                    smartclip.logger.info("Twitch Broadcaster ID updated")
                elif prev_broadcaster_id:
                    smartclip.logger.info("Twitch Broadcaster ID cleared")
            smartclip.config["twitch_broadcaster_id"] = new_broadcaster_id
        else:
            # UI is empty but we have a previous value - preserve it
            smartclip.config["twitch_broadcaster_id"] = prev_broadcaster_id
            smartclip.logger.debug("Preserving existing Broadcaster ID (UI empty)")

        # Update component settings (with change logging)
        new_basic_emotion_enabled = obs.obs_data_get_bool(settings, "basic_emotion_enabled")
        if new_basic_emotion_enabled != prev_config.get("basic_emotion_enabled", True):
            smartclip.logger.info(f"Basic emotion detection {'enabled' if new_basic_emotion_enabled else 'disabled'}")
        smartclip.config["basic_emotion_enabled"] = new_basic_emotion_enabled

        new_opensmile_enabled = obs.obs_data_get_bool(settings, "opensmile_enabled")
        if new_opensmile_enabled != prev_config.get("opensmile_enabled", True):
            smartclip.logger.info(f"OpenSMILE detection {'enabled' if new_opensmile_enabled else 'disabled'}")
        smartclip.config["opensmile_enabled"] = new_opensmile_enabled

        new_vosk_enabled = obs.obs_data_get_bool(settings, "vosk_enabled")
        if new_vosk_enabled != prev_config.get("vosk_enabled", True):
            smartclip.logger.info(f"Vosk speech recognition {'enabled' if new_vosk_enabled else 'disabled'}")
        smartclip.config["vosk_enabled"] = new_vosk_enabled

        new_quality_scoring_enabled = obs.obs_data_get_bool(settings, "quality_scoring_enabled")
        if new_quality_scoring_enabled != prev_config.get("quality_scoring_enabled", True):
            smartclip.logger.info(f"Quality scoring {'enabled' if new_quality_scoring_enabled else 'disabled'}")
        smartclip.config["quality_scoring_enabled"] = new_quality_scoring_enabled

        new_auto_start_on_stream = obs.obs_data_get_bool(settings, "auto_start_on_stream")
        if new_auto_start_on_stream != prev_config.get("auto_start_on_stream", False):
            smartclip.logger.info(f"Auto-start on stream {'enabled' if new_auto_start_on_stream else 'disabled'}")
        smartclip.config["auto_start_on_stream"] = new_auto_start_on_stream

        # Update clip duration
        new_clip_duration = obs.obs_data_get_int(settings, "clip_duration")
        if new_clip_duration != prev_config.get("clip_duration", 30):
            smartclip.logger.info(f"Clip duration changed to {new_clip_duration} seconds")
        smartclip.config["clip_duration"] = new_clip_duration

        # Update language configuration
        new_language = obs.obs_data_get_string(settings, "language")
        if new_language != prev_config.get("language", "en"):
            smartclip.logger.info(f"Language changed to {'English' if new_language == 'en' else 'Czech'}")
            smartclip.config["language"] = new_language
            smartclip.texts = smartclip.get_texts()  # Update localized texts

        # Update logging configuration
        enable_debug_logging = obs.obs_data_get_bool(settings, "enable_debug_logging")
        if enable_debug_logging != prev_config.get("advanced_settings", {}).get("enable_debug_logging", False):
            smartclip.logger.info(f"Debug logging {'enabled' if enable_debug_logging else 'disabled'}")
            if "advanced_settings" not in smartclip.config:
                smartclip.config["advanced_settings"] = {}
            smartclip.config["advanced_settings"]["enable_debug_logging"] = enable_debug_logging
            smartclip._configure_logging()  # Reconfigure logging with new setting

        # Handle auto-start setting change
        if new_auto_start_on_stream:
            smartclip.start_stream_monitoring()
        else:
            smartclip.stop_stream_monitoring()

        # Update Twitch API credentials only if they actually changed
        if smartclip.twitch_api:
            current_credentials = {
                "client_id": smartclip.config.get("twitch_client_id", ""),
                "oauth_token": smartclip.config.get("twitch_oauth_token", ""),
                "broadcaster_id": smartclip.config.get("twitch_broadcaster_id", ""),
                "client_secret": smartclip.config.get("twitch_client_secret", ""),
                "refresh_token": smartclip.config.get("twitch_refresh_token", "")
            }

            previous_credentials = {
                "client_id": prev_config.get("twitch_client_id", ""),
                "oauth_token": prev_config.get("twitch_oauth_token", ""),
                "broadcaster_id": prev_config.get("twitch_broadcaster_id", ""),
                "client_secret": prev_config.get("twitch_client_secret", ""),
                "refresh_token": prev_config.get("twitch_refresh_token", "")
            }

            if current_credentials != previous_credentials:
                smartclip.twitch_api.update_credentials(**current_credentials)

        # Handle basic emotion detector enable/disable
        basic_emotion_enabled = smartclip.config.get("basic_emotion_enabled", True)
        if basic_emotion_enabled and not smartclip.emotion_detector:
            # Enable basic emotion detector
            try:
                basic_sensitivity = smartclip.config.get("basic_emotion_sensitivity",
                                                        smartclip.config.get("emotion_sensitivity", 0.7))
                smartclip.emotion_detector = EmotionDetector(
                    enabled_emotions=smartclip.config.get("enabled_emotions", []),
                    sensitivity=basic_sensitivity
                )
                # Note: Enable/disable logging is handled by configuration change detection
            except Exception as e:
                smartclip.logger.error(f"Failed to enable basic emotion detector: {e}")
        elif not basic_emotion_enabled and smartclip.emotion_detector:
            # Disable basic emotion detector
            smartclip.emotion_detector = None
            # Note: Enable/disable logging is handled by configuration change detection

        # Handle OpenSMILE detector enable/disable
        opensmile_enabled = smartclip.config.get("opensmile_enabled", True)
        if opensmile_enabled and not smartclip.opensmile_detector:
            # Enable OpenSMILE detector
            try:
                opensmile_sensitivity = smartclip.config.get("opensmile_sensitivity",
                                                            smartclip.config.get("emotion_sensitivity", 0.7))
                smartclip.opensmile_detector = OpenSMILEDetector(
                    config_file="IS09_emotion.conf",
                    sensitivity=opensmile_sensitivity,
                    result_callback=smartclip._handle_opensmile_detection
                )
                smartclip.logger.info(f"OpenSMILE detector enabled (sensitivity: {opensmile_sensitivity})")

                # Start detection if main detection is running
                if smartclip.running:
                    smartclip.opensmile_detector.start_detection()

            except Exception as e:
                smartclip.logger.warning(f"OpenSMILE initialization failed: {e}")
                smartclip.opensmile_detector = None

        elif not opensmile_enabled and smartclip.opensmile_detector:
            # Disable OpenSMILE detector
            smartclip.opensmile_detector.stop_detection()
            smartclip.opensmile_detector = None
            smartclip.logger.info("OpenSMILE detector disabled")

        # Update component settings if they exist (only log if values changed)
        if smartclip.emotion_detector:
            basic_sensitivity = smartclip.config.get("basic_emotion_sensitivity",
                                                    smartclip.config.get("emotion_sensitivity", 0.7))
            prev_basic_sensitivity = prev_config.get("basic_emotion_sensitivity",
                                                    prev_config.get("emotion_sensitivity", 0.7))
            if abs(basic_sensitivity - prev_basic_sensitivity) > 0.001:  # Only update if changed
                smartclip.emotion_detector.set_sensitivity(basic_sensitivity, log_change=True)
            else:
                smartclip.emotion_detector.set_sensitivity(basic_sensitivity, log_change=False)

            # Update enabled emotions if they changed
            current_enabled_emotions = smartclip.config.get("enabled_emotions", [])
            prev_enabled_emotions = prev_config.get("enabled_emotions", [])

            if current_enabled_emotions != prev_enabled_emotions:
                smartclip.emotion_detector.set_enabled_emotions(current_enabled_emotions)
                smartclip.logger.info(f"Basic emotion detector emotions updated: {len(current_enabled_emotions)} emotions")

        if smartclip.opensmile_detector:
            opensmile_sensitivity = smartclip.config.get("opensmile_sensitivity",
                                                        smartclip.config.get("emotion_sensitivity", 0.7))
            prev_opensmile_sensitivity = prev_config.get("opensmile_sensitivity",
                                                        prev_config.get("emotion_sensitivity", 0.7))
            if abs(opensmile_sensitivity - prev_opensmile_sensitivity) > 0.001:  # Only update if changed
                smartclip.opensmile_detector.set_sensitivity(opensmile_sensitivity, log_change=True)
            else:
                smartclip.opensmile_detector.set_sensitivity(opensmile_sensitivity, log_change=False)

        if smartclip.vosk_detector:
            vosk_sensitivity = smartclip.config.get("vosk_sensitivity",
                                                   smartclip.config.get("emotion_sensitivity", 0.7))
            prev_vosk_sensitivity = prev_config.get("vosk_sensitivity",
                                                   prev_config.get("emotion_sensitivity", 0.7))
            if abs(vosk_sensitivity - prev_vosk_sensitivity) > 0.001:  # Only update if changed
                smartclip.vosk_detector.set_confidence_threshold(vosk_sensitivity, log_change=True)
            else:
                smartclip.vosk_detector.set_confidence_threshold(vosk_sensitivity, log_change=False)

            # Update activation phrases if they changed
            current_czech_phrases = smartclip.config.get("activation_phrases", [])
            current_english_phrases = smartclip.config.get("english_activation_phrases", [])
            prev_czech_phrases = prev_config.get("activation_phrases", [])
            prev_english_phrases = prev_config.get("english_activation_phrases", [])

            phrases_changed = (current_czech_phrases != prev_czech_phrases or
                             current_english_phrases != prev_english_phrases)

            if phrases_changed:
                smartclip.vosk_detector.update_activation_phrases(
                    czech_phrases=current_czech_phrases,
                    english_phrases=current_english_phrases,
                    log_change=True
                )
            else:
                # Still update but don't log (in case of first load)
                smartclip.vosk_detector.update_activation_phrases(
                    czech_phrases=current_czech_phrases,
                    english_phrases=current_english_phrases,
                    log_change=False
                )

        # Save configuration to file after all updates
        try:
            config_path = os.path.join(plugin_dir, 'smartclip_cz_config.json')
            save_success = smartclip.config_manager.save_config(config_path, smartclip.config)
            if save_success:
                smartclip.logger.debug("Configuration saved to file successfully")
            else:
                smartclip.logger.error("Failed to save configuration to file")
        except Exception as save_error:
            smartclip.logger.error(f"Error saving configuration: {save_error}")

    except Exception as e:
        obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] Error updating settings: {e}")

def script_load(settings):
    """Script loaded"""
    try:
        smartclip.load_config()
        smartclip.initialize_components()

        # Populate OBS UI with config values (especially Twitch credentials)
        if smartclip.config:
            # Set Twitch credentials in OBS UI from config
            client_id = smartclip.config.get("twitch_client_id", "")
            client_secret = smartclip.config.get("twitch_client_secret", "")
            oauth_token = smartclip.config.get("twitch_oauth_token", "")
            refresh_token = smartclip.config.get("twitch_refresh_token", "")
            broadcaster_id = smartclip.config.get("twitch_broadcaster_id", "")

            if client_id:
                obs.obs_data_set_string(settings, "twitch_client_id", client_id)
            if client_secret:
                obs.obs_data_set_string(settings, "twitch_client_secret", client_secret)
            if oauth_token:
                obs.obs_data_set_string(settings, "twitch_oauth_token", oauth_token)
            if refresh_token:
                obs.obs_data_set_string(settings, "twitch_refresh_token", refresh_token)
            if broadcaster_id:
                obs.obs_data_set_string(settings, "twitch_broadcaster_id", broadcaster_id)

            # Log if we populated any credentials
            if client_id or oauth_token or broadcaster_id:
                smartclip.logger.info("Populated OBS UI with Twitch credentials from config")
                if client_id:
                    smartclip.logger.info(f"Client ID populated: {client_id[:8]}...")
                if oauth_token:
                    smartclip.logger.info(f"OAuth token populated: {oauth_token[:8]}...")
                if broadcaster_id:
                    smartclip.logger.info(f"Broadcaster ID populated: {broadcaster_id}")

        smartclip._log_to_obs(obs.LOG_INFO, "[SmartClip CZ] Python plugin loaded successfully")
    except Exception as e:
        obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] Load error: {e}")

def script_unload():
    """Script unloaded"""
    try:
        smartclip.stop_detection()
        smartclip._log_to_obs(obs.LOG_INFO, "[SmartClip CZ] Python plugin unloaded")
    except Exception as e:
        obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] Unload error: {e}")

# Callback functions
def language_changed_callback(props, prop, settings):
    """Language selection callback - triggers UI refresh"""
    try:
        # This will trigger script_update which handles the language change
        return True
    except Exception as e:
        obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] Language callback error: {e}")
    return True

def start_detection_callback(props, prop):
    """Start detection button callback"""
    try:
        success = smartclip.start_detection()
        if success:
            smartclip._log_to_obs(obs.LOG_INFO, "[SmartClip CZ] Detection started via UI")
        else:
            obs.script_log(obs.LOG_WARNING, "[SmartClip CZ] Failed to start detection")
    except Exception as e:
        obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] Start callback error: {e}")
    return True

def stop_detection_callback(props, prop):
    """Stop detection button callback"""
    try:
        smartclip.stop_detection()
        smartclip._log_to_obs(obs.LOG_INFO, "[SmartClip CZ] Detection stopped via UI")
    except Exception as e:
        obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] Stop callback error: {e}")
    return True

def reload_config_callback(props, prop):
    """Reload config button callback"""
    try:
        smartclip.reload_config()
        smartclip._log_to_obs(obs.LOG_INFO, "[SmartClip CZ] Configuration reloaded")
    except Exception as e:
        obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] Reload callback error: {e}")
    return True

def show_statistics_callback(props, prop):
    """Show statistics button callback"""
    try:
        stats = smartclip.get_statistics()
        stats_text = f"""
SmartClip CZ Statistics:
- Running: {stats['running']}
- Total Detections: {stats['total_detections']}
- Clips Created: {stats['clips_created']}
- Success Rate: {stats['success_rate']:.1%}
- Session Runtime: {stats['session_runtime']}
- Top Emotions: {list(stats['emotions_detected'].keys())[:3]}
- Top Phrases: {list(stats['phrases_detected'].keys())[:3]}
        """
        smartclip._log_to_obs(obs.LOG_INFO, f"[SmartClip CZ] {stats_text}")
    except Exception as e:
        obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] Statistics error: {e}")
    return True

def test_detection_callback(props, prop):
    """Test detection button callback"""
    try:
        # Generate test audio data
        test_audio = np.random.normal(0, 0.3, 1024).astype(np.float32)

        # Add a simulated "laughter" pattern
        t = np.linspace(0, 1, 1024)
        laughter_signal = np.sin(2 * np.pi * 800 * t) * np.exp(-t * 2) * 0.5
        test_audio += laughter_signal

        # Process with emotion detector
        if smartclip.emotion_detector:
            result = smartclip.emotion_detector.detect(test_audio)
            if result:
                smartclip._log_to_obs(obs.LOG_INFO, f"[SmartClip CZ] Test detection: {result.emotion_type.value} ({result.confidence:.2f})")
            else:
                smartclip._log_to_obs(obs.LOG_INFO, "[SmartClip CZ] Test detection: No emotion detected")
        else:
            obs.script_log(obs.LOG_WARNING, "[SmartClip CZ] Emotion detector not available for testing")

    except Exception as e:
        obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] Test callback error: {e}")
    return True

def force_token_refresh_callback(props, prop):
    """Force token refresh button callback for debugging"""
    try:
        smartclip._log_to_obs(obs.LOG_INFO, "[SmartClip CZ] Manual token refresh requested")

        if not smartclip.twitch_api:
            obs.script_log(obs.LOG_WARNING, "[SmartClip CZ] Twitch API not initialized")
            return True

        # Force token refresh
        success = smartclip.twitch_api.force_token_refresh()

        if success:
            smartclip._log_to_obs(obs.LOG_INFO, "[SmartClip CZ] Manual token refresh successful")
            # Test API after refresh
            if smartclip.twitch_api.is_configured():
                smartclip._log_to_obs(obs.LOG_INFO, "[SmartClip CZ] API validation successful after refresh")
            else:
                obs.script_log(obs.LOG_WARNING, "[SmartClip CZ] API validation failed after refresh")
        else:
            obs.script_log(obs.LOG_ERROR, "[SmartClip CZ] Manual token refresh failed")

    except Exception as e:
        obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] Force token refresh error: {e}")
    return True

def show_confidence_widget_disabled_callback(props, prop):
    """Disabled confidence widget button callback"""
    try:
        smartclip._log_to_obs(obs.LOG_INFO, "[SmartClip CZ] Confidence widget is temporarily disabled")
        smartclip._log_to_obs(obs.LOG_INFO, "[SmartClip CZ] This feature is being improved and will be re-enabled in a future update")
    except Exception as e:
        obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] Disabled callback error: {e}")
    return True

def show_confidence_widget_callback(props, prop):
    """Show confidence widget button callback"""
    try:
        import subprocess
        import os

        # Get the path to the confidence widgets
        script_dir = os.path.dirname(os.path.abspath(__file__))
        widgets_dir = os.path.join(script_dir, "widgets")
        obs_widget_path = os.path.join(widgets_dir, "obs_confidence_widget.py")
        standalone_widget_path = os.path.join(widgets_dir, "standalone_confidence_widget.py")
        simple_widget_path = os.path.join(widgets_dir, "simple_confidence_widget.py")

        smartclip._log_to_obs(obs.LOG_INFO, f"[SmartClip CZ] Script directory: {script_dir}")

        # Check which widgets exist (prefer OBS-compatible)
        obs_exists = os.path.exists(obs_widget_path)
        standalone_exists = os.path.exists(standalone_widget_path)
        simple_exists = os.path.exists(simple_widget_path)

        smartclip._log_to_obs(obs.LOG_INFO, f"[SmartClip CZ] OBS widget exists: {obs_exists}")
        smartclip._log_to_obs(obs.LOG_INFO, f"[SmartClip CZ] Standalone widget exists: {standalone_exists}")
        smartclip._log_to_obs(obs.LOG_INFO, f"[SmartClip CZ] Simple widget exists: {simple_exists}")

        # Try OBS widget first (designed for OBS subprocess)
        if obs_exists:
            widget_path = obs_widget_path
            widget_name = "obs_confidence_widget.py"
        elif standalone_exists:
            widget_path = standalone_widget_path
            widget_name = "standalone_confidence_widget.py"
        elif simple_exists:
            widget_path = simple_widget_path
            widget_name = "simple_confidence_widget.py"
        else:
            obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] No confidence widget found in: {widgets_dir}")
            return True

        smartclip._log_to_obs(obs.LOG_INFO, f"[SmartClip CZ] Using widget: {widget_name}")

        # Launch the confidence widget in a separate process
        try:
            # Use the widget path we determined above
            widget_full_path = widget_path

            smartclip._log_to_obs(obs.LOG_INFO, f"[SmartClip CZ] Widget path: {widget_full_path}")
            smartclip._log_to_obs(obs.LOG_INFO, f"[SmartClip CZ] Working directory: {script_dir}")

            # Create environment with locale suppression
            widget_env = dict(os.environ)
            widget_env.update({
                'PYTHONIOENCODING': 'utf-8',
                'LC_ALL': 'C',
                'LANG': 'C',
                'LC_CTYPE': 'C',
                'PYTHONPATH': script_dir,
                # Suppress Qt/tkinter locale warnings
                'QT_LOGGING_RULES': '*.debug=false',
                'PYTHONWARNINGS': 'ignore'
            })

            if sys.platform == "win32":
                # Windows - launch with locale suppression environment
                process = subprocess.Popen([sys.executable, widget_full_path],
                                         cwd=script_dir,
                                         creationflags=subprocess.CREATE_NEW_CONSOLE,
                                         env=widget_env,
                                         stderr=subprocess.DEVNULL,
                                         stdout=subprocess.DEVNULL)
            else:
                # Unix-like systems
                process = subprocess.Popen([sys.executable, widget_full_path],
                                         cwd=script_dir,
                                         env=widget_env,
                                         stderr=subprocess.DEVNULL,
                                         stdout=subprocess.DEVNULL)

            widget_type = "standalone" if "standalone" in widget_name else ("simple" if "simple" in widget_name else "advanced")
            smartclip._log_to_obs(obs.LOG_INFO, f"[SmartClip CZ] Confidence widget ({widget_type}) launched successfully")
            smartclip._log_to_obs(obs.LOG_INFO, f"[SmartClip CZ] Process ID: {process.pid}")

        except Exception as launch_error:
            obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] Failed to launch widget: {launch_error}")
            import traceback
            obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] Traceback: {traceback.format_exc()}")

    except Exception as e:
        obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] Confidence widget callback error: {e}")
        import traceback
        obs.script_log(obs.LOG_ERROR, f"[SmartClip CZ] Traceback: {traceback.format_exc()}")
    return True


