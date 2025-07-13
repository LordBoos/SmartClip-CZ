"""
Quality Scorer for SmartClip CZ
Smart clip quality scoring to reduce false positives and improve clip relevance
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class QualityScore:
    """Represents a quality score for a detection"""
    overall_score: float
    confidence_score: float
    timing_score: float
    frequency_score: float
    context_score: float
    should_create_clip: bool
    reasons: List[str]

class QualityScorer:
    """Evaluates detection quality to determine if clips should be created"""
    
    def __init__(self, min_confidence: float = 0.6, min_time_between_clips: int = 30, 
                 max_clips_per_hour: int = 12):
        self.min_confidence = min_confidence
        self.min_time_between_clips = min_time_between_clips
        self.max_clips_per_hour = max_clips_per_hour
        
        # Tracking
        self.recent_clips = []
        self.recent_detections = []
        self.max_history = 100
        
        # Scoring weights
        self.weights = {
            'confidence': 0.3,
            'timing': 0.25,
            'frequency': 0.25,
            'context': 0.2
        }
        
        # Quality thresholds
        self.quality_threshold = 0.7
        
        self.logger = logging.getLogger('SmartClipCZ.QualityScorer')
        self.logger.info("Quality scorer initialized")
    
    def score_detection(self, detection_result, detection_type: str) -> QualityScore:
        """Score a detection for clip creation quality"""
        try:
            # Extract detection info - handle both dict and object types
            if hasattr(detection_result, 'confidence'):
                confidence = detection_result.confidence
            elif isinstance(detection_result, dict):
                confidence = detection_result.get('confidence', 0.0)
            else:
                confidence = 0.0

            if hasattr(detection_result, 'emotion_type'):
                emotion_or_phrase = detection_result.emotion_type.value
            elif hasattr(detection_result, 'matched_phrase'):
                emotion_or_phrase = detection_result.matched_phrase
            elif isinstance(detection_result, dict):
                emotion_or_phrase = detection_result.get('emotion', detection_result.get('matched_phrase', 'unknown'))
            else:
                emotion_or_phrase = 'unknown'
            
            # Calculate individual scores
            confidence_score = self._score_confidence(confidence, detection_type)
            timing_score = self._score_timing()
            frequency_score = self._score_frequency(emotion_or_phrase)
            context_score = self._score_context(detection_result, detection_type)
            
            # Calculate overall score
            overall_score = (
                confidence_score * self.weights['confidence'] +
                timing_score * self.weights['timing'] +
                frequency_score * self.weights['frequency'] +
                context_score * self.weights['context']
            )
            
            # Determine if clip should be created
            should_create_clip = self._should_create_clip(overall_score, confidence, emotion_or_phrase)
            
            # Generate reasons
            reasons = self._generate_reasons(confidence_score, timing_score, frequency_score, 
                                           context_score, should_create_clip)
            
            quality_score = QualityScore(
                overall_score=overall_score,
                confidence_score=confidence_score,
                timing_score=timing_score,
                frequency_score=frequency_score,
                context_score=context_score,
                should_create_clip=should_create_clip,
                reasons=reasons
            )
            
            # Add to detection history
            self._add_to_detection_history(detection_result, quality_score)
            
            return quality_score
            
        except Exception as e:
            self.logger.error(f"Error scoring detection: {e}")
            return QualityScore(0.0, 0.0, 0.0, 0.0, 0.0, False, ["Error in scoring"])
    
    def _score_confidence(self, confidence: float, detection_type: str) -> float:
        """Score based on detection confidence"""
        try:
            # Base confidence score
            base_score = min(1.0, confidence / self.min_confidence)
            
            # Adjust based on detection type reliability
            type_multipliers = {
                'emotion': 1.0,
                'opensmile': 1.1,  # OpenSMILE is generally more reliable
                'vosk': 0.9        # Speech recognition can be less reliable
            }
            
            multiplier = type_multipliers.get(detection_type, 1.0)
            adjusted_score = min(1.0, base_score * multiplier)
            
            return adjusted_score
            
        except Exception as e:
            self.logger.error(f"Error scoring confidence: {e}")
            return 0.0
    
    def _score_timing(self) -> float:
        """Score based on timing since last clip"""
        try:
            if not self.recent_clips:
                return 1.0  # No recent clips, timing is perfect
            
            # Get time since last clip
            last_clip_time = self.recent_clips[-1]['timestamp']
            time_since_last = (datetime.now() - last_clip_time).total_seconds()
            
            # Score based on time elapsed
            if time_since_last >= self.min_time_between_clips * 2:
                return 1.0  # Plenty of time has passed
            elif time_since_last >= self.min_time_between_clips:
                return 0.8  # Minimum time has passed
            elif time_since_last >= self.min_time_between_clips * 0.5:
                return 0.4  # Half the minimum time
            else:
                return 0.1  # Too soon
                
        except Exception as e:
            self.logger.error(f"Error scoring timing: {e}")
            return 0.5
    
    def _score_frequency(self, emotion_or_phrase: str) -> float:
        """Score based on recent frequency of this trigger"""
        try:
            # Count recent occurrences of this trigger
            cutoff_time = datetime.now() - timedelta(hours=1)
            recent_count = sum(1 for detection in self.recent_detections 
                             if detection['timestamp'] >= cutoff_time and 
                             detection['trigger'] == emotion_or_phrase)
            
            # Score based on frequency (less frequent = higher score)
            if recent_count == 0:
                return 1.0
            elif recent_count == 1:
                return 0.9
            elif recent_count <= 3:
                return 0.7
            elif recent_count <= 5:
                return 0.4
            else:
                return 0.1  # Too frequent
                
        except Exception as e:
            self.logger.error(f"Error scoring frequency: {e}")
            return 0.5
    
    def _score_context(self, detection_result: Dict, detection_type: str) -> float:
        """Score based on detection context and features"""
        try:
            context_score = 0.5  # Base score
            
            # Check for multiple detection types agreeing
            recent_detections_same_time = [
                d for d in self.recent_detections 
                if (datetime.now() - d['timestamp']).total_seconds() < 5
            ]
            
            if len(recent_detections_same_time) > 1:
                context_score += 0.3  # Multiple detectors agree
            
            # Check audio features if available
            if hasattr(detection_result, 'features'):
                features = detection_result.features or {}
            elif isinstance(detection_result, dict):
                features = detection_result.get('features', {})
            else:
                features = {}
            if features:
                # High energy suggests more interesting content
                energy = features.get('rms_energy', 0)
                if energy > 0.2:
                    context_score += 0.2
                
                # Good spectral characteristics
                spectral_centroid = features.get('spectral_centroid', 0)
                if 500 < spectral_centroid < 3000:  # Good speech/emotion range
                    context_score += 0.1
            
            # Emotion-specific context
            if detection_type == 'emotion':
                if hasattr(detection_result, 'emotion_type'):
                    emotion = detection_result.emotion_type.value
                elif isinstance(detection_result, dict):
                    emotion = detection_result.get('emotion', '')
                else:
                    emotion = ''
                high_value_emotions = ['laughter', 'excitement', 'surprise']
                if emotion in high_value_emotions:
                    context_score += 0.2
            
            return min(1.0, context_score)
            
        except Exception as e:
            self.logger.error(f"Error scoring context: {e}")
            return 0.5
    
    def _should_create_clip(self, overall_score: float, confidence: float, trigger: str) -> bool:
        """Determine if a clip should be created based on all factors"""
        try:
            # Basic quality threshold
            if overall_score < self.quality_threshold:
                return False
            
            # Minimum confidence threshold
            if confidence < self.min_confidence:
                return False
            
            # Check rate limiting
            if not self._check_rate_limits():
                return False
            
            # Special cases for high-value triggers
            high_value_triggers = ['laughter', 'excitement', 'to je skvělé', 'wow', 'úžasné']
            if trigger in high_value_triggers and confidence > 0.8:
                return True  # Always create for high-confidence high-value triggers
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error determining clip creation: {e}")
            return False
    
    def _check_rate_limits(self) -> bool:
        """Check if rate limits allow clip creation"""
        try:
            now = datetime.now()
            
            # Check clips in last hour
            hour_ago = now - timedelta(hours=1)
            clips_last_hour = sum(1 for clip in self.recent_clips 
                                if clip['timestamp'] >= hour_ago)
            
            if clips_last_hour >= self.max_clips_per_hour:
                return False
            
            # Check minimum time between clips
            if self.recent_clips:
                last_clip_time = self.recent_clips[-1]['timestamp']
                time_since_last = (now - last_clip_time).total_seconds()
                
                if time_since_last < self.min_time_between_clips:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking rate limits: {e}")
            return False
    
    def _generate_reasons(self, confidence_score: float, timing_score: float, 
                         frequency_score: float, context_score: float, 
                         should_create_clip: bool) -> List[str]:
        """Generate human-readable reasons for the scoring decision"""
        reasons = []
        
        try:
            # Confidence reasons
            if confidence_score >= 0.8:
                reasons.append("High confidence detection")
            elif confidence_score < 0.5:
                reasons.append("Low confidence detection")
            
            # Timing reasons
            if timing_score >= 0.8:
                reasons.append("Good timing since last clip")
            elif timing_score < 0.5:
                reasons.append("Too soon since last clip")
            
            # Frequency reasons
            if frequency_score >= 0.8:
                reasons.append("Rare trigger, high value")
            elif frequency_score < 0.5:
                reasons.append("Frequent trigger, lower value")
            
            # Context reasons
            if context_score >= 0.8:
                reasons.append("Strong contextual indicators")
            elif context_score < 0.5:
                reasons.append("Weak contextual support")
            
            # Overall decision
            if should_create_clip:
                reasons.append("✅ Clip creation approved")
            else:
                reasons.append("❌ Clip creation rejected")
            
        except Exception as e:
            self.logger.error(f"Error generating reasons: {e}")
            reasons.append("Error in reason generation")
        
        return reasons
    
    def record_clip_decision(self, quality_score: QualityScore, clip_created: bool):
        """Record the outcome of a clip decision"""
        try:
            clip_record = {
                'timestamp': datetime.now(),
                'quality_score': quality_score.overall_score,
                'should_create': quality_score.should_create_clip,
                'actually_created': clip_created,
                'reasons': quality_score.reasons
            }
            
            self.recent_clips.append(clip_record)
            
            # Maintain history limit
            if len(self.recent_clips) > self.max_history:
                self.recent_clips.pop(0)
                
        except Exception as e:
            self.logger.error(f"Error recording clip decision: {e}")
    
    def _add_to_detection_history(self, detection_result, quality_score: QualityScore):
        """Add detection to history for context analysis"""
        try:
            # Handle both object and dict types
            if hasattr(detection_result, 'emotion_type'):
                trigger = detection_result.emotion_type.value
            elif hasattr(detection_result, 'matched_phrase'):
                trigger = detection_result.matched_phrase
            elif isinstance(detection_result, dict):
                trigger = detection_result.get('emotion', detection_result.get('matched_phrase', 'unknown'))
            else:
                trigger = 'unknown'

            if hasattr(detection_result, 'confidence'):
                confidence = detection_result.confidence
            elif isinstance(detection_result, dict):
                confidence = detection_result.get('confidence', 0)
            else:
                confidence = 0

            if hasattr(detection_result, 'type'):
                result_type = detection_result.type
            else:
                result_type = detection_result.get('type', 'unknown') if isinstance(detection_result, dict) else 'unknown'

            detection_record = {
                'timestamp': datetime.now(),
                'trigger': trigger,
                'confidence': confidence,
                'type': result_type,
                'quality_score': quality_score.overall_score
            }
            
            self.recent_detections.append(detection_record)
            
            # Maintain history limit
            if len(self.recent_detections) > self.max_history:
                self.recent_detections.pop(0)
                
        except Exception as e:
            self.logger.error(f"Error adding to detection history: {e}")
    
    def get_statistics(self) -> Dict:
        """Get quality scorer statistics"""
        try:
            if not self.recent_clips:
                return {
                    'total_decisions': 0,
                    'clips_approved': 0,
                    'clips_rejected': 0,
                    'approval_rate': 0.0,
                    'average_quality_score': 0.0
                }
            
            total_decisions = len(self.recent_clips)
            clips_approved = sum(1 for clip in self.recent_clips if clip['should_create'])
            clips_rejected = total_decisions - clips_approved
            approval_rate = clips_approved / total_decisions if total_decisions > 0 else 0
            
            quality_scores = [clip['quality_score'] for clip in self.recent_clips]
            average_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
            
            return {
                'total_decisions': total_decisions,
                'clips_approved': clips_approved,
                'clips_rejected': clips_rejected,
                'approval_rate': approval_rate,
                'average_quality_score': average_quality_score,
                'recent_clips_count': len([c for c in self.recent_clips 
                                         if (datetime.now() - c['timestamp']).total_seconds() < 3600])
            }
            
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {}
    
    def update_settings(self, min_confidence: float = None, min_time_between_clips: int = None,
                       max_clips_per_hour: int = None, quality_threshold: float = None):
        """Update quality scorer settings"""
        try:
            if min_confidence is not None:
                self.min_confidence = max(0.1, min(1.0, min_confidence))
            
            if min_time_between_clips is not None:
                self.min_time_between_clips = max(5, min_time_between_clips)
            
            if max_clips_per_hour is not None:
                self.max_clips_per_hour = max(1, min(60, max_clips_per_hour))
            
            if quality_threshold is not None:
                self.quality_threshold = max(0.1, min(1.0, quality_threshold))
            
            self.logger.info("Quality scorer settings updated")
            
        except Exception as e:
            self.logger.error(f"Error updating settings: {e}")
