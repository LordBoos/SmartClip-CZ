"""
Configuration Manager for SmartClip CZ
Handles loading, saving, and validation of plugin configuration

Author: Jakub Kolář (LordBoos)
Email: lordboos@gmail.com
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

class ConfigManager:
    """Manages plugin configuration"""
    
    def __init__(self):
        self.logger = logging.getLogger('SmartClipCZ.ConfigManager')
        
        # Default configuration schema
        self.default_config = {
            "version": "2.0.0",
            "enabled_emotions": ["laughter", "excitement", "surprise", "joy", "anger", "fear", "sadness", "neutral"],
            "emotion_sensitivity": 0.7,
            "activation_phrases": [
                "to je skvělé", "wow", "úžasné", "perfektní", "super", "bomba",
                "co to bylo", "to je šílené", "neuvěřitelné", "holy shit",
                "to je hustý", "parádní", "skvělý", "výborný"
            ],
            "audio_sources": ["Desktop Audio"],
            "twitch_client_id": "",
            "twitch_oauth_token": "",
            "twitch_broadcaster_id": "",
            "clip_duration": 30,
            "quality_scoring_enabled": True,
            "opensmile_enabled": True,
            "vosk_enabled": True,
            "gaming_profiles": {
                "fps": {
                    "emotion_sensitivity": 0.8,
                    "cooldown": 1.5,
                    "enabled_emotions": ["excitement", "anger", "surprise"],
                    "activation_phrases": ["headshot", "ace", "clutch", "wow", "holy shit"]
                },
                "strategy": {
                    "emotion_sensitivity": 0.6,
                    "cooldown": 3.0,
                    "enabled_emotions": ["excitement", "surprise", "joy"],
                    "activation_phrases": ["victory", "win", "skvělé", "perfektní"]
                },
                "casual": {
                    "emotion_sensitivity": 0.7,
                    "cooldown": 2.0,
                    "enabled_emotions": ["laughter", "excitement", "surprise", "joy"],
                    "activation_phrases": ["to je skvělé", "wow", "úžasné", "super"]
                }
            },
            "current_profile": "casual",
            "advanced_settings": {
                "min_clip_interval": 30,
                "max_clips_per_hour": 12,
                "confidence_boost_for_multiple_detectors": 0.2,
                "enable_debug_logging": False,
                "audio_buffer_size": 1024,
                "detection_smoothing_window": 3
            },
            "ui_settings": {
                "show_confidence_visualization": True,
                "show_real_time_stats": True,
                "notification_level": "important_only"
            }
        }
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                
                # Validate and merge with defaults
                config = self._validate_and_merge_config(loaded_config)
                
                self.logger.info(f"Configuration loaded from {config_path}")
                return config
            else:
                self.logger.info(f"Config file not found at {config_path}, using defaults")
                # Create default config file
                self.save_config(config_path, self.default_config)
                return self.default_config.copy()
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in config file: {e}")
            return self.default_config.copy()
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return self.default_config.copy()
    
    def save_config(self, config_path: str, config: Dict[str, Any]) -> bool:
        """Save configuration to JSON file"""
        try:
            # Add metadata
            config_with_metadata = config.copy()
            config_with_metadata['_metadata'] = {
                'last_saved': datetime.now().isoformat(),
                'version': self.default_config['version']
            }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_with_metadata, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Configuration saved to {config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
            return False
    
    def _validate_and_merge_config(self, loaded_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate loaded config and merge with defaults"""
        try:
            # Start with default config
            merged_config = self.default_config.copy()
            
            # Recursively merge loaded config
            self._deep_merge(merged_config, loaded_config)
            
            # Validate specific fields
            merged_config = self._validate_config_fields(merged_config)
            
            return merged_config
            
        except Exception as e:
            self.logger.error(f"Error validating config: {e}")
            return self.default_config.copy()
    
    def _deep_merge(self, base_dict: Dict, update_dict: Dict):
        """Recursively merge dictionaries"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_merge(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def _validate_config_fields(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and fix specific configuration fields"""
        try:
            # Validate emotion sensitivity
            if not isinstance(config.get('emotion_sensitivity'), (int, float)):
                config['emotion_sensitivity'] = 0.7
            else:
                config['emotion_sensitivity'] = max(0.1, min(1.0, config['emotion_sensitivity']))
            
            # Validate enabled emotions
            valid_emotions = ["laughter", "excitement", "surprise", "joy", "anger", "fear", "sadness", "neutral"]
            if not isinstance(config.get('enabled_emotions'), list):
                config['enabled_emotions'] = valid_emotions
            else:
                config['enabled_emotions'] = [e for e in config['enabled_emotions'] if e in valid_emotions]
                if not config['enabled_emotions']:
                    config['enabled_emotions'] = valid_emotions
            
            # Validate activation phrases
            if not isinstance(config.get('activation_phrases'), list):
                config['activation_phrases'] = self.default_config['activation_phrases']
            else:
                # Filter out empty phrases and ensure they're strings
                config['activation_phrases'] = [str(phrase).strip() for phrase in config['activation_phrases'] 
                                              if phrase and str(phrase).strip()]
                if not config['activation_phrases']:
                    config['activation_phrases'] = self.default_config['activation_phrases']
            
            # Validate audio sources
            if not isinstance(config.get('audio_sources'), list):
                config['audio_sources'] = ["Desktop Audio"]
            
            # Validate Twitch settings
            twitch_fields = ['twitch_client_id', 'twitch_oauth_token', 'twitch_broadcaster_id']
            for field in twitch_fields:
                if not isinstance(config.get(field), str):
                    config[field] = ""
            
            # Validate clip duration
            if not isinstance(config.get('clip_duration'), (int, float)):
                config['clip_duration'] = 30
            else:
                config['clip_duration'] = max(10, min(300, config['clip_duration']))
            
            # Validate boolean settings
            boolean_fields = ['quality_scoring_enabled', 'opensmile_enabled', 'vosk_enabled']
            for field in boolean_fields:
                if not isinstance(config.get(field), bool):
                    config[field] = True
            
            # Validate gaming profiles
            if not isinstance(config.get('gaming_profiles'), dict):
                config['gaming_profiles'] = self.default_config['gaming_profiles']
            else:
                config['gaming_profiles'] = self._validate_gaming_profiles(config['gaming_profiles'])
            
            # Validate current profile
            if config.get('current_profile') not in config['gaming_profiles']:
                config['current_profile'] = 'casual'
            
            # Validate advanced settings
            if not isinstance(config.get('advanced_settings'), dict):
                config['advanced_settings'] = self.default_config['advanced_settings']
            else:
                config['advanced_settings'] = self._validate_advanced_settings(config['advanced_settings'])
            
            return config
            
        except Exception as e:
            self.logger.error(f"Error validating config fields: {e}")
            return self.default_config.copy()
    
    def _validate_gaming_profiles(self, profiles: Dict) -> Dict:
        """Validate gaming profiles configuration"""
        try:
            validated_profiles = {}
            
            for profile_name, profile_config in profiles.items():
                if not isinstance(profile_config, dict):
                    continue
                
                validated_profile = {
                    'emotion_sensitivity': max(0.1, min(1.0, profile_config.get('emotion_sensitivity', 0.7))),
                    'cooldown': max(0.5, min(10.0, profile_config.get('cooldown', 2.0))),
                    'enabled_emotions': profile_config.get('enabled_emotions', self.default_config['enabled_emotions']),
                    'activation_phrases': profile_config.get('activation_phrases', self.default_config['activation_phrases'])
                }
                
                # Validate emotions list
                valid_emotions = ["laughter", "excitement", "surprise", "joy", "anger", "fear", "sadness", "neutral"]
                if isinstance(validated_profile['enabled_emotions'], list):
                    validated_profile['enabled_emotions'] = [e for e in validated_profile['enabled_emotions'] 
                                                           if e in valid_emotions]
                if not validated_profile['enabled_emotions']:
                    validated_profile['enabled_emotions'] = valid_emotions
                
                # Validate phrases list
                if isinstance(validated_profile['activation_phrases'], list):
                    validated_profile['activation_phrases'] = [str(p).strip() for p in validated_profile['activation_phrases'] 
                                                             if p and str(p).strip()]
                if not validated_profile['activation_phrases']:
                    validated_profile['activation_phrases'] = self.default_config['activation_phrases']
                
                validated_profiles[profile_name] = validated_profile
            
            # Ensure default profiles exist
            for default_profile in ['fps', 'strategy', 'casual']:
                if default_profile not in validated_profiles:
                    validated_profiles[default_profile] = self.default_config['gaming_profiles'][default_profile]
            
            return validated_profiles
            
        except Exception as e:
            self.logger.error(f"Error validating gaming profiles: {e}")
            return self.default_config['gaming_profiles']
    
    def _validate_advanced_settings(self, settings: Dict) -> Dict:
        """Validate advanced settings"""
        try:
            validated_settings = self.default_config['advanced_settings'].copy()
            
            # Validate numeric settings
            numeric_settings = {
                'min_clip_interval': (5, 300),
                'max_clips_per_hour': (1, 60),
                'confidence_boost_for_multiple_detectors': (0.0, 1.0),
                'audio_buffer_size': (256, 8192),
                'detection_smoothing_window': (1, 10)
            }
            
            for setting, (min_val, max_val) in numeric_settings.items():
                if setting in settings and isinstance(settings[setting], (int, float)):
                    validated_settings[setting] = max(min_val, min(max_val, settings[setting]))
            
            # Validate boolean settings
            boolean_settings = ['enable_debug_logging']
            for setting in boolean_settings:
                if setting in settings and isinstance(settings[setting], bool):
                    validated_settings[setting] = settings[setting]
            
            return validated_settings
            
        except Exception as e:
            self.logger.error(f"Error validating advanced settings: {e}")
            return self.default_config['advanced_settings']
    
    def get_profile_config(self, config: Dict[str, Any], profile_name: str) -> Dict[str, Any]:
        """Get configuration for a specific gaming profile"""
        try:
            if profile_name not in config.get('gaming_profiles', {}):
                profile_name = 'casual'
            
            profile_config = config['gaming_profiles'][profile_name].copy()
            
            # Merge with base config
            merged_config = config.copy()
            merged_config.update(profile_config)
            merged_config['current_profile'] = profile_name
            
            return merged_config
            
        except Exception as e:
            self.logger.error(f"Error getting profile config: {e}")
            return config
    
    def create_backup(self, config_path: str) -> bool:
        """Create a backup of the current configuration"""
        try:
            if not os.path.exists(config_path):
                return False
            
            backup_path = f"{config_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            with open(config_path, 'r', encoding='utf-8') as src:
                with open(backup_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            
            self.logger.info(f"Configuration backup created: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating config backup: {e}")
            return False
    
    def validate_twitch_config(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Validate Twitch configuration and return validation results"""
        results = {
            'client_id': 'valid' if config.get('twitch_client_id') else 'missing',
            'oauth_token': 'valid' if config.get('twitch_oauth_token') else 'missing',
            'broadcaster_id': 'valid' if config.get('twitch_broadcaster_id') else 'missing'
        }
        
        # Additional validation could be added here (format checks, etc.)
        
        return results
    
    def get_config_summary(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get a summary of the current configuration"""
        try:
            return {
                'version': config.get('version', 'unknown'),
                'current_profile': config.get('current_profile', 'unknown'),
                'enabled_emotions_count': len(config.get('enabled_emotions', [])),
                'activation_phrases_count': len(config.get('activation_phrases', [])),
                'audio_sources_count': len(config.get('audio_sources', [])),
                'twitch_configured': bool(config.get('twitch_client_id') and 
                                        config.get('twitch_oauth_token') and 
                                        config.get('twitch_broadcaster_id')),
                'opensmile_enabled': config.get('opensmile_enabled', False),
                'vosk_enabled': config.get('vosk_enabled', False),
                'quality_scoring_enabled': config.get('quality_scoring_enabled', False),
                'emotion_sensitivity': config.get('emotion_sensitivity', 0.7)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting config summary: {e}")
            return {}
