# message_processor.py
from datetime import datetime
import logging
from typing import Tuple, Dict
from message import Message
from decision_engine import DecisionEngine
from analysis_logger import AnalysisLogger
from response_handler import ResponseHandler

logger = logging.getLogger(__name__)

class MessageProcessor:
    def __init__(self, decision_engine: DecisionEngine, 
                 response_handler: ResponseHandler,
                 analysis_logger: AnalysisLogger):
        self.decision_engine = decision_engine
        self.response_handler = response_handler
        self.analysis_logger = analysis_logger

    async def process_message(self, chat_id: int, message: Message, 
                            username: str, is_reply_to_bot: bool = False) -> Tuple[bool, str]:
        """Process a message and return response if needed"""
        try:
            logger.info(f"""
Received message:
Chat ID: {chat_id}
User: {username}
Message Preview: {message.content[:50]}...
Timestamp: {datetime.now()}
            """)

            if not is_reply_to_bot and not await self.response_handler._check_rate_limit(chat_id):
                logger.info(f"Skipping response due to rate limit for chat {chat_id}")
                return False, None

            should_respond, debug_info = self.decision_engine.process_message(
                message, 
                is_reply_to_bot=is_reply_to_bot
            )

            context_summary = self.decision_engine.context_tracker.get_context_summary()
            sentiment_details = self.decision_engine.sentiment_analyzer.analyze(message)

            logger.info(f"""
Message Analysis Results:
Decision: {'Will Respond' if should_respond or is_reply_to_bot else 'No Response'}
Sentiment Score: {sentiment_details.get('polarity', 0):.2f}
Keywords Detected: {', '.join(message.keywords) if message.keywords else 'None'}
Is Reply to Bot: {is_reply_to_bot}
Debug Info: {debug_info}
            """)

            bot_response = None
            if should_respond or is_reply_to_bot:
                bot_response = await self.response_handler.get_assistant_response(
                    chat_id,
                    message,
                    sentiment_details,
                    username,
                    is_reply_to_bot
                )
                
                self.response_handler.last_response_times[chat_id] = datetime.now()

            self.analysis_logger.log_analysis(
                chat_id=chat_id,
                message_obj=message,
                sentiment_analysis=sentiment_details,
                decision_info=debug_info,
                bot_response=bot_response,
                context_summary=context_summary
            )

            return should_respond or is_reply_to_bot, bot_response

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return False, None