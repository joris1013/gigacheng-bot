# response_handler.py
from typing import Dict, Tuple
from datetime import datetime, timedelta
import asyncio
import logging
import re
import json
from pathlib import Path
from openai import OpenAI
from message import Message
from settings import Settings
from decision_engine import DecisionEngine

logger = logging.getLogger(__name__)

class ResponseHandler:
    def __init__(self, client: OpenAI, decision_engine: DecisionEngine):
        self.client = client
        self.decision_engine = decision_engine
        self.last_response_times = {}
        
        # Load existing thread IDs from file
        self.threads_file = Path("thread_ids.json")
        if self.threads_file.exists():
            try:
                with open(self.threads_file, 'r') as f:
                    self.thread_ids = json.load(f)
                logger.info(f"Loaded {len(self.thread_ids)} existing threads")
            except Exception as e:
                logger.error(f"Error loading threads: {e}")
                self.thread_ids = {}
        else:
            self.thread_ids = {}
            logger.info("Starting with fresh thread mapping")

    def _save_threads(self):
        """Save thread IDs to file"""
        try:
            with open(self.threads_file, 'w') as f:
                json.dump(self.thread_ids, f)
            logger.info(f"Saved {len(self.thread_ids)} threads to file")
        except Exception as e:
            logger.error(f"Error saving threads: {e}")

    def clean_response(self, text: str) -> str:
        """Clean up response text by removing reference notations"""
        cleaned = re.sub(r'【\d+:\d+†[^】]+】', '', text)
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

    async def _get_or_create_thread(self, chat_id):
        """Get existing thread or create new one for the chat"""
        try:
            chat_id_str = str(chat_id)
            if chat_id_str not in self.thread_ids:
                thread = self.client.beta.threads.create()
                self.thread_ids[chat_id_str] = thread.id
                self._save_threads()  # Save after creating new thread
                logger.info(f"Created new thread for chat {chat_id}: {thread.id}")
            else:
                logger.info(f"Using existing thread for chat {chat_id}: {self.thread_ids[chat_id_str]}")
            return self.thread_ids[chat_id_str]
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
            # Get full context for logging
            full_context = self._get_full_context(message, sentiment_details, username, is_reply)
            logger.info(f"Processing message with context: {full_context}")
            
            thread_id = await self._get_or_create_thread(chat_id)
            
            # Simplified context for assistant
            context_message = self._format_message_with_context(
                message,
                sentiment_details,
                username,
                is_reply
            )
            
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=context_message
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
                elif run_status.status == 'failed':
                    raise Exception(f"Assistant run failed for chat {chat_id}")
                
                await asyncio.sleep(1)
            
            messages = self.client.beta.threads.messages.list(thread_id=thread_id)
            
            for msg in messages.data:
                if msg.role == "assistant":
                    response_text = msg.content[0].text.value
                    return self.clean_response(response_text)
            
            raise Exception("No assistant response found")
            
        except Exception as e:
            logger.error(f"Error getting assistant response: {str(e)}")
            raise