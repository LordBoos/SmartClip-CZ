"""
Clip Manager for SmartClip CZ
Manages clip creation attempts, success tracking, and analytics
"""

import json
import logging
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

@dataclass
class ClipAttempt:
    """Represents a clip creation attempt"""
    timestamp: datetime
    detection_type: str  # 'emotion', 'opensmile', 'vosk'
    trigger_value: str   # emotion name or phrase
    confidence: float
    audio_source: str
    clip_title: str
    clip_id: Optional[str] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ClipAttempt':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

class ClipManager:
    """Manages clip creation and tracking"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.clip_attempts: List[ClipAttempt] = []
        
        # Statistics
        self.total_attempts = 0
        self.successful_clips = 0
        self.failed_clips = 0
        
        # Performance tracking
        self.detection_type_stats = {}
        self.trigger_value_stats = {}
        self.hourly_stats = {}
        
        self.logger = logging.getLogger('SmartClipCZ.ClipManager')
        
        # Load existing data
        self.data_file = os.path.join(os.path.dirname(__file__), 'clip_history.json')
        self._load_history()
    
    def record_clip_attempt(self, detection_type: str, trigger_value: str, confidence: float,
                          audio_source: str, clip_title: str) -> str:
        """Record a new clip creation attempt"""
        try:
            attempt = ClipAttempt(
                timestamp=datetime.now(),
                detection_type=detection_type,
                trigger_value=trigger_value,
                confidence=confidence,
                audio_source=audio_source,
                clip_title=clip_title
            )
            
            self.clip_attempts.append(attempt)
            self.total_attempts += 1
            
            # Update statistics
            self._update_detection_type_stats(detection_type)
            self._update_trigger_value_stats(trigger_value)
            self._update_hourly_stats()
            
            # Maintain history limit
            if len(self.clip_attempts) > self.max_history:
                self.clip_attempts.pop(0)
            
            # Save to file
            self._save_history()
            
            # Return attempt ID (index in list)
            attempt_id = str(len(self.clip_attempts) - 1)
            self.logger.info(f"Recorded clip attempt: {detection_type} - {trigger_value} ({confidence:.2f})")
            
            return attempt_id
            
        except Exception as e:
            self.logger.error(f"Error recording clip attempt: {e}")
            return ""
    
    def update_clip_result(self, clip_id: str, success: bool, error_message: str = ""):
        """Update the result of a clip creation attempt"""
        try:
            # Find the most recent attempt (assuming it's the one being updated)
            if self.clip_attempts:
                latest_attempt = self.clip_attempts[-1]
                latest_attempt.clip_id = clip_id if success else None
                latest_attempt.success = success
                latest_attempt.error_message = error_message if not success else None
                
                # Update statistics
                if success:
                    self.successful_clips += 1
                else:
                    self.failed_clips += 1
                
                # Save to file
                self._save_history()
                
                result_text = "successful" if success else "failed"
                self.logger.info(f"Updated clip result: {result_text} - {clip_id or error_message}")
            
        except Exception as e:
            self.logger.error(f"Error updating clip result: {e}")
    
    def get_recent_attempts(self, count: int = 10) -> List[Dict]:
        """Get recent clip attempts"""
        try:
            recent = self.clip_attempts[-count:] if count > 0 else self.clip_attempts
            return [attempt.to_dict() for attempt in reversed(recent)]
        except Exception as e:
            self.logger.error(f"Error getting recent attempts: {e}")
            return []
    
    def get_success_rate(self, time_window: Optional[timedelta] = None) -> float:
        """Get clip creation success rate"""
        try:
            if time_window:
                cutoff_time = datetime.now() - time_window
                relevant_attempts = [a for a in self.clip_attempts 
                                   if a.timestamp >= cutoff_time and a.success is not None]
            else:
                relevant_attempts = [a for a in self.clip_attempts if a.success is not None]
            
            if not relevant_attempts:
                return 0.0
            
            successful = sum(1 for a in relevant_attempts if a.success)
            return successful / len(relevant_attempts)
            
        except Exception as e:
            self.logger.error(f"Error calculating success rate: {e}")
            return 0.0
    
    def get_detection_type_performance(self) -> Dict[str, Dict]:
        """Get performance statistics by detection type"""
        try:
            performance = {}
            
            for detection_type in self.detection_type_stats:
                type_attempts = [a for a in self.clip_attempts 
                               if a.detection_type == detection_type and a.success is not None]
                
                if type_attempts:
                    successful = sum(1 for a in type_attempts if a.success)
                    total = len(type_attempts)
                    avg_confidence = sum(a.confidence for a in type_attempts) / total
                    
                    performance[detection_type] = {
                        'total_attempts': total,
                        'successful': successful,
                        'success_rate': successful / total,
                        'average_confidence': avg_confidence
                    }
            
            return performance
            
        except Exception as e:
            self.logger.error(f"Error getting detection type performance: {e}")
            return {}
    
    def get_trigger_value_performance(self) -> Dict[str, Dict]:
        """Get performance statistics by trigger value (emotion/phrase)"""
        try:
            performance = {}
            
            for trigger_value in self.trigger_value_stats:
                trigger_attempts = [a for a in self.clip_attempts 
                                  if a.trigger_value == trigger_value and a.success is not None]
                
                if trigger_attempts:
                    successful = sum(1 for a in trigger_attempts if a.success)
                    total = len(trigger_attempts)
                    avg_confidence = sum(a.confidence for a in trigger_attempts) / total
                    
                    performance[trigger_value] = {
                        'total_attempts': total,
                        'successful': successful,
                        'success_rate': successful / total,
                        'average_confidence': avg_confidence,
                        'last_triggered': max(a.timestamp for a in trigger_attempts).isoformat()
                    }
            
            return performance
            
        except Exception as e:
            self.logger.error(f"Error getting trigger value performance: {e}")
            return {}
    
    def get_hourly_statistics(self, hours: int = 24) -> Dict[str, int]:
        """Get hourly clip creation statistics"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_attempts = [a for a in self.clip_attempts if a.timestamp >= cutoff_time]
            
            hourly_counts = {}
            for attempt in recent_attempts:
                hour_key = attempt.timestamp.strftime('%Y-%m-%d %H:00')
                hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1
            
            return hourly_counts
            
        except Exception as e:
            self.logger.error(f"Error getting hourly statistics: {e}")
            return {}
    
    def get_best_performing_triggers(self, limit: int = 5) -> List[Dict]:
        """Get best performing trigger values"""
        try:
            trigger_performance = self.get_trigger_value_performance()
            
            # Sort by success rate, then by total attempts
            sorted_triggers = sorted(
                trigger_performance.items(),
                key=lambda x: (x[1]['success_rate'], x[1]['total_attempts']),
                reverse=True
            )
            
            return [
                {
                    'trigger_value': trigger,
                    **stats
                }
                for trigger, stats in sorted_triggers[:limit]
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting best performing triggers: {e}")
            return []
    
    def get_statistics_summary(self) -> Dict:
        """Get comprehensive statistics summary"""
        try:
            now = datetime.now()
            
            # Time-based success rates
            last_hour_rate = self.get_success_rate(timedelta(hours=1))
            last_day_rate = self.get_success_rate(timedelta(days=1))
            overall_rate = self.get_success_rate()
            
            # Recent activity
            recent_attempts = len([a for a in self.clip_attempts 
                                 if a.timestamp >= now - timedelta(hours=1)])
            
            return {
                'total_attempts': self.total_attempts,
                'successful_clips': self.successful_clips,
                'failed_clips': self.failed_clips,
                'overall_success_rate': overall_rate,
                'last_hour_success_rate': last_hour_rate,
                'last_day_success_rate': last_day_rate,
                'recent_attempts_last_hour': recent_attempts,
                'detection_type_performance': self.get_detection_type_performance(),
                'best_triggers': self.get_best_performing_triggers(3),
                'hourly_stats': self.get_hourly_statistics(12)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting statistics summary: {e}")
            return {}
    
    def _update_detection_type_stats(self, detection_type: str):
        """Update detection type statistics"""
        self.detection_type_stats[detection_type] = self.detection_type_stats.get(detection_type, 0) + 1
    
    def _update_trigger_value_stats(self, trigger_value: str):
        """Update trigger value statistics"""
        self.trigger_value_stats[trigger_value] = self.trigger_value_stats.get(trigger_value, 0) + 1
    
    def _update_hourly_stats(self):
        """Update hourly statistics"""
        hour_key = datetime.now().strftime('%Y-%m-%d %H')
        self.hourly_stats[hour_key] = self.hourly_stats.get(hour_key, 0) + 1
    
    def _save_history(self):
        """Save clip history to file"""
        try:
            data = {
                'clip_attempts': [attempt.to_dict() for attempt in self.clip_attempts],
                'statistics': {
                    'total_attempts': self.total_attempts,
                    'successful_clips': self.successful_clips,
                    'failed_clips': self.failed_clips,
                    'detection_type_stats': self.detection_type_stats,
                    'trigger_value_stats': self.trigger_value_stats,
                    'hourly_stats': self.hourly_stats
                }
            }
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"Error saving clip history: {e}")
    
    def _load_history(self):
        """Load clip history from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Load clip attempts
                if 'clip_attempts' in data:
                    self.clip_attempts = [ClipAttempt.from_dict(attempt_data) 
                                        for attempt_data in data['clip_attempts']]
                
                # Load statistics
                if 'statistics' in data:
                    stats = data['statistics']
                    self.total_attempts = stats.get('total_attempts', 0)
                    self.successful_clips = stats.get('successful_clips', 0)
                    self.failed_clips = stats.get('failed_clips', 0)
                    self.detection_type_stats = stats.get('detection_type_stats', {})
                    self.trigger_value_stats = stats.get('trigger_value_stats', {})
                    self.hourly_stats = stats.get('hourly_stats', {})
                
                self.logger.info(f"Loaded {len(self.clip_attempts)} clip attempts from history")
            else:
                self.logger.info("No existing clip history found, starting fresh")
                
        except Exception as e:
            self.logger.error(f"Error loading clip history: {e}")
    
    def clear_history(self):
        """Clear all clip history"""
        try:
            self.clip_attempts.clear()
            self.total_attempts = 0
            self.successful_clips = 0
            self.failed_clips = 0
            self.detection_type_stats.clear()
            self.trigger_value_stats.clear()
            self.hourly_stats.clear()
            
            # Remove history file
            if os.path.exists(self.data_file):
                os.remove(self.data_file)
            
            self.logger.info("Clip history cleared")
            
        except Exception as e:
            self.logger.error(f"Error clearing clip history: {e}")
