"""
UI Manager for SmartClip CZ
Handles user interface elements and real-time visualization
"""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import threading

class UIManager:
    """Manages UI elements and real-time visualization"""
    
    def __init__(self, smartclip_instance):
        self.smartclip = smartclip_instance
        self.logger = logging.getLogger('SmartClipCZ.UIManager')
        
        # Visualization data
        self.audio_levels = []
        self.confidence_history = []
        self.detection_history = []
        self.max_history = 100
        
        # UI state
        self.visualization_active = False
        self.update_thread = None
        self.update_interval = 0.1  # 100ms updates
        
        # Statistics for display
        self.display_stats = {
            'current_audio_level': 0.0,
            'last_detection': None,
            'detections_last_minute': 0,
            'clips_created_session': 0,
            'session_start_time': datetime.now()
        }
        
        self.logger.info("UI Manager initialized")
    
    def start_visualization(self):
        """Start real-time visualization updates"""
        try:
            if self.visualization_active:
                return
            
            self.visualization_active = True
            self.update_thread = threading.Thread(target=self._visualization_loop, daemon=True)
            self.update_thread.start()
            
            self.logger.info("Real-time visualization started")
            
        except Exception as e:
            self.logger.error(f"Error starting visualization: {e}")
    
    def stop_visualization(self):
        """Stop real-time visualization updates"""
        try:
            self.visualization_active = False
            
            if self.update_thread and self.update_thread.is_alive():
                self.update_thread.join(timeout=1)
            
            self.logger.info("Real-time visualization stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping visualization: {e}")
    
    def _visualization_loop(self):
        """Main visualization update loop"""
        self.logger.info("Visualization loop started")
        
        while self.visualization_active:
            try:
                # Update audio level
                self._update_audio_level()
                
                # Update detection statistics
                self._update_detection_stats()
                
                # Update confidence history
                self._update_confidence_history()
                
                # Clean old data
                self._cleanup_old_data()
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"Error in visualization loop: {e}")
                time.sleep(1)
        
        self.logger.info("Visualization loop ended")
    
    def _update_audio_level(self):
        """Update current audio level"""
        try:
            if self.smartclip.audio_handler:
                current_level = self.smartclip.audio_handler.get_audio_level()
                self.display_stats['current_audio_level'] = current_level
                
                # Add to history
                self.audio_levels.append({
                    'timestamp': datetime.now(),
                    'level': current_level
                })
                
                # Maintain history limit
                if len(self.audio_levels) > self.max_history:
                    self.audio_levels.pop(0)
                    
        except Exception as e:
            self.logger.error(f"Error updating audio level: {e}")
    
    def _update_detection_stats(self):
        """Update detection statistics"""
        try:
            now = datetime.now()
            minute_ago = now - timedelta(minutes=1)
            
            # Count detections in last minute
            recent_detections = 0
            if hasattr(self.smartclip, 'stats'):
                # This would need to be implemented based on actual detection tracking
                recent_detections = 0  # Placeholder
            
            self.display_stats['detections_last_minute'] = recent_detections
            
            # Update clips created
            if hasattr(self.smartclip, 'stats'):
                self.display_stats['clips_created_session'] = self.smartclip.stats.get('clips_created', 0)
                
        except Exception as e:
            self.logger.error(f"Error updating detection stats: {e}")
    
    def _update_confidence_history(self):
        """Update confidence history for visualization"""
        try:
            # Get recent detection results from components
            current_confidence = 0.0
            
            # Check emotion detector
            if (self.smartclip.emotion_detector and 
                hasattr(self.smartclip.emotion_detector, 'detection_history') and
                self.smartclip.emotion_detector.detection_history):
                latest_emotion = self.smartclip.emotion_detector.detection_history[-1]
                current_confidence = max(current_confidence, latest_emotion.confidence)
            
            # Check OpenSMILE detector
            if (self.smartclip.opensmile_detector and 
                hasattr(self.smartclip.opensmile_detector, 'last_detection_time') and
                self.smartclip.opensmile_detector.last_detection_time):
                # Add OpenSMILE confidence if recent
                time_diff = datetime.now() - self.smartclip.opensmile_detector.last_detection_time
                if time_diff.total_seconds() < 5:  # Within last 5 seconds
                    current_confidence = max(current_confidence, 0.7)  # Placeholder
            
            # Check Vosk detector
            if (self.smartclip.vosk_detector and 
                hasattr(self.smartclip.vosk_detector, 'recent_detections')):
                recent_vosk = self.smartclip.vosk_detector.get_recent_detections()
                if recent_vosk:
                    latest_vosk = recent_vosk[-1]
                    vosk_time = datetime.fromisoformat(latest_vosk['timestamp'])
                    if (datetime.now() - vosk_time).total_seconds() < 5:
                        current_confidence = max(current_confidence, latest_vosk['confidence'])
            
            # Add to confidence history
            self.confidence_history.append({
                'timestamp': datetime.now(),
                'confidence': current_confidence
            })
            
            # Maintain history limit
            if len(self.confidence_history) > self.max_history:
                self.confidence_history.pop(0)
                
        except Exception as e:
            self.logger.error(f"Error updating confidence history: {e}")
    
    def _cleanup_old_data(self):
        """Clean up old visualization data"""
        try:
            cutoff_time = datetime.now() - timedelta(minutes=5)
            
            # Clean audio levels
            self.audio_levels = [level for level in self.audio_levels 
                               if level['timestamp'] >= cutoff_time]
            
            # Clean confidence history
            self.confidence_history = [conf for conf in self.confidence_history 
                                     if conf['timestamp'] >= cutoff_time]
            
            # Clean detection history
            self.detection_history = [det for det in self.detection_history 
                                    if det['timestamp'] >= cutoff_time]
                                    
        except Exception as e:
            self.logger.error(f"Error cleaning old data: {e}")
    
    def add_detection_event(self, detection_type: str, trigger: str, confidence: float):
        """Add a detection event to the visualization"""
        try:
            event = {
                'timestamp': datetime.now(),
                'type': detection_type,
                'trigger': trigger,
                'confidence': confidence
            }
            
            self.detection_history.append(event)
            self.display_stats['last_detection'] = event
            
            # Maintain history limit
            if len(self.detection_history) > self.max_history:
                self.detection_history.pop(0)
                
        except Exception as e:
            self.logger.error(f"Error adding detection event: {e}")
    
    def get_visualization_data(self) -> Dict[str, Any]:
        """Get current visualization data"""
        try:
            return {
                'audio_levels': self.audio_levels[-20:],  # Last 20 samples
                'confidence_history': self.confidence_history[-20:],
                'recent_detections': self.detection_history[-10:],
                'current_stats': self.display_stats.copy(),
                'is_active': self.visualization_active
            }
            
        except Exception as e:
            self.logger.error(f"Error getting visualization data: {e}")
            return {}
    
    def get_status_summary(self) -> str:
        """Get a text summary of current status"""
        try:
            status_parts = []
            
            # Running status
            if self.smartclip.running:
                status_parts.append("🟢 RUNNING")
            else:
                status_parts.append("🔴 STOPPED")
            
            # Audio level
            audio_level = self.display_stats['current_audio_level']
            if audio_level > 0.1:
                status_parts.append(f"🔊 Audio: {audio_level:.1%}")
            else:
                status_parts.append("🔇 No Audio")
            
            # Last detection
            last_detection = self.display_stats['last_detection']
            if last_detection:
                time_since = datetime.now() - last_detection['timestamp']
                if time_since.total_seconds() < 60:
                    status_parts.append(f"🎯 Last: {last_detection['trigger']} ({time_since.seconds}s ago)")
            
            # Session stats
            clips_created = self.display_stats['clips_created_session']
            session_time = datetime.now() - self.display_stats['session_start_time']
            status_parts.append(f"📊 {clips_created} clips in {session_time.seconds//60}min")
            
            return " | ".join(status_parts)
            
        except Exception as e:
            self.logger.error(f"Error getting status summary: {e}")
            return "❌ Status Error"
    
    def get_component_status(self) -> Dict[str, str]:
        """Get status of all components"""
        try:
            status = {}
            
            # Audio Handler
            if self.smartclip.audio_handler:
                status['audio_handler'] = "🟢 Active" if self.smartclip.audio_handler.capturing else "🔴 Inactive"
            else:
                status['audio_handler'] = "❌ Not Initialized"
            
            # Emotion Detector
            if self.smartclip.emotion_detector:
                status['emotion_detector'] = "🟢 Ready"
            else:
                status['emotion_detector'] = "❌ Not Available"
            
            # OpenSMILE Detector
            if self.smartclip.opensmile_detector:
                if self.smartclip.opensmile_detector.is_available:
                    status['opensmile_detector'] = "🟢 Available" if self.smartclip.opensmile_detector.running else "🟡 Ready"
                else:
                    status['opensmile_detector'] = "🔴 Not Available"
            else:
                status['opensmile_detector'] = "❌ Disabled"
            
            # Vosk Detector
            if self.smartclip.vosk_detector:
                if self.smartclip.vosk_detector.is_available:
                    status['vosk_detector'] = "🟢 Available" if self.smartclip.vosk_detector.running else "🟡 Ready"
                else:
                    status['vosk_detector'] = "🔴 Not Available"
            else:
                status['vosk_detector'] = "❌ Disabled"
            
            # Twitch API
            if self.smartclip.twitch_api:
                if self.smartclip.twitch_api.is_configured:
                    status['twitch_api'] = "🟢 Configured"
                else:
                    status['twitch_api'] = "🟡 Not Configured"
            else:
                status['twitch_api'] = "❌ Not Available"
            
            # Quality Scorer
            if self.smartclip.quality_scorer:
                status['quality_scorer'] = "🟢 Active"
            else:
                status['quality_scorer'] = "❌ Disabled"
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting component status: {e}")
            return {}
    
    def format_detection_history_for_display(self, count: int = 5) -> List[str]:
        """Format recent detection history for display"""
        try:
            recent_detections = self.detection_history[-count:] if count > 0 else self.detection_history
            formatted = []
            
            for detection in reversed(recent_detections):
                timestamp = detection['timestamp'].strftime('%H:%M:%S')
                detection_type = detection['type']
                trigger = detection['trigger']
                confidence = detection['confidence']
                
                # Add emoji based on detection type
                emoji = {
                    'emotion': '🎭',
                    'opensmile': '🤖',
                    'vosk': '🗣️'
                }.get(detection_type, '🎯')
                
                formatted.append(f"{emoji} {timestamp} - {trigger} ({confidence:.1%})")
            
            return formatted
            
        except Exception as e:
            self.logger.error(f"Error formatting detection history: {e}")
            return []
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get performance metrics for display"""
        try:
            metrics = {}
            
            # Audio processing metrics
            if self.audio_levels:
                recent_levels = [level['level'] for level in self.audio_levels[-10:]]
                metrics['avg_audio_level'] = sum(recent_levels) / len(recent_levels)
                metrics['peak_audio_level'] = max(recent_levels)
            
            # Detection frequency
            if self.detection_history:
                recent_detections = [d for d in self.detection_history 
                                   if (datetime.now() - d['timestamp']).total_seconds() < 300]  # Last 5 minutes
                metrics['detections_per_minute'] = len(recent_detections) / 5
            
            # Confidence metrics
            if self.confidence_history:
                recent_confidences = [c['confidence'] for c in self.confidence_history[-20:] if c['confidence'] > 0]
                if recent_confidences:
                    metrics['avg_confidence'] = sum(recent_confidences) / len(recent_confidences)
                    metrics['peak_confidence'] = max(recent_confidences)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {e}")
            return {}
