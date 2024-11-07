# response_handler.py
from typing import Dict, Tuple, List
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
        # Remove citation markers
        cleaned = re.sub(r'【\d+:\d+†[^】]+】', '', text)
        # Remove file references
        cleaned = re.sub(r'\[.*?\]:', '', cleaned)
        # Remove multiple spaces
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
            # Convert chat_id to string for JSON serialization
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
        # Include sentiment information for context
        sentiment_score = sentiment_details.get('polarity', 0)
        sentiment_category = sentiment_details.get('sentiment_category', 'NEUTRAL')
        
        # Build context string
        context_parts = []
        
        # Add reply context if applicable
        if is_reply:
            context_parts.append("This is a reply to your previous message.")
        
        # Add sentiment context
        context_parts.append(f"Message sentiment: {sentiment_category} ({sentiment_score:.2f})")
        
        # Add active topics if available
        if message.keywords:
            context_parts.append(f"Topics detected: {', '.join(message.keywords)}")
        
        # Combine context with user message
        context_str = " | ".join(context_parts)
        
        return f"""Context: {context_str}
User {username} says: {message.content}"""

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
            
            # Get or create thread
            thread_id = await self._get_or_create_thread(chat_id)
            
            # Format message with context
            context_message = self._format_message_with_context(
                message,
                sentiment_details,
                username,
                is_reply
            )
            
            # Create message in thread
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=context_message
            )
            
            # Create run with additional instructions
            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=Settings.ASSISTANT_ID,
                instructions="Maintain character and use file search for accurate information."
            )
            
            # Wait for response with timeout
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
            
            # Get the latest assistant message
            messages = self.client.beta.threads.messages.list(
                thread_id=thread_id,
                order="desc",
                limit=1
            )
            
            for msg in messages.data:
                if msg.role == "assistant":
                    response_text = msg.content[0].text.value
                    cleaned_response = self.clean_response(response_text)
                    
                    # Log successful response
                    logger.info(f"""
Response generated:
Thread ID: {thread_id}
Raw Response: {response_text}
Cleaned Response: {cleaned_response}
                    """)
                    
                    return cleaned_response
            
            raise Exception("No assistant response found")
            
        except Exception as e:
            logger.error(f"Error getting assistant response: {str(e)}")
            raise

    async def cleanup_old_threads(self, max_age_days: int = 7):
        """Clean up old threads"""
        try:
            current_time = datetime.now()
            threads_to_delete = []
            
            for chat_id, thread_id in self.thread_ids.items():
                try:
                    thread = self.client.beta.threads.retrieve(thread_id)
                    thread_age = current_time - datetime.fromisoformat(thread.created_at)
                    
                    if thread_age.days > max_age_days:
                        self.client.beta.threads.delete(thread_id)
                        threads_to_delete.append(chat_id)
                        logger.info(f"Deleted old thread {thread_id} for chat {chat_id}")
                except Exception as e:
                    logger.error(f"Error cleaning up thread {thread_id}: {str(e)}")
                    threads_to_delete.append(chat_id)
                
                # Rate limiting
                await asyncio.sleep(0.5)
            
            # Remove deleted threads from mapping
            for chat_id in threads_to_delete:
                del self.thread_ids[chat_id]
            
            self._save_thread_ids()
            
        except Exception as e:
            logger.error(f"Error in thread cleanup: {str(e)}")