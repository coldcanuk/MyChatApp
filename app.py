import os
from flask import Flask, render_template, request, jsonify, session
from openai import OpenAIError, BadRequestError
import openai
import time
import datetime
import chromadb
import traceback
import json


app = Flask(__name__)

# Load OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key:
    print("API key not loaded. Check your environment variable setup.")

assistant_id = os.getenv("ASSISTANT_ID")
if not assistant_id:
    print("Assistant ID not loaded. Check your environment variable setup.")

# Load Session Mgmt key from environment variable
app.secret_key = os.getenv('MCA_SESSION')

# Polling interval (seconds) to wait between run status checks
POLL_INTERVAL = 2

# Connect to a running ChromaDB server
client = chromadb.HttpClient(host='localhost', port=8000)
thread_collection = client.get_or_create_collection("mychat_threads")


# Function to get the current timestamp with milliseconds
def get_current_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


# Helper function to process the messages
def process_messages(messages, user_input=None):
    assistant_message = ""
    conversation = []
    current_time = get_current_timestamp()  # Capture timestamp

    # Add user input first if available
    if user_input:
        conversation.append({
            "role": "user",
            "content": user_input,
            "time_state": "Sent",
            "time_value": current_time
        })

    for message in messages:
        message_text = message['content'] if 'content' in message else ''
        if message['role'] == "assistant":
            assistant_message += message_text
        conversation.append({
            "role": message['role'],
            "content": message_text,
            "time_state": "Sent" if message['role'] == "user" else "Received",
            "time_value": current_time  # Precise timestamp
        })
    return assistant_message, conversation


# Helper function to retrieve token usage
def get_token_usage(completed_run):
    usage = completed_run.get('usage', {})
    total_tokens = usage.get('total_tokens', 'unknown')
    return f"Tokens used: {total_tokens}"


# Helper function to build response
def build_response(assistant_message, token_usage, thread_id):
    return jsonify({
        'response': assistant_message,
        'tokens_used': token_usage,
        'thread_id': thread_id
    }), 200


# Function to create a new thread and run for each user interaction
def create_thread_and_run(user_input):
    try:
        print("Creating a new thread and run...")  # Debugging log
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

    except OpenAIError as e:
        print(f"An OpenAI error occurred: {str(e)}")
        return None


# Function to create a new thread and store it in the session and database
def create_thread():
    try:
        new_thread = openai.beta.threads.create()
        thread_id = new_thread['id']  # Ensure we get the ID from the response
        print(f"New thread created with ID: {thread_id}")

        # Save the thread in session and database
        session['thread_id'] = thread_id
        save_thread(thread_id, [])

        return new_thread
    except Exception as e:
        print(f"Error creating new thread: {str(e)}")
        return None


# Creating a run in an existing thread
def create_run_in_existing_thread(thread_id, user_input):
    try:
        run = openai.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )
        print(f"Run created in thread {thread_id}")
        return run
    except BadRequestError as e:  # Handling thread not found error
        error_message = str(e)
        if "No thread found" in error_message:
            print(f"Thread {thread_id} not found.")
            # Instead of automatically creating a new thread, notify the user
            return {"error": "Thread not found. The selected thread no longer exists."}
        else:
            print(f"Error creating run in thread {thread_id}: {error_message}")
            return None
    except OpenAIError as e:  # Catching other OpenAI API-related errors
        print(f"An OpenAI error occurred: {str(e)}")
        return None


# Function to poll the run until it completes
def wait_for_run_completion(run_id, thread_id):
    WHILE_INTERVAL = 0
    while True:
        try:
            print(f"Polling for run completion... (attempt {WHILE_INTERVAL})")
            run_status = openai.beta.threads.runs.retrieve(
                thread_id=thread_id, run_id=run_id
            )
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
        print("Listing messages in the thread...")  # Debugging log
        messages_response = openai.beta.threads.messages.list(
            thread_id=thread_id)
        print("Messages response:", messages_response)
        return messages_response.data
    except Exception as e:
        print(f"Error listing thread messages: {str(e)}")
        return None


# Updated save_thread to store empty thread at start
def save_thread(thread_id, conversation):
    try:
        current_time = get_current_timestamp()
        updated_thread = {
            "id": thread_id,
            "messages": conversation,
            "last_updated": current_time,
        }

        thread_collection.add(
            ids=[thread_id],
            documents=[json.dumps(updated_thread)]
        )
        print(f"Thread {thread_id} saved.")
    except Exception as e:
        print(f"Error saving thread: {e}")


@app.route('/')
def index():
    return render_template('index.html')


# Loading existing threads from the collection
@app.route('/load_thread/<thread_id>', methods=['GET'])
def load_thread(thread_id):
    try:
        result = thread_collection.get(ids=[thread_id])
        thread_data = result['documents'][0]
        return jsonify(json.loads(thread_data)), 200
    except Exception as e:
        print(f"Error loading thread: {str(e)}")
        return jsonify({'error': 'Thread not found'}), 404


@app.route('/chat', methods=['POST'])
def chat():
    try:
        print("Received a chat request...")  # Debugging log
        data = request.json
        user_input = data.get('message')

        # Check if there's a thread ID in the session
        thread_id = session.get('thread_id')

        if not thread_id:  # No thread, create a new one
            print("No thread found. Creating a new one.")
            thread = create_thread()
            if thread:
                thread_id = thread.id
                session['thread_id'] = thread_id
                print(f"New thread ID: {thread_id}")
        else:
            print(f"Using existing thread ID: {thread_id}")

        # Create a run within the thread
        run = create_run_in_existing_thread(thread_id, user_input)
        if not run:
            return jsonify({'error': 'Failed to interact with assistant'}), 500

        # Wait for the run to complete
        completed_run = wait_for_run_completion(run.id, thread_id)
        if not completed_run:
            return jsonify({'error': 'Run did not complete successfully'}), 500

        messages = list_thread_messages(thread_id)
        if not messages:
            return jsonify({'error': 'No messages found in thread'}), 500

        # Add user input while processing messages
        assistant_message, conversation = process_messages(
            messages, user_input=user_input)

        # Save thread with updated messages
        save_thread(thread_id, conversation)

        token_usage = get_token_usage(completed_run)

        return build_response(assistant_message, token_usage, thread_id)

    except Exception as e:
        print(f"Error occurred: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/get_threads', methods=['GET'])
def get_threads():
    """ API to get all saved threads """
    try:
        result = thread_collection.get()  # Fetch all saved threads
        threads = [json.loads(thread).get('id')
                   for thread in result['documents']]
        return jsonify({'threads': threads}), 200
    except Exception as e:
        print(f"Error retrieving threads: {str(e)}")
        return jsonify({'threads': []}), 500


if __name__ == '__main__':
    app.run(debug=True)
