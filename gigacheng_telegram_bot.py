# gigacheng_telegram_bot.py
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters
from openai import OpenAI
import logging
from datetime import datetime
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
            # Initialize OpenAI client with v2 API configuration
            self.client = OpenAI(
                api_key=Settings.OPENAI_API_KEY,
                default_headers={"OpenAI-Beta": "assistants=v2"}
            )
            
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
            
            # Check assistant configuration
            self._check_assistant_config()
            
            logger.info("Bot initialized successfully with v2 API")
        except Exception as e:
            logger.error(f"Failed to initialize bot: {str(e)}")
            raise

    def _check_assistant_config(self):
        """Verify assistant configuration"""
        try:
            assistant = self.client.beta.assistants.retrieve(Settings.ASSISTANT_ID)
            logger.info(f"Assistant Configuration:")
            logger.info(f"Name: {assistant.name}")
            logger.info(f"Model: {assistant.model}")
            
        except Exception as e:
            logger.error(f"Error checking assistant configuration: {str(e)}")
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

    async def _daily_summary_task(self):
        """Generate daily summary at end of day"""
        try:
            summary = self.analysis_logger.generate_daily_summary()
            self.analysis_logger.log_aggregate_stats({
                'date': datetime.now().strftime('%Y-%m-%d'),
                'summary': summary
            })
        except Exception as e:
            logger.error(f"Error generating daily summary: {str(e)}")

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