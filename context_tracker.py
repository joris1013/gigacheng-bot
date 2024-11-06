from collections import deque
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from message import Message
from settings import Settings

class ContextTracker:
    def __init__(self):
        # Use deque with maxlen for automatic size management
        self.messages = deque(maxlen=Settings.CONTEXT_SETTINGS['MAX_CONTEXT_MESSAGES'])
        self.current_context: Optional[str] = None
        self.context_start_time = datetime.now()
        self.topic_frequency: Dict[str, int] = {}
    
    def add_message(self, message: Message):
        """Add message to context and update tracking"""
        self.messages.append(message)
        self._clean_old_messages()
        self._update_context()
        self._update_topic_frequency(message)
    
    def _clean_old_messages(self):
        """Remove messages older than the context timeframe"""
        cutoff_time = datetime.now() - timedelta(
            minutes=Settings.CONTEXT_SETTINGS['CONTEXT_TIMEFRAME_MINUTES']
        )
        
        # Remove old messages from the front of the deque
        while self.messages and self.messages[0].timestamp < cutoff_time:
            self.messages.popleft()
    
    def _update_topic_frequency(self, message: Message):
        """Update the frequency count of topics/keywords"""
        if message.keywords:
            for keyword in message.keywords:
                self.topic_frequency[keyword] = self.topic_frequency.get(keyword, 0) + 1
    
    def _update_context(self):
        """Update current context based on recent messages"""
        if len(self.messages) < Settings.CONTEXT_SETTINGS['MIN_MESSAGES_FOR_TREND']:
            return
        
        # Reset topic frequency if context is too old
        if (datetime.now() - self.context_start_time).total_seconds() > \
           Settings.CONTEXT_SETTINGS['CONTEXT_TIMEFRAME_MINUTES'] * 60:
            self.topic_frequency.clear()
            self.context_start_time = datetime.now()
        
        # Find most common topic
        if self.topic_frequency:
            self.current_context = max(
                self.topic_frequency.items(),
                key=lambda x: x[1]
            )[0]
    
    def get_context_summary(self) -> Dict:
        """Get summary of current context"""
        return {
            'current_context': self.current_context,
            'message_count': len(self.messages),
            'top_topics': sorted(
                self.topic_frequency.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            'context_age_minutes': (
                datetime.now() - self.context_start_time
            ).total_seconds() / 60
        }
    
    def is_topic_trending(self, keyword: str) -> bool:
        """Check if a topic is trending in recent messages"""
        if keyword not in self.topic_frequency:
            return False
            
        # Consider a topic trending if it appears in > 20% of recent messages
        topic_frequency = self.topic_frequency[keyword]
        message_count = len(self.messages)
        
        return message_count > 0 and (topic_frequency / message_count) > 0.2