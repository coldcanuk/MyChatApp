import os
from flask import Flask, render_template, request, jsonify
import openai
import time

app = Flask(__name__)

# Load OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key:
    print("API key not loaded. Check your environment variable setup.")

assistant_id = os.getenv("ASSISTANT_ID")
if not assistant_id:
    print("Assistant ID not loaded. Check your environment variable setup.")

# Polling interval (seconds) to wait between run status checks
POLL_INTERVAL = 2

# Function to create a new thread and run for each user interaction
def create_thread_and_run(user_input):
    try:
        print("Attempting to create a new thread and run...")  # Debugging log
        run = openai.beta.threads.create_and_run(
            assistant_id=assistant_id,
            thread={
                "messages": [
                    {"role": "user", "content": user_input}
                ]
            }
        )
        print("Run object created:", run)
        return run

    except Exception as e:
        print(f"Error creating thread and run: {str(e)}")
        return None

# Function to poll the run until it completes
def wait_for_run_completion(run_id, thread_id):
    WHILE_INTERVAL = 0
    while True:
        try:
            print(f"Polling for run completion... (attempt {WHILE_INTERVAL})")  # Debugging log
            run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
            print(f"Current run status: {run_status.status}")

            if run_status.status == "completed":
                print("Run completed!")
                return run_status

            time.sleep(POLL_INTERVAL)
            WHILE_INTERVAL += 1

        except Exception as e:
            print(f"Error while polling run status: {str(e)}")
            return None

# Function to list all messages in the thread after the run completes
def list_thread_messages(thread_id):
    try:
        print("Attempting to list messages in the thread...")  # Debugging log
        messages_response = openai.beta.threads.messages.list(thread_id=thread_id)
        print("Messages response:", messages_response)
        return messages_response.data
    except Exception as e:
        print(f"Error listing thread messages: {str(e)}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        print("Received a chat request...")  # Debugging log
        data = request.json
        user_input = data.get('message')
        print(f"User input: {user_input}")

        if not user_input:
            return jsonify({'error': 'No message provided'}), 400

        # Create a thread and run to chat with Luna
        run = create_thread_and_run(user_input)

        if not run:
            return jsonify({'error': 'Failed to interact with assistant'}), 500

        # Poll for the run's completion
        completed_run = wait_for_run_completion(run.id, run.thread_id)

        if not completed_run:
            return jsonify({'error': 'Run did not complete successfully'}), 500

        # List all messages in the thread
        messages = list_thread_messages(completed_run.thread_id)

        if not messages:
            return jsonify({'error': 'No messages found in thread'}), 500

        # Filter to find the assistant's message
        assistant_message = ""
        for message in messages:
            if message.role == "assistant":  # Check if the message is from Luna
                for block in message.content:
                    if block.type == "text":  # Ensure it's a text block
                        assistant_message += block.text.value

        print("Assistant response:", assistant_message)

        # Get token usage from the run
        token_usage = completed_run.usage
        if token_usage:
            tokens_used = f"Tokens used: {token_usage.total_tokens}"
        else:
            tokens_used = "Tokens used: unknown"

        return jsonify({
            'response': assistant_message,
            'tokens_used': tokens_used
        }), 200

    except Exception as e:
        print("Error occurred:", str(e))
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
