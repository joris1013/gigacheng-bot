from typing import List, Set
from message import Message
from settings import Settings

class KeywordDetector:
    def __init__(self):
        # Load keywords from settings
        self.technical_keywords = set(Settings.TECHNICAL_KEYWORDS)
        self.emoji_triggers = set(Settings.EMOJI_TRIGGERS)
    
    def detect_keywords(self, message: Message) -> Set[str]:
        """Detect keywords in message"""
        # Convert message to lowercase and split into words
        words = set(message.content.lower().split())
        
        # Find intersection with our technical keywords
        detected_keywords = words.intersection(self.technical_keywords)
        
        # Detect emojis
        emojis = set([char for char in message.content if char in self.emoji_triggers])
        
        # Combine both sets
        detected_keywords.update(emojis)
        
        return detected_keywords
    
    def has_important_keywords(self, keywords: Set[str]) -> bool:
        """Check if detected keywords are important enough to trigger a response"""
        # For now, any keyword is considered important
        return bool(keywords)