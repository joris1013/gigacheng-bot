from typing import Optional, Dict, Set, Tuple
from datetime import datetime, timedelta
import random
import re
import logging
import traceback
from message import Message
from sentiment_analyzer import SentimentAnalyzer
from keyword_detector import KeywordDetector
from context_tracker import ContextTracker
from settings import Settings

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DecisionEngine:
    def __init__(self):
        try:
            self.sentiment_analyzer = SentimentAnalyzer()
            self.keyword_detector = KeywordDetector()
            self.context_tracker = ContextTracker()
            self.last_response_time: Optional[datetime] = None
            self.project_terms = Settings.PROJECT_TERMS
            self.bot_name = "GIGACHENG"
            logger.info("DecisionEngine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DecisionEngine: {str(e)}")
            raise

    def _is_negative_about_projects(self, message: Message) -> bool:
        """Check if message is negative about project terms"""
        try:
            text_lower = message.content.lower()
            words = text_lower.split()
            
            # Check for project mention
            has_project_mention = any(term in text_lower for term in self.project_terms)
            
            if has_project_mention and message.sentiment_score < Settings.SENTIMENT_THRESHOLD_ALERT:
                return True
                
            return False
        except Exception as e:
            logger.error(f"Error in negative sentiment detection: {str(e)}")
            return False

    def _is_question_about_project(self, message: Message) -> bool:
        """Check if message contains question about project"""
        try:
            text_lower = message.content.lower()
            words = text_lower.split()
            
            # Check for project mention
            has_project_mention = any(term in text_lower for term in self.project_terms)
            
            if not has_project_mention:
                return False
            
            # Check for question indicators
            if ('?' in message.content or 
                any(word in Settings.QUESTION_INDICATORS for word in words)):
                return True
                
            return False
        except Exception as e:
            logger.error(f"Error in question detection: {str(e)}")
            return False

    def _should_respond(self, message: Message, is_reply_to_bot: bool = False) -> Tuple[bool, str]:
        """Determine if bot should respond to message"""
        try:
            # Check rate limiting
            if self.last_response_time:
                time_since_last = (datetime.now() - self.last_response_time).seconds
                if time_since_last < Settings.RATE_LIMITS['MIN_RESPONSE_INTERVAL']:
                    logger.info(f"Rate limited: {time_since_last}s since last response")
                    return False, "Rate limited"
            
            # Check project mentions (highest priority)
            if any(term in message.content.lower() for term in self.project_terms):
                logger.info("Responding to project mention")
                return True, "Project mention"
            
            # Check sentiment thresholds
            if message.sentiment_score <= Settings.SENTIMENT_THRESHOLD_ALERT:
                logger.info(f"Responding to negative sentiment: {message.sentiment_score}")
                return True, "Negative sentiment"
            elif message.sentiment_score >= Settings.SENTIMENT_THRESHOLD_RESPONSE:
                logger.info(f"Responding to positive sentiment: {message.sentiment_score}")
                return True, "Positive sentiment"
            
            # Check for project questions
            if self._is_question_about_project(message):
                logger.info("Responding to project question")
                return True, "Project question"
            
            # Check for technical keywords with significant sentiment
            if message.keywords and abs(message.sentiment_score) > 0.3:
                logger.info("Responding to technical discussion with sentiment")
                return True, "Technical discussion"
            
            # Random engagement with lower probability
            if random.random() < Settings.RATE_LIMITS['RANDOM_RESPONSE_PROBABILITY']:
                logger.info("Random response triggered")
                return True, "Random engagement"
            
            logger.info("No response triggers met")
            return False, "No triggers met"
            
        except Exception as e:
            logger.error(f"Error in response decision making: {str(e)}")
            return False, f"Error: {str(e)}"

    def process_message(self, message: Message, is_reply_to_bot: bool = False) -> Tuple[bool, Dict]:
        """Process message and decide on response"""
        debug_info = {
            'message_id': message.id,
            'content': message.content[:50] + '...' if len(message.content) > 50 else message.content,
            'sentiment_score': 0.0,
            'sentiment_subjectivity': 0.0,
            'has_keywords': False,
            'keywords': [],
            'decision_reason': 'Not processed',
            'should_respond': False
        }
        
        try:
            logger.info(f"Processing message: {message.content[:50]}...")
            
            # Analyze sentiment
            sentiment = self.sentiment_analyzer.analyze(message)
            message.sentiment_score = sentiment['polarity']
            message.sentiment_subjectivity = sentiment['subjectivity']
            debug_info['sentiment_score'] = message.sentiment_score
            debug_info['sentiment_subjectivity'] = message.sentiment_subjectivity
            
            # Detect keywords
            keywords = self.keyword_detector.detect_keywords(message)
            message.keywords = list(keywords)
            debug_info['has_keywords'] = bool(keywords)
            debug_info['keywords'] = list(keywords)
            
            # Update context
            self.context_tracker.add_message(message)
            
            # Make response decision
            should_respond, reason = self._should_respond(message, is_reply_to_bot)
            debug_info['should_respond'] = should_respond
            debug_info['decision_reason'] = reason
            
            if should_respond:
                self.last_response_time = datetime.now()
            
            return should_respond, debug_info
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            debug_info['decision_reason'] = f"Error: {str(e)}"
            return False, debug_info
        
    def should_generate_spontaneous_message(self) -> bool:
        """Check if bot should generate spontaneous message"""
        try:
            if not self.last_response_time:
                return True
            
            time_since_last_message = (
                datetime.now() - self.context_tracker.messages[-1].timestamp
                if self.context_tracker.messages
                else timedelta(hours=1)
            )
                
            return time_since_last_message > timedelta(
                minutes=Settings.CONTEXT_SETTINGS['DEAD_CHAT_MINUTES']
            )
            
        except Exception as e:
            logger.error(f"Error in spontaneous message check: {str(e)}")
            return False