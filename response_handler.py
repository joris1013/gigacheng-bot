# response_handler.py
from typing import Dict, Tuple
from datetime import datetime, timedelta
import asyncio
import logging
import re
from pathlib import Path
import json
from openai import OpenAI
from message import Message
from settings import Settings
from decision_engine import DecisionEngine

logger = logging.getLogger(__name__)

class ResponseHandler:
    def __init__(self, client: OpenAI, decision_engine: DecisionEngine):
        self.client = client
        self.decision_engine = decision_engine
        self.project_root = Path(__file__).resolve().parent
        self.thread_file = self.project_root / 'data' / 'thread_ids.json'
        self.thread_ids = self._load_thread_ids()
        self.last_response_times = {}
        
        # Create data directory if it doesn't exist
        self.thread_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_thread_ids(self) -> Dict[int, str]:
        """Load thread IDs from file"""
        try:
            if self.thread_file.exists():
                with open(self.thread_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading thread IDs: {str(e)}")
            return {}

    def _save_thread_ids(self):
        """Save thread IDs to file"""
        try:
            with open(self.thread_file, 'w') as f:
                json.dump(self.thread_ids, f)
        except Exception as e:
            logger.error(f"Error saving thread IDs: {str(e)}")

    def clean_response(self, text: str) -> str:
        """Clean up response text by removing reference notations"""
        cleaned = re.sub(r'【\d+:\d+†[^】]+】', '', text)
        cleaned = re.sub(r'\[.*?\]:', '', cleaned)
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

    async def _get_or_create_thread(self, chat_id: int) -> str:
        """Get existing thread or create new one for the chat"""
        try:
            chat_id_str = str(chat_id)
            
            if chat_id_str not in self.thread_ids:
                thread = self.client.beta.threads.create()
                self.thread_ids[chat_id_str] = thread.id
                self._save_thread_ids()
                logger.info(f"Created new thread for chat {chat_id}: {thread.id}")
                return thread.id
            
            # Verify thread still exists
            try:
                self.client.beta.threads.retrieve(self.thread_ids[chat_id_str])
                return self.thread_ids[chat_id_str]
            except Exception:
                # Thread doesn't exist, create new one
                thread = self.client.beta.threads.create()
                self.thread_ids[chat_id_str] = thread.id
                self._save_thread_ids()
                logger.info(f"Recreated thread for chat {chat_id}: {thread.id}")
                return thread.id
                
        except Exception as e:
            logger.error(f"Error creating/getting thread: {str(e)}")
            raise

    def _format_message_with_context(self, message: Message, sentiment_details: dict, 
                                   username: str, is_reply: bool = False) -> str:
        """Format message for the assistant"""
        reply_context = "This is a reply to your previous message. " if is_reply else ""
        return f"{reply_context}User {username} says: {message.content}"

    def _get_full_context(self, message: Message, sentiment_details: dict,
                         username: str, is_reply: bool = False) -> Dict:
        """Get full context for logging purposes"""
        chat_context = self.decision_engine.context_tracker.get_context_summary()
        return {
            'sender': username,
            'is_reply': is_reply,
            'sentiment': sentiment_details.get('sentiment_category', 'NEUTRAL'),
            'score': sentiment_details.get('polarity', 0),
            'subjectivity': sentiment_details.get('subjectivity', 0),
            'keywords': message.keywords,
            'current_context': chat_context.get('current_context', 'None'),
            'active_topics': [topic[0] for topic in chat_context.get('top_topics', [])]
        }

    async def get_assistant_response(self, chat_id: int, message: Message, 
                                   sentiment_details: dict, username: str, 
                                   is_reply: bool = False) -> str:
        """Get response from OpenAI assistant"""
        try:
            full_context = self._get_full_context(message, sentiment_details, username, is_reply)
            logger.info(f"Processing message with context: {full_context}")
            
            thread_id = await self._get_or_create_thread(chat_id)
            
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=self._format_message_with_context(message, sentiment_details, username, is_reply)
            )
            
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
                elif run_status.status in ['failed', 'cancelled', 'expired']:
                    raise Exception(f"Assistant run failed with status: {run_status.status}")
                
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