from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List

@dataclass
class Message:
    id: str
    content: str
    user_id: str
    timestamp: datetime
    sentiment_score: float = 0.0
    sentiment_subjectivity: float = 0.0
    keywords: List[str] = field(default_factory=list)
    context_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'content': self.content,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat(),
            'sentiment_score': self.sentiment_score,
            'sentiment_subjectivity': self.sentiment_subjectivity,
            'keywords': self.keywords,
            'context_id': self.context_id
        }