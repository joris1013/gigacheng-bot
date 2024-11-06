import re
from textblob import TextBlob
from typing import Dict
from message import Message
from settings import Settings

class SentimentAnalyzer:
    def __init__(self):
        # Project Status Terms
        self.status_modifiers = {
            'working on': 0.3,
            'development': 0.3,
            'progress': 0.4,
            'update': 0.2,
            'integration': 0.3,
            'release': 0.3,
            'launching': 0.3,
            'delays': -0.2,
            'delayed': -0.2,
            'waiting': -0.1,
        }
        
        # Core project terms (slightly positive)
        self.project_modifiers = {
            'gigacheng': 0.3,
            'giga': 0.2,
            'cheng': 0.2,
            'alephium': 0.2,
            'alph': 0.2,
            'ayin': 0.2,
            'candyswap': 0.2,
            'chengverse': 0.3,
            'chenginator': 0.3,
        }
        
        # Community/Chat Terms
        self.community_modifiers = {
            'gm': 0.1,
            'ser': 0.1,
            'sers': 0.1,
            'fam': 0.2,
            'lfg': 0.3,
            'wagmi': 0.3,
        }
        
        # Market Terms (Stronger weights)
        self.market_modifiers = {
            # Positive
            'moon': 0.4,
            'pump': 0.3,
            'pumping': 0.3,
            'bullish': 0.4,
            'support': 0.3,
            'ath': 0.4,
            'accumulate': 0.2,
            'volume': -0.2,  # Usually in context of "need more volume"
            'liquidity': -0.1,  # Usually in context of "low liquidity"
            
            # Negative
            'dump': -0.5,
            'dumping': -0.5,
            'bearish': -0.4,
            'dip': -0.3,
            'down': -0.3,
            'rough': -0.3,
            'low': -0.2,
        }
        
        # Criticism Terms (Strengthened negative impact)
        self.criticism_modifiers = {
            'dead': -0.5,
            'inactive': -0.4,
            'abandoned': -0.6,
            'rug': -0.7,
            'rugpull': -0.7,
            'scam': -0.7,
            'fud': -0.4,
            'worried': -0.4,
            'concerned': -0.4,
            'issues': -0.3,
            'broken': -0.4,
            'bug': -0.3,
            'delayed': -0.3,
            'slow': -0.3,
        }

        # Reduced emoji impact
        self.emoji_sentiment = {
            '🚀': 0.2,
            '📈': 0.2,
            '💪': 0.1,
            '🔥': 0.2,
            '💎': 0.1,
            '👍': 0.1,
            '📉': -0.2,
            '😢': -0.1,
            '💀': -0.2,
        }

        # Multipliers
        self.exclamation_multiplier = 1.05
        self.caps_multiplier = 1.1
        self.emoji_repeat_multiplier = 1.02
        self.question_discount = 0.5  # Reduce sentiment impact for questions

    def analyze(self, message: Message) -> Dict[str, float]:
        blob = TextBlob(message.content)
        base_sentiment = blob.sentiment.polarity * 1.2  # Slightly increase base sentiment weight
        base_subjectivity = blob.sentiment.subjectivity
        
        # Initialize sentiment with base
        adjusted_sentiment = base_sentiment
        
        text_lower = message.content.lower()
        words = text_lower.split()
        
        # Track modifiers
        all_modifiers = []
        
        # Check each modifier dictionary
        for modifier_dict in [self.status_modifiers, self.project_modifiers, 
                            self.community_modifiers, self.market_modifiers, 
                            self.criticism_modifiers]:
            for term, modifier in modifier_dict.items():
                if term in text_lower:
                    all_modifiers.append(modifier)
        
        # Apply modifiers with diminishing returns
        if all_modifiers:
            # Average the modifiers but maintain sign
            avg_modifier = sum(all_modifiers) / len(all_modifiers)
            if abs(avg_modifier) > 0.1:  # Only apply if significant
                adjusted_sentiment = self._adjust_sentiment(adjusted_sentiment, avg_modifier)
        
        # Count and apply emoji sentiment with reduced impact
        emoji_impact = 0
        for emoji, value in self.emoji_sentiment.items():
            count = message.content.count(emoji)
            if count > 0:
                emoji_impact += value * min(count, 2) * 0.3
        
        if emoji_impact != 0:
            adjusted_sentiment = self._adjust_sentiment(adjusted_sentiment, emoji_impact)
        
        # Reduce sentiment impact for questions
        if '?' in message.content or any(word in ['wen', 'when', 'what', 'how', 'why'] for word in words):
            adjusted_sentiment *= self.question_discount
        
        # Apply caps modifier for emphasis
        caps_words = re.findall(r'\b[A-Z]{2,}\b', message.content)
        if caps_words:
            adjusted_sentiment *= self.caps_multiplier
        
        # Normalize final sentiment
        final_sentiment = max(min(adjusted_sentiment, 1.0), -1.0)
        
        return {
            'polarity': final_sentiment,
            'subjectivity': base_subjectivity,
            'base_sentiment': base_sentiment,
            'emoji_impact': emoji_impact,
            'has_custom_keywords': bool(all_modifiers),
            'sentiment_category': self._get_sentiment_category(final_sentiment)
        }

    def _adjust_sentiment(self, current: float, modifier: float) -> float:
        """Adjust sentiment with diminishing returns"""
        if modifier > 0:
            return current + (1 - current) * modifier * 0.4
        else:
            return current + (current + 1) * modifier * 0.5

    def _get_sentiment_category(self, sentiment: float) -> str:
        """More nuanced sentiment categories"""
        if sentiment >= 0.6:
            return "GIGA BULLISH"
        elif sentiment >= 0.3:
            return "BULLISH"
        elif sentiment >= 0.1:
            return "SLIGHTLY BULLISH"
        elif sentiment > -0.1:
            return "NEUTRAL"
        elif sentiment > -0.3:
            return "SLIGHTLY BEARISH"
        elif sentiment > -0.6:
            return "BEARISH"
        else:
            return "FUD DETECTED"