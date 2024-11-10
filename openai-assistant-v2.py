import openai
import time
from typing import Optional

class AssistantManager:
    def __init__(self, api_key: str):
        """Initialize the OpenAI client with your API key."""
        self.client = openai.OpenAI(
            api_key=api_key,
            default_headers={
                "OpenAI-Beta": "assistants=v2"
            }
        )
        self.assistant_id = "asst_KDSKd8UOrujz5oixKtXykQfu"

    def create_thread_and_run(self, user_input: str) -> tuple[str, str]:
        """Create a thread and run in one go."""
        # Create thread with initial message
        thread = self.client.beta.threads.create()

        # Add the first message
        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
        )
        
        # Create run
        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant_id,
        )
        
        return thread.id, run.id

    def get_response(self, thread_id: str, run_id: str) -> Optional[str]:
        """Wait for run to complete and get response."""
        while True:
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )

            if run.status == "completed":
                messages = self.client.beta.threads.messages.list(
                    thread_id=thread_id,
                    order="desc",  # Get most recent first
                    limit=1  # Only get the latest message
                )
                
                # Get the latest assistant message
                if messages.data:
                    message = messages.data[0]
                    if message.role == "assistant":
                        return message.content[0].text.value
                return None

            elif run.status == "failed":
                raise Exception(f"Run failed: {run.last_error}")
            
            elif run.status == "requires_action":
                # Handle any required tool calls
                required_actions = run.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []
                
                for action in required_actions:
                    # Here you can handle specific tool outputs if needed
                    pass
                
                if tool_outputs:
                    self.client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread_id,
                        run_id=run_id,
                        tool_outputs=tool_outputs
                    )

            time.sleep(1)

    def send_message(self, thread_id: str, message: str) -> Optional[str]:
        """Send a message in an existing thread and get the response."""
        # Add the message to the thread
        self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )
        
        # Create a run
        run = self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=self.assistant_id,
        )
        
        # Get the response
        return self.get_response(thread_id, run.id)

def main():
    # Replace with your API key
    api_key = "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"
    
    try:
        print("Initializing OpenAI Assistant (v2)...")
        manager = AssistantManager(api_key)
        
        # Start conversation
        user_input = input("\nEnter your message (or 'quit' to exit): ")
        if user_input.lower() == 'quit':
            return
        
        # Create thread and get first response
        thread_id, run_id = manager.create_thread_and_run(user_input)
        print("Waiting for response...")
        
        response = manager.get_response(thread_id, run_id)
        if response:
            print("\nAssistant:", response)
        
        # Continue conversation
        while True:
            user_input = input("\nEnter your message (or 'quit' to exit): ")
            if user_input.lower() == 'quit':
                break
            
            print("Waiting for response...")
            response = manager.send_message(thread_id, user_input)
            
            if response:
                print("\nAssistant:", response)
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        if hasattr(e, 'response'):
            print("Full error details:", e.response.text if hasattr(e.response, 'text') else e.response)

if __name__ == "__main__":
    main()