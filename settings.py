## settings.py
from pathlib import Path
from dotenv import load_dotenv
import os
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Get the directory containing the settings file
SETTINGS_DIR = Path(__file__).resolve().parent
ENV_PATH = SETTINGS_DIR / '.env'

# Load environment variables
logger.info(f"Loading environment variables from: {ENV_PATH}")
load_dotenv(dotenv_path=ENV_PATH)

class Settings:
    # Load API Keys and IDs from environment variables
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    ASSISTANT_ID = os.getenv('ASSISTANT_ID')
    
    # Response Trigger Thresholds
    SENTIMENT_THRESHOLD_RESPONSE = 0.3     
    SENTIMENT_THRESHOLD_ALERT = -0.3     
    
    # Project Terms for Response Triggers
    PROJECT_TERMS = {
        'gigacheng', 'giga', 'cheng',    # Core project terms
        'alephium', 'alph', 'ayin',      # Ecosystem terms
        'candyswap', 'chengverse', 'chenginator'
    }

    # Technical Keywords for Monitoring
    TECHNICAL_KEYWORDS = [
        # Project/Token Criticism
        'shitcoin', 'rugpull', 'rug', 'rugged', 'honeypot', 'scam', 'ponzi', 
        'pyramid', 'exit scam', 'dead project', 'ghost chain', 'vaporware',
        'abandoned', 'inactive', 'no devs', 'copy paste', 'fake', 'fud', 
        'fuding', 'fudder', 'larpy', 'larper', 'shit coin', 'dead coin',
        'joke project', 'meme coin',
        
        # Price/Trading Related
        'dump', 'dumping', 'dumped', 'rekt', 'ngmi', 'going to zero',
        'bagholder', 'bagholding', 'exit liquidity', 'panic sell',
        'paper hands', 'paperhanded', 'down bad', 'dumpcoin', 'dip',
        'mcap too high', 'overvalued', 'expensive', 'priced in',
        'no volume', 'illiquid', 'bleeding',
        
        # Common Criticism
        'trash', 'garbage', 'useless', 'worthless', 'joke', 'stupid',
        'cringe', 'cope', 'copium', 'hopium', 'clown',
        
        # Community/Team Criticism
        'no community', 'dead chat', 'bot activity', 'paid shills',
        'anon team', 'anonymous devs', 'no docs', 'no whitepaper',
        'no roadmap', 'missed deadline', 'delayed', 'no updates',
        'empty promises'
    ]
    
    # Emoji Detection
    EMOJI_TRIGGERS = {
        # Positive
        '🚀', '📈', '💎', '🔥', '⚡', '🦁', '💪',
        '🤝', '✅', '🎉', '🤑', '👑', '🏆', '❤', '👍',
        
        # Negative
        '📉', '😢', '😭', '💀'
    }
    
    # Question Detection
    QUESTION_INDICATORS = {
        # Direct Questions
        'what', 'how', 'when', 'where', 'why', 'who',
        'which', 'whose', 'whom',
        
        # Crypto-Specific
        'wen', 'ser',
        
        # Action Questions
        'can', 'could', 'would', 'should', 'will',
        'do', 'does', 'did', 'has', 'have',
        'is', 'are', 'was', 'were'
    }
    
    # Context Settings
    CONTEXT_SETTINGS = {
        'MAX_CONTEXT_MESSAGES': 50,       # Maximum messages to keep in context
        'CONTEXT_TIMEFRAME_MINUTES': 30,  # How long to maintain context
        'MIN_MESSAGES_FOR_TREND': 5,      # Messages needed to establish trend
        'DEAD_CHAT_MINUTES': 2,          # Time before considering chat "dead"
    }
    
    # Rate Limiting
    RATE_LIMITS = {
        'MIN_RESPONSE_INTERVAL': 15,       
        'MAX_DAILY_RESPONSES': 100,        
        'RANDOM_RESPONSE_PROBABILITY': 0.1
    }

    # Telegram-Specific Settings
    TELEGRAM_SETTINGS = {
        'AUTO_RESPOND': True,
        'ALLOWED_CHAT_TYPES': ['group', 'supergroup'],
        'MAX_MESSAGE_LENGTH': 4096,       # Telegram message length limit
        'ALLOWED_CHATS': [],             # Empty list = all chats allowed
        'ADMIN_USERS': []                # Empty list = no admins
    }
    
    # Response Priority Categories
    RESPONSE_PRIORITIES = {
        'MENTIONS': 1.0,                 # Direct mentions
        'QUESTIONS': 0.8,                # Project questions
        'NEGATIVE_SENTIMENT': 0.7,       # Strong negative sentiment
        'TECHNICAL_DISCUSSION': 0.6,     # Technical topics
        'PRICE_DISCUSSION': 0.5,         # Price/market discussion
        'COMMUNITY': 0.4,                # Community topics
        'RANDOM': 0.1                    # Random engagement
    }
    
    # Alert Thresholds
    ALERT_THRESHOLDS = {
        'NEGATIVE_MESSAGE_STREAK': 3,    # Consecutive negative messages
        'SPAM_MESSAGES_PER_MINUTE': 10,  # Messages per minute for spam
        'INACTIVE_HOURS': 24,            # Hours before marking chat inactive
        'SENTIMENT_SWING': 0.5           # Large sentiment change threshold
    }

    @classmethod
    def validate_env_vars(cls):
        """Validate that all required environment variables are set"""
        required_vars = ['TELEGRAM_BOT_TOKEN', 'OPENAI_API_KEY', 'ASSISTANT_ID']
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

# Validate environment variables when settings are imported
Settings.validate_env_vars()