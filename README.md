# gigacheng-bot
# GIGACHENG Telegram Bot

## Project Overview
A Telegram bot powered by OpenAI's Assistant API that monitors group chats, analyzes sentiment, and provides contextual responses. The bot features advanced message processing, sentiment analysis, and decision-making capabilities.

## Core Components

### Main Application
- `gigacheng_telegram_bot.py`: Main entry point for the bot. Initializes all components and handles Telegram integration.
  - Manages the OpenAI client connection
  - Sets up message handlers
  - Coordinates between different components

### Message Processing Pipeline
1. **Message Management**
   - `message.py`: Defines the core Message dataclass used throughout the application
   - `message_processor.py`: Orchestrates the message processing workflow
     - Coordinates between decision engine, response handler, and analysis logger
     - Manages the complete lifecycle of message processing

2. **Analysis & Decision Making**
   - `decision_engine.py`: Core decision-making component
     - Determines if and when the bot should respond
     - Integrates sentiment analysis and context tracking
   - `sentiment_analyzer.py`: Analyzes message sentiment
     - Provides detailed sentiment scoring
     - Handles emoji impact and context modifiers
   - `keyword_detector.py`: Detects important keywords and triggers
     - Monitors for technical terms and project-related keywords
   - `context_tracker.py`: Maintains conversation context
     - Tracks message history and topic trends
     - Manages context timeframes

3. **Response Generation**
   - `response_handler.py`: Manages OpenAI Assistant interactions
     - Handles thread management
     - Formats messages with context
     - Rate limits responses

### Logging & Analysis
- `analysis_logger.py`: Comprehensive logging system
  - Records message analysis
  - Generates daily summaries
  - Maintains structured logs

### Configuration
- `settings.py`: Central configuration file
  - Contains all configurable parameters
  - Manages environment variables
  - Defines triggers and thresholds

## Data Flow
1. Telegram message received → `gigacheng_telegram_bot.py`
2. Message converted to internal format → `message.py`
3. Processing pipeline initiated → `message_processor.py`
4. Analysis performed:
   - Sentiment analysis → `sentiment_analyzer.py`
   - Keyword detection → `keyword_detector.py`
   - Context tracking → `context_tracker.py`
5. Decision making → `decision_engine.py`
6. Response generation (if needed) → `response_handler.py`
7. Logging → `analysis_logger.py`

## Dependencies
- OpenAI API
- Telegram Bot API
- TextBlob (for sentiment analysis)
- Python 3.8+
- Environment variables required:
  - `TELEGRAM_BOT_TOKEN`
  - `OPENAI_API_KEY`
  - `ASSISTANT_ID`

## File Dependencies Map
```
gigacheng_telegram_bot.py
├── decision_engine.py
│   ├── sentiment_analyzer.py
│   ├── keyword_detector.py
│   └── context_tracker.py
├── message_processor.py
│   ├── response_handler.py
│   └── analysis_logger.py
├── message.py
└── settings.py
```

## Error Handling
- Comprehensive error logging throughout all components
- Graceful degradation on API failures
- Rate limiting protection
- Message validation and sanitization
