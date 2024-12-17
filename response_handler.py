# response_handler.py
from typing import Dict, Tuple
from datetime import datetime, timedelta
import asyncio
import logging
import re
from openai import OpenAI
from message import Message
from settings import Settings
from decision_engine import DecisionEngine

logger = logging.getLogger(__name__)

class ResponseHandler:
    def __init__(self, client: OpenAI, decision_engine: DecisionEngine):
        self.client = client
        self.decision_engine = decision_engine
        self.thread_ids = {}
        self.last_response_times = {}

    def clean_response(self, text: str) -> str:
        """Clean up response text by removing reference notations and formatting"""
        cleaned = re.sub(r'【\d+:\d+†[^】]+】', '', text)
        cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)  # Remove bold formatting
        cleaned = re.sub(r'\d\.\s+', '', cleaned)  # Remove numbered lists
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()

    async def _check_rate_limit(self, chat_id: int) -> bool:
        """Check if we should rate limit responses for this chat"""
        current_time = datetime.now()
        if chat_id in self.last_response_times:
            time_since_last = (current_time - self.last_response_times[chat_id]).seconds
            if time_since_last < Settings.RATE_LIMITS['MIN_RESPONSE_INTERVAL']:
                logger.info(f"Rate limited chat {chat_id}: {time_since_last}s since last response")
                return False
        return True

    async def _get_or_create_thread(self, chat_id: int):
        """Get existing thread or create new one for the chat"""
        try:
            if chat_id not in self.thread_ids:
                thread = self.client.beta.threads.create()
                self.thread_ids[chat_id] = thread.id
                logger.info(f"Created new thread for chat {chat_id}")
            return self.thread_ids[chat_id]
        except Exception as e:
            logger.error(f"Error creating/getting thread: {str(e)}")
            raise

    def _format_message_with_context(self, message: Message, sentiment_details: dict, 
                                   username: str, is_reply: bool = False) -> str:
        """Format message with sentiment context"""
        reply_context = "This is a reply to your previous message. " if is_reply else ""
        
        chat_context = self.decision_engine.context_tracker.get_context_summary()
        
        context = f"""[Message Analysis:
Sender: {username}
Is Reply: {is_reply}
Sentiment: {sentiment_details.get('sentiment_category', 'NEUTRAL')}
Score: {sentiment_details.get('polarity', 0):.2f}
Subjectivity: {sentiment_details.get('subjectivity', 0):.2f}
Keywords: {', '.join(message.keywords) if message.keywords else 'None'}
Current Chat Context: {chat_context.get('current_context', 'None')}
Active Discussion Topics: {', '.join([topic[0] for topic in chat_context.get('top_topics', [])])}]

{reply_context}Message: {message.content}"""
        return context

    async def get_assistant_response(self, chat_id: int, message: Message, 
                                   sentiment_details: dict, username: str, 
                                   is_reply: bool = False) -> str:
        """Get response from OpenAI assistant using v2 API"""
        try:
            thread_id = await self._get_or_create_thread(chat_id)
            
            # Create message in thread
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=self._format_message_with_context(
                    message, 
                    sentiment_details, 
                    username,
                    is_reply
                )
            )
            
            # Create run
            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=Settings.ASSISTANT_ID
            )
            
            start_time = datetime.now()
            timeout = timedelta(seconds=30)
            
            while True:
                if datetime.now() - start_time > timeout:
                    raise TimeoutError("Assistant response timed out")
                    
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
                
                if run_status.status == 'completed':
                    break
                elif run_status.status == 'failed':
                    raise Exception(f"Assistant run failed for chat {chat_id}")
                elif run_status.status == 'requires_action':
                    logger.info(f"Run {run.id} requires action: {run_status.required_action}")
                
                await asyncio.sleep(1)
            
            messages = self.client.beta.threads.messages.list(
                thread_id=thread_id,
                order="desc",
                limit=1
            )
            
            for msg in messages.data:
                if msg.role == "assistant":
                    response_text = msg.content[0].text.value
                    return self.clean_response(response_text)
            
            raise Exception("No assistant response found")
            
        except Exception as e:
            logger.error(f"Error getting assistant response: {str(e)}")
            raise