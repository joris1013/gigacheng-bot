# gigacheng_telegram_bot.py
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters
from openai import OpenAI
import logging
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv
from message import Message
from settings import Settings
from decision_engine import DecisionEngine
from analysis_logger import AnalysisLogger
from response_handler import ResponseHandler
from message_processor import MessageProcessor

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class GigaChengGroupBot:
    def __init__(self):
        try:
            # Just load environment variables and create client
            load_dotenv()
            self.client = OpenAI(api_key=Settings.OPENAI_API_KEY)
            
            # Initialize components
            self.decision_engine = DecisionEngine()
            self.bot_username = "GIGACHENG_BOT"
            self.analysis_logger = AnalysisLogger()
            self.response_handler = ResponseHandler(self.client, self.decision_engine)
            self.message_processor = MessageProcessor(
                self.decision_engine,
                self.response_handler,
                self.analysis_logger
            )
            logger.info("Bot initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize bot: {str(e)}")
            raise

    async def handle_group_message(self, update: Update, context):
        """Handle incoming group messages"""
        try:
            chat_id = update.effective_chat.id
            message_text = update.effective_message.text
            user_id = update.effective_user.id
            username = update.effective_user.username or "Unknown"
            
            is_reply_to_bot = False
            if update.effective_message.reply_to_message:
                reply_from = update.effective_message.reply_to_message.from_user
                if reply_from and reply_from.username == self.bot_username:
                    is_reply_to_bot = True
            
            message = Message(
                id=str(update.effective_message.message_id),
                content=message_text,
                user_id=str(user_id),
                timestamp=datetime.now()
            )

            should_respond, response = await self.message_processor.process_message(
                chat_id,
                message,
                username,
                is_reply_to_bot
            )

            if should_respond and response:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=response,
                    reply_to_message_id=update.effective_message.message_id
                )
                
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")

    def run(self):
        """Run the bot"""
        try:
            application = Application.builder().token(Settings.TELEGRAM_BOT_TOKEN).build()
            
            application.add_handler(MessageHandler(
                filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND, 
                self.handle_group_message
            ))
            
            logger.info("Starting bot...")
            application.run_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            logger.error(f"Failed to start bot: {str(e)}")
            raise

if __name__ == '__main__':
    try:
        bot = GigaChengGroupBot()
        bot.run()
    except Exception as e:
        logger.error(f"Bot crashed: {str(e)}")