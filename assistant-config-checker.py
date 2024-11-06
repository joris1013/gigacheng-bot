import os
from openai import OpenAI
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AssistantConfigChecker:
    def __init__(self):
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.assistant_id = os.getenv('ASSISTANT_ID')
        
    def check_assistant(self):
        """Check current assistant configuration"""
        try:
            assistant = self.client.beta.assistants.retrieve(self.assistant_id)
            logger.info(f"Current Assistant Configuration:")
            logger.info(f"ID: {assistant.id}")
            logger.info(f"Name: {assistant.name}")
            logger.info(f"Model: {assistant.model}")
            return assistant
        except Exception as e:
            logger.error(f"Error retrieving assistant: {str(e)}")
            raise

    def update_assistant_model(self, new_model="gpt-4-1106-preview"):
        """Update assistant model"""
        try:
            assistant = self.client.beta.assistants.update(
                assistant_id=self.assistant_id,
                model=new_model
            )
            logger.info(f"Successfully updated assistant model to: {new_model}")
            return assistant
        except Exception as e:
            logger.error(f"Error updating assistant: {str(e)}")
            raise

    def create_test_thread(self):
        """Test thread creation"""
        try:
            thread = self.client.beta.threads.create()
            logger.info(f"Successfully created test thread: {thread.id}")
            
            # Create a test message
            message = self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content="Test message"
            )
            
            # Create a test run
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant_id
            )
            
            logger.info(f"Successfully created test run: {run.id}")
            return thread, run
        except Exception as e:
            logger.error(f"Error in test thread creation: {str(e)}")
            raise

if __name__ == "__main__":
    checker = AssistantConfigChecker()
    
    # Check current configuration
    print("\n1. Checking current assistant configuration...")
    current_config = checker.check_assistant()
    
    # Update model if needed
    if current_config.model == "gpt-4o" or current_config.model not in ["gpt-4-1106-preview", "gpt-4", "gpt-3.5-turbo-1106"]:
        print("\n2. Updating assistant model...")
        checker.update_assistant_model()
    
    # Test thread creation
    print("\n3. Testing thread creation...")
    checker.create_test_thread()
