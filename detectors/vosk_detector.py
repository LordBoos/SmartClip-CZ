"""
Vosk Speech Recognition Detector for SmartClip CZ
Czech speech recognition with activation phrase detection

Author: Jakub Kolář (LordBoos)
Email: lordboos@gmail.com
"""

import os
import json
import logging
import threading
import time
import queue
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
import numpy as np

try:
    import vosk
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    vosk = None

class VoskDetector:
    """Multi-language speech recognition using Vosk for activation phrase detection"""

    def __init__(self, model_path: str = None, activation_phrases: List[str] = None,
                 confidence_threshold: float = 0.7, czech_model_path: str = None,
                 english_model_path: str = None, czech_phrases: List[str] = None,
                 english_phrases: List[str] = None):
        # Backward compatibility - if old parameters are used, treat as Czech
        if model_path and activation_phrases:
            self.czech_model_path = model_path
            self.czech_phrases = [phrase.lower() for phrase in activation_phrases]
            self.english_model_path = None
            self.english_phrases = []
        else:
            # New multi-language setup
            self.czech_model_path = czech_model_path
            self.english_model_path = english_model_path
            self.czech_phrases = [phrase.lower() for phrase in (czech_phrases or [])]
            self.english_phrases = [phrase.lower() for phrase in (english_phrases or [])]

        self.all_phrases = self.czech_phrases + self.english_phrases
        self.confidence_threshold = confidence_threshold
        self.running = False

        # Vosk components
        self.czech_model = None
        self.english_model = None
        self.czech_recognizer = None
        self.english_recognizer = None
        
        # Audio processing
        self.sample_rate = 16000
        self.audio_queue = queue.Queue(maxsize=50)
        self.result_queue = queue.Queue(maxsize=10)  # Queue for returning results
        self.detection_thread = None
        
        # Phrase matching
        self.phrase_variations = self._generate_phrase_variations()
        self.partial_matches = {}

        # Statistics
        self.recognition_count = 0
        self.phrase_matches = {}
        self.last_recognition_time = None

        # Deduplication for preventing spam
        self.last_phrase_detections = {}  # phrase -> timestamp
        self.phrase_cooldown = timedelta(seconds=3)  # 3 second cooldown per phrase

        self.logger = logging.getLogger('SmartClipCZ.Vosk')

        # Initialize Vosk models
        self.czech_available = False
        self.english_available = False

        if self.czech_model_path and self.czech_phrases:
            self.czech_available = self._initialize_czech_model()

        if self.english_model_path and self.english_phrases:
            self.english_available = self._initialize_english_model()

        self.is_available = self.czech_available or self.english_available

        if self.is_available:
            total_phrases = len(self.czech_phrases) + len(self.english_phrases)
            self.logger.info(f"Vosk detector initialized with {total_phrases} phrases "
                           f"(Czech: {len(self.czech_phrases)}, English: {len(self.english_phrases)})")
        else:
            self.logger.warning("Vosk detector not available")
    
    def _initialize_czech_model(self) -> bool:
        """Initialize Czech Vosk model and recognizer"""
        try:
            if not VOSK_AVAILABLE:
                self.logger.warning("Vosk library not available - install with: pip install vosk")
                return False

            # Check if model exists
            if not os.path.exists(self.czech_model_path):
                self.logger.warning(f"Czech Vosk model not found at: {self.czech_model_path}")
                return False

            # Set Vosk log level
            vosk.SetLogLevel(-1)  # Suppress Vosk logs

            # Load Czech model
            self.czech_model = vosk.Model(self.czech_model_path)
            self.logger.info(f"Czech Vosk model loaded from: {self.czech_model_path}")

            # Create Czech recognizer
            self.czech_recognizer = vosk.KaldiRecognizer(self.czech_model, self.sample_rate)

            # Configure recognizer for better phrase detection (safe methods only)
            self._configure_czech_recognizer()
            self.logger.debug("Czech recognizer initialized and configured")

            return True

        except Exception as e:
            self.logger.error(f"Error initializing Czech Vosk model: {e}")
            return False

    def _initialize_english_model(self) -> bool:
        """Initialize English Vosk model and recognizer"""
        try:
            if not VOSK_AVAILABLE:
                self.logger.warning("Vosk library not available - install with: pip install vosk")
                return False

            # Check if model exists
            if not os.path.exists(self.english_model_path):
                self.logger.warning(f"English Vosk model not found at: {self.english_model_path}")
                return False

            # Load English model
            self.english_model = vosk.Model(self.english_model_path)
            self.logger.info(f"English Vosk model loaded from: {self.english_model_path}")

            # Create English recognizer
            self.english_recognizer = vosk.KaldiRecognizer(self.english_model, self.sample_rate)

            # Configure recognizer for better phrase detection (safe methods only)
            self._configure_english_recognizer()
            self.logger.debug("English recognizer initialized and configured")

            return True

        except Exception as e:
            self.logger.error(f"Error initializing English Vosk model: {e}")
            return False
    
    def _configure_czech_recognizer(self):
        """Configure Czech Vosk recognizer for optimal phrase detection (safe methods only)"""
        try:
            # Generate phrase variations for better matching (this is safe)
            phrases_for_grammar = []
            for phrase in self.czech_phrases:
                # Add the phrase and common variations
                phrases_for_grammar.append(phrase)
                # Add variations with different punctuation
                phrases_for_grammar.append(phrase.replace(" ", ""))
                phrases_for_grammar.append(phrase.replace(" ", "-"))
                # Add individual words for partial matching
                words = phrase.split()
                phrases_for_grammar.extend(words)

            # Remove duplicates
            phrases_for_grammar = list(set(phrases_for_grammar))

            self.logger.info(f"Czech recognizer configured with {len(phrases_for_grammar)} phrase variations")

        except Exception as e:
            self.logger.error(f"Error configuring Czech Vosk recognizer: {e}")

    def _configure_english_recognizer(self):
        """Configure English Vosk recognizer for optimal phrase detection (safe methods only)"""
        try:
            # Generate phrase variations for better matching (this is safe)
            phrases_for_grammar = []
            for phrase in self.english_phrases:
                # Add the phrase and common variations
                phrases_for_grammar.append(phrase)
                # Add variations with different punctuation
                phrases_for_grammar.append(phrase.replace(" ", ""))
                phrases_for_grammar.append(phrase.replace(" ", "-"))
                # Add individual words for partial matching
                words = phrase.split()
                phrases_for_grammar.extend(words)

            # Remove duplicates
            phrases_for_grammar = list(set(phrases_for_grammar))

            self.logger.info(f"English recognizer configured with {len(phrases_for_grammar)} phrase variations")

        except Exception as e:
            self.logger.error(f"Error configuring English Vosk recognizer: {e}")
    
    def _generate_phrase_variations(self) -> Dict[str, List[str]]:
        """Generate variations of activation phrases for better matching"""
        variations = {}

        try:
            # Process Czech phrases
            for phrase in self.czech_phrases:
                variations[phrase] = self._generate_czech_variations(phrase)

            # Process English phrases
            for phrase in self.english_phrases:
                variations[phrase] = self._generate_english_variations(phrase)

        except Exception as e:
            self.logger.error(f"Error generating phrase variations: {e}")

        return variations

    def _generate_czech_variations(self, phrase: str) -> List[str]:
        """Generate Czech-specific phrase variations"""
        try:
            phrase_variations = [phrase]

            # Common Czech variations and typos
            common_replacements = {
                'ě': ['e', 'ie'],
                'ř': ['r', 'rz'],
                'ž': ['z'],
                'š': ['s'],
                'č': ['c'],
                'ý': ['y', 'i'],
                'í': ['i', 'y'],
                'ú': ['u'],
                'ů': ['u'],
                'á': ['a'],
                'é': ['e'],
                'ó': ['o']
            }

            # Generate variations with character replacements
            for original, replacements in common_replacements.items():
                if original in phrase:
                    for replacement in replacements:
                        variation = phrase.replace(original, replacement)
                        if variation not in phrase_variations:
                            phrase_variations.append(variation)

            # Add variations without diacritics
            import unicodedata
            normalized = unicodedata.normalize('NFD', phrase)
            ascii_phrase = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
            if ascii_phrase not in phrase_variations:
                phrase_variations.append(ascii_phrase)

            return phrase_variations

        except Exception as e:
            self.logger.error(f"Error generating Czech variations for '{phrase}': {e}")
            return [phrase]

    def _generate_english_variations(self, phrase: str) -> List[str]:
        """Generate English-specific phrase variations"""
        try:
            phrase_variations = [phrase]

            # Common English contractions and variations
            contractions = {
                "that's": ["that is", "thats"],
                "what's": ["what is", "whats"],
                "it's": ["it is", "its"],
                "let's": ["let us", "lets"],
                "can't": ["cannot", "cant"],
                "won't": ["will not", "wont"],
                "don't": ["do not", "dont"],
                "isn't": ["is not", "isnt"],
                "aren't": ["are not", "arent"],
                "wasn't": ["was not", "wasnt"],
                "weren't": ["were not", "werent"]
            }

            # Apply contractions
            for contraction, expansions in contractions.items():
                if contraction in phrase:
                    for expansion in expansions:
                        variation = phrase.replace(contraction, expansion)
                        if variation not in phrase_variations:
                            phrase_variations.append(variation)

            # Also check reverse (expansion to contraction)
            for contraction, expansions in contractions.items():
                for expansion in expansions:
                    if expansion in phrase:
                        variation = phrase.replace(expansion, contraction)
                        if variation not in phrase_variations:
                            phrase_variations.append(variation)

            return phrase_variations

        except Exception as e:
            self.logger.error(f"Error generating English variations for '{phrase}': {e}")
            return [phrase]


    def start_detection(self):
        """Start Vosk speech detection"""
        self.logger.info(f"Attempting to start Vosk detection (available: {self.is_available}, running: {self.running})")

        if not self.is_available:
            self.logger.warning(f"Cannot start Vosk detection - not available (Czech: {self.czech_available}, English: {self.english_available})")
            self.logger.warning(f"Czech model path: {self.czech_model_path}, phrases: {len(self.czech_phrases)}")
            self.logger.warning(f"English model path: {self.english_model_path}, phrases: {len(self.english_phrases)}")
            return False

        if self.running:
            self.logger.info("Vosk detection already running")
            return True

        try:
            self.running = True
            self.detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
            self.detection_thread.start()

            self.logger.info(f"Vosk detection started successfully with {len(self.all_phrases)} total phrases")
            return True

        except Exception as e:
            self.logger.error(f"Error starting Vosk detection: {e}")
            self.running = False
            return False
    
    def stop_detection(self):
        """Stop Vosk speech detection"""
        if not self.running:
            return
        
        try:
            self.running = False
            
            # Clear audio queue
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break

            # Clear result queue
            while not self.result_queue.empty():
                try:
                    self.result_queue.get_nowait()
                except queue.Empty:
                    break
            
            if self.detection_thread and self.detection_thread.is_alive():
                self.detection_thread.join(timeout=2)
            
            self.logger.info("Vosk detection stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping Vosk detection: {e}")
    
    def process_audio(self, audio_data: np.ndarray) -> Optional[Dict]:
        """Process audio data for speech recognition"""
        try:
            if not self.is_available:
                self.logger.debug("Vosk process_audio called but not available")
                return None

            if not self.running:
                self.logger.debug("Vosk process_audio called but not running")
                return None

            # Convert to bytes (Vosk expects 16-bit PCM)
            audio_int16 = (audio_data * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()

            # Add to queue for processing
            try:
                self.audio_queue.put(audio_bytes, block=False)
            except queue.Full:
                # Drop audio if queue is full
                pass

            # Check for available results
            try:
                result = self.result_queue.get_nowait()
                return result
            except queue.Empty:
                return None

        except Exception as e:
            self.logger.error(f"Error processing audio: {e}")
            return None
    
    def _detection_loop(self):
        # Configure logging to handle Unicode properly
        import logging
        import sys
        
        # Set up logging handler that can handle Unicode
        if not hasattr(self.logger, '_unicode_handler_added'):
            for handler in self.logger.handlers:
                if hasattr(handler, 'stream') and handler.stream == sys.stderr:
                    # Replace stderr handler with one that handles Unicode
                    handler.stream = sys.stdout
            self.logger._unicode_handler_added = True
        
        """Main speech recognition loop"""
        self.logger.info("Vosk detection loop started")
        
        while self.running:
            try:
                # Get audio data from queue
                try:
                    audio_bytes = self.audio_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # Process with Czech recognizer if available
                if self.czech_available and self.czech_recognizer:
                    if self.czech_recognizer.AcceptWaveform(audio_bytes):
                        # Final result
                        result = json.loads(self.czech_recognizer.Result())
                        self._process_recognition_result(result, is_final=True, language='czech')
                    else:
                        # Partial result
                        result = json.loads(self.czech_recognizer.PartialResult())
                        self._process_recognition_result(result, is_final=False, language='czech')

                # Process with English recognizer if available
                if self.english_available and self.english_recognizer:
                    if self.english_recognizer.AcceptWaveform(audio_bytes):
                        # Final result
                        result = json.loads(self.english_recognizer.Result())
                        self._process_recognition_result(result, is_final=True, language='english')
                    else:
                        # Partial result
                        result = json.loads(self.english_recognizer.PartialResult())
                        self._process_recognition_result(result, is_final=False, language='english')
                
            except Exception as e:
                self.logger.error(f"Error in Vosk detection loop: {e}")
                time.sleep(0.1)
        
        self.logger.info("Vosk detection loop ended")
    
    def _process_recognition_result(self, result: Dict, is_final: bool, language: str = 'czech'):
        """Process Vosk recognition result"""
        try:
            text_key = 'text' if is_final else 'partial'
            recognized_text = result.get(text_key, '').lower().strip()

            if not recognized_text:
                return

            self.recognition_count += 1
            self.last_recognition_time = datetime.now()

            # Check for phrase matches based on language
            if language == 'czech':
                matched_phrases = self._find_matching_phrases(recognized_text, self.czech_phrases)
            elif language == 'english':
                matched_phrases = self._find_matching_phrases(recognized_text, self.english_phrases)
            else:
                matched_phrases = self._find_matching_phrases(recognized_text, self.all_phrases)
            
            if matched_phrases:
                for phrase, confidence in matched_phrases:
                    # Check deduplication cooldown
                    now = datetime.now()
                    last_detection = self.last_phrase_detections.get(phrase)

                    if last_detection and (now - last_detection) < self.phrase_cooldown:
                        # Skip this detection due to cooldown
                        continue

                    # Update last detection time for this phrase
                    self.last_phrase_detections[phrase] = now

                    # Update statistics
                    self.phrase_matches[phrase] = self.phrase_matches.get(phrase, 0) + 1

                    # Create detection result
                    detection_result = {
                        'text': recognized_text,
                        'matched_phrase': phrase,
                        'confidence': confidence,
                        'is_final': is_final,
                        'type': 'vosk',
                        'timestamp': now.isoformat()
                    }

                    # Log the detection
                    self.logger.info(f"Phrase detected: '{recognized_text}' -> '{phrase}' ({confidence:.2f})")

                    # Put result in queue for main detection loop
                    try:
                        self.result_queue.put_nowait(detection_result)
                    except queue.Full:
                        # Drop result if queue is full
                        self.logger.warning("Result queue full, dropping detection result")

                    # Also store it for retrieval (backward compatibility)
                    self._store_detection_result(detection_result)
            
            # Log all recognition for debugging
            if is_final:
                self.logger.debug(f"Vosk recognized: '{recognized_text}'")
                
        except Exception as e:
            self.logger.error(f"Error processing recognition result: {e}")
    
    def _find_matching_phrases(self, recognized_text: str, phrase_list: List[str] = None) -> List[tuple]:
        """Find activation phrases that match the recognized text"""
        matches = []

        try:
            # Use provided phrase list or default to all phrases
            phrases_to_check = phrase_list if phrase_list is not None else self.all_phrases

            for phrase in phrases_to_check:
                confidence = self._calculate_phrase_match_confidence(phrase, recognized_text)

                if confidence >= self.confidence_threshold:
                    matches.append((phrase, confidence))

            # Sort by confidence (highest first)
            matches.sort(key=lambda x: x[1], reverse=True)

        except Exception as e:
            self.logger.error(f"Error finding matching phrases: {e}")

        return matches
    
    def _calculate_phrase_match_confidence(self, phrase: str, recognized_text: str) -> float:
        """Calculate confidence score for phrase match"""
        try:
            # Exact match
            if phrase in recognized_text:
                return 1.0
            
            # Check variations
            if phrase in self.phrase_variations:
                for variation in self.phrase_variations[phrase]:
                    if variation in recognized_text:
                        return 0.9
            
            # Fuzzy matching - check individual words
            phrase_words = phrase.split()
            recognized_words = recognized_text.split()
            
            if not phrase_words:
                return 0.0
            
            # Count matching words
            matching_words = 0
            for phrase_word in phrase_words:
                for recognized_word in recognized_words:
                    if self._words_similar(phrase_word, recognized_word):
                        matching_words += 1
                        break
            
            # Calculate word-based confidence
            word_confidence = matching_words / len(phrase_words)
            
            # Require at least 70% word match for partial confidence
            if word_confidence >= 0.7:
                return word_confidence * 0.8  # Reduce confidence for partial matches
            
            # Check for substring matches
            if any(word in recognized_text for word in phrase_words if len(word) > 3):
                return 0.5
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating phrase match confidence: {e}")
            return 0.0
    
    def _words_similar(self, word1: str, word2: str) -> bool:
        """Check if two words are similar (accounting for Czech language specifics)"""
        try:
            # Exact match
            if word1 == word2:
                return True
            
            # Length difference check
            if abs(len(word1) - len(word2)) > 2:
                return False
            
            # Simple edit distance for short words
            if len(word1) <= 4 or len(word2) <= 4:
                return self._edit_distance(word1, word2) <= 1
            
            # For longer words, allow more differences
            return self._edit_distance(word1, word2) <= 2
            
        except Exception as e:
            self.logger.error(f"Error comparing words: {e}")
            return False
    
    def _edit_distance(self, s1: str, s2: str) -> int:
        """Calculate edit distance between two strings"""
        try:
            if len(s1) < len(s2):
                return self._edit_distance(s2, s1)
            
            if len(s2) == 0:
                return len(s1)
            
            previous_row = list(range(len(s2) + 1))
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row
            
            return previous_row[-1]
            
        except Exception as e:
            self.logger.error(f"Error calculating edit distance: {e}")
            return 999
    
    def _store_detection_result(self, result: Dict):
        """Store detection result (placeholder for callback mechanism)"""
        # In a real implementation, this would trigger a callback or event
        # For now, we'll just store recent results
        if not hasattr(self, 'recent_detections'):
            self.recent_detections = []
        
        self.recent_detections.append(result)
        
        # Keep only recent detections
        if len(self.recent_detections) > 10:
            self.recent_detections.pop(0)
    
    def get_recent_detections(self) -> List[Dict]:
        """Get recent detection results"""
        return getattr(self, 'recent_detections', [])
    
    def get_statistics(self) -> Dict:
        """Get Vosk detector statistics"""
        return {
            'is_available': self.is_available,
            'running': self.running,
            'recognition_count': self.recognition_count,
            'phrase_matches': dict(self.phrase_matches),
            'last_recognition_time': self.last_recognition_time.isoformat() if self.last_recognition_time else None,
            'model_path': self.model_path,
            'activation_phrases': self.activation_phrases,
            'confidence_threshold': self.confidence_threshold
        }
    
    def add_activation_phrase(self, phrase: str):
        """Add new activation phrase"""
        phrase_lower = phrase.lower()
        if phrase_lower not in self.activation_phrases:
            self.activation_phrases.append(phrase_lower)
            self.phrase_variations.update(self._generate_phrase_variations())
            self.logger.info(f"Added activation phrase: {phrase}")
    
    def remove_activation_phrase(self, phrase: str):
        """Remove activation phrase"""
        phrase_lower = phrase.lower()
        if phrase_lower in self.activation_phrases:
            self.activation_phrases.remove(phrase_lower)
            if phrase_lower in self.phrase_variations:
                del self.phrase_variations[phrase_lower]
            self.logger.info(f"Removed activation phrase: {phrase}")
    
    def set_confidence_threshold(self, sensitivity: float, log_change: bool = True):
        """Update sensitivity (converts to internal confidence threshold)"""
        old_sensitivity = 1.0 - (self.confidence_threshold - 0.1) / 0.8  # Convert back to sensitivity for comparison

        # Map sensitivity to confidence threshold (inverted)
        # Higher sensitivity (1.0) -> Lower threshold (0.1) -> More detections
        # Lower sensitivity (0.1) -> Higher threshold (0.9) -> Fewer detections
        mapped_threshold = 0.1 + (1.0 - max(0.1, min(1.0, sensitivity))) * 0.8

        self.confidence_threshold = mapped_threshold

        if log_change and abs(sensitivity - old_sensitivity) > 0.001:
            self.logger.info(f"Vosk sensitivity updated to {sensitivity:.3f} (confidence threshold: {self.confidence_threshold:.3f})")

    def update_activation_phrases(self, czech_phrases: List[str] = None, english_phrases: List[str] = None, log_change: bool = True):
        """Update activation phrases for both languages"""
        try:
            # Store old phrases for comparison
            old_czech_phrases = self.czech_phrases.copy()
            old_english_phrases = self.english_phrases.copy()

            # Update Czech phrases if provided
            if czech_phrases is not None:
                # Normalize Czech phrases with proper encoding handling
                self.czech_phrases = []
                for phrase in czech_phrases:
                    if phrase and phrase.strip():
                        # Ensure proper UTF-8 encoding and normalize
                        normalized_phrase = phrase.strip().lower()
                        # Handle Czech characters properly
                        normalized_phrase = self._normalize_czech_text(normalized_phrase)
                        self.czech_phrases.append(normalized_phrase)

            # Update English phrases if provided
            if english_phrases is not None:
                self.english_phrases = []
                for phrase in english_phrases:
                    if phrase and phrase.strip():
                        normalized_phrase = phrase.strip().lower()
                        self.english_phrases.append(normalized_phrase)

            # Update combined phrase list
            self.all_phrases = self.czech_phrases + self.english_phrases

            # Regenerate phrase variations for better matching
            self.phrase_variations = self._generate_phrase_variations()

            # Update custom word corrections map (includes all phrase words automatically)
            self.custom_word_corrections = self._build_word_corrections_map()

            # Log changes if requested
            if log_change:
                if czech_phrases is not None and old_czech_phrases != self.czech_phrases:
                    self.logger.info(f"Czech activation phrases updated: {len(self.czech_phrases)} phrases")
                    self.logger.debug(f"New Czech phrases: {self.czech_phrases}")

                if english_phrases is not None and old_english_phrases != self.english_phrases:
                    self.logger.info(f"English activation phrases updated: {len(self.english_phrases)} phrases")
                    self.logger.debug(f"New English phrases: {self.english_phrases}")

            return True

        except Exception as e:
            self.logger.error(f"Error updating activation phrases: {e}")
            return False

    # Removed vocabulary update methods that could cause crashes
    # Word corrections map is rebuilt automatically when phrases change

    def _normalize_czech_text(self, text: str) -> str:
        """Normalize Czech text for better recognition"""
        try:
            # Ensure proper UTF-8 encoding
            if isinstance(text, bytes):
                text = text.decode('utf-8')

            # Convert to lowercase using Czech locale if available
            import locale
            try:
                # Try to set Czech locale for proper character handling
                locale.setlocale(locale.LC_ALL, 'cs_CZ.UTF-8')
            except:
                try:
                    locale.setlocale(locale.LC_ALL, 'Czech_Czech Republic.1250')
                except:
                    pass  # Use default locale

            # Normalize the text
            normalized = text.lower()

            # Additional Czech character normalization if needed
            czech_char_map = {
                'á': 'a', 'č': 'c', 'ď': 'd', 'é': 'e', 'ě': 'e',
                'í': 'i', 'ň': 'n', 'ó': 'o', 'ř': 'r', 'š': 's',
                'ť': 't', 'ú': 'u', 'ů': 'u', 'ý': 'y', 'ž': 'z'
            }

            # Create both original and ASCII-normalized versions for better matching
            # Keep the original with Czech characters for primary matching
            return normalized

        except Exception as e:
            self.logger.warning(f"Error normalizing Czech text '{text}': {e}")
            return text.lower()

    def get_activation_phrases(self) -> List[str]:
        """Get current activation phrases (combined Czech and English)"""
        return self.all_phrases.copy()

    def get_czech_phrases(self) -> List[str]:
        """Get current Czech activation phrases"""
        return self.czech_phrases.copy()

    def get_english_phrases(self) -> List[str]:
        """Get current English activation phrases"""
        return self.english_phrases.copy()
