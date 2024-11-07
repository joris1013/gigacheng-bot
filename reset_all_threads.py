#!/usr/bin/env python3
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from typing import Dict, List
import asyncio

# Import local modules
from settings import Settings
from response_handler import ResponseHandler
from decision_engine import DecisionEngine

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ThreadResetter:
    def __init__(self):
        """Initialize the thread resetter with required components"""
        try:
            # Initialize OpenAI client
            self.client = OpenAI(api_key=Settings.OPENAI_API_KEY)
            
            # Initialize bot components
            self.decision_engine = DecisionEngine()
            self.response_handler = ResponseHandler(self.client, self.decision_engine)
            
            # Setup backup directory
            self.backup_dir = Path("thread_backups")
            self.backup_dir.mkdir(exist_ok=True)
            
            logger.info("ThreadResetter initialized successfully")
            logger.info(f"OpenAI API Key present: {bool(Settings.OPENAI_API_KEY)}")
            logger.info(f"Assistant ID present: {bool(Settings.ASSISTANT_ID)}")
        except Exception as e:
            logger.error(f"Failed to initialize ThreadResetter: {str(e)}")
            raise

    def find_existing_threads(self) -> Dict:
        """Find all existing threads from logs and current session"""
        threads = {}
        try:
            # Check current day's logs
            logs_dir = Path("analysis_logs")
            if logs_dir.exists():
                today = datetime.now().strftime("%Y-%m-%d")
                today_log = logs_dir / today / "analysis.jsonl"
                if today_log.exists():
                    with open(today_log, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                data = json.loads(line)
                                chat_id = data.get('chat_id')
                                if chat_id:
                                    threads[str(chat_id)] = None  # We'll create new threads for these
                            except json.JSONDecodeError:
                                continue

            # Add any threads from current response handler
            if hasattr(self.response_handler, 'thread_ids'):
                threads.update(self.response_handler.thread_ids)

            logger.info(f"Found {len(threads)} existing chat threads")
            return threads

        except Exception as e:
            logger.error(f"Error finding existing threads: {str(e)}")
            return {}

    def backup_current_threads(self, threads: Dict) -> Dict:
        """Backup current thread mappings before reset"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"thread_backup_{timestamp}.json"
            
            # Get current thread mappings
            thread_data = {
                'timestamp': timestamp,
                'threads': threads
            }
            
            # Save backup
            with open(backup_file, 'w') as f:
                json.dump(thread_data, f, indent=2)
            
            logger.info(f"Thread backup saved to {backup_file}")
            return thread_data
            
        except Exception as e:
            logger.error(f"Error backing up threads: {str(e)}")
            return {}

    async def reset_all_threads(self) -> Dict[str, List]:
        """Reset all chat threads and create new ones"""
        results = {
            'success': [],
            'failed': []
        }
        
        try:
            # Find all existing threads
            existing_threads = self.find_existing_threads()
            logger.info(f"Found {len(existing_threads)} threads to reset")
            
            # Backup current threads
            self.backup_current_threads(existing_threads)
            
            # Process each chat
            for chat_id in existing_threads.keys():
                try:
                    # Create new thread
                    new_thread = self.client.beta.threads.create()
                    
                    # Update thread mapping
                    self.response_handler.thread_ids[chat_id] = new_thread.id
                    
                    logger.info(f"Reset thread for chat {chat_id}: New thread ID: {new_thread.id}")
                    results['success'].append({
                        'chat_id': chat_id,
                        'old_thread': existing_threads.get(chat_id, 'Unknown'),
                        'new_thread': new_thread.id
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to reset thread for chat {chat_id}: {str(e)}")
                    results['failed'].append({
                        'chat_id': chat_id,
                        'error': str(e)
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in reset_all_threads: {str(e)}")
            return results

def print_results(results: Dict[str, List]):
    """Print formatted results of the reset operation"""
    print("\nThread Reset Results:")
    print("=" * 50)
    
    print("\nSuccessful Resets:")
    if results['success']:
        for item in results['success']:
            print(f"Chat ID: {item['chat_id']}")
            print(f"Old Thread: {item['old_thread']}")
            print(f"New Thread: {item['new_thread']}")
            print("-" * 30)
    else:
        print("No successful resets")
    
    print("\nFailed Resets:")
    if results['failed']:
        for item in results['failed']:
            print(f"Chat ID: {item['chat_id']}")
            print(f"Error: {item['error']}")
            print("-" * 30)
    else:
        print("No failed resets")

async def main():
    try:
        # Initialize resetter
        resetter = ThreadResetter()
        
        # Confirm with user
        print("\nWARNING: This will reset all chat threads for the bot.")
        print("All conversation history with the OpenAI Assistant will be cleared.")
        response = input("\nDo you want to continue? (y/N): ")
        
        if response.lower() != 'y':
            print("Operation cancelled.")
            return
        
        # Perform reset
        print("\nResetting all threads...")
        results = await resetter.reset_all_threads()
        
        # Print results
        print_results(results)
        
        if results['success'] or results['failed']:
            print("\nDon't forget to restart the bot to apply changes!")
            print("Run these commands:")
            print("pkill -f gigacheng_telegram_bot.py")
            print("./update_bot.sh")
        else:
            print("\nNo threads found to reset. This could mean:")
            print("1. The bot hasn't had any conversations yet")
            print("2. The analysis logs are empty or not accessible")
            print("3. The thread_ids dictionary is empty")
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        print(f"\nError: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())