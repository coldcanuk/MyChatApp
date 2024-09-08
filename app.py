import os
from flask import Flask, render_template, request, jsonify
import openai
import time
import datetime
import uuid
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

# Polling interval (seconds) to wait between run status checks
POLL_INTERVAL = 2

# Connect to a running ChromaDB server
client = chromadb.HttpClient(host='localhost', port=8000)
thread_collection = client.get_or_create_collection("mychat_threads")


# Function to get the current timestamp with milliseconds
def get_current_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


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
            # Debugging log
            print(f"Polling for run completion... (attempt {WHILE_INTERVAL})")
            run_status = openai.beta.threads.runs.retrieve(
                thread_id=thread_id, run_id=run_id)
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
        messages_response = openai.beta.threads.messages.list(
            thread_id=thread_id)
        print("Messages response:", messages_response)
        return messages_response.data
    except Exception as e:
        print(f"Error listing thread messages: {str(e)}")
        return None


# Retrieve all saved threads
def get_all_threads():
    try:
        threads = thread_collection.get()  # Fetch all saved threads
        # Return thread ids for sidebar
        return [thread['id'] for thread in threads]
    except Exception as e:
        print(f"Error retrieving threads: {e}")
        return []


# Save thread after the first reply
def save_thread_after_first_reply(thread_id, conversation):
    try:
        # Only save the thread if it's not already saved
        if not get_thread(thread_id):
            # Ensure conversation has valid messages before saving
            if conversation and isinstance(conversation, list):
                save_thread(thread_id, conversation)
                print(f"Thread {thread_id} saved after first reply.")
            else:
                print(f"Invalid conversation data for thread {
                      thread_id}. Not saving.")
    except Exception as e:
        print(f"Error saving thread after first reply: {e}")


# Save thread with milliseconds
def save_thread(thread_id, new_messages, is_new_thread=False):
    try:
        if not new_messages or not isinstance(new_messages, list):
            print(f"Invalid or empty messages. Cannot save thread {
                  thread_id}.")
            return  # Don't save if messages are invalid

        # Get the current timestamp with milliseconds
        current_time = get_current_timestamp()

        # Check if the thread already exists
        existing_thread = get_thread(thread_id)

        if existing_thread:
            # Ensure existing thread has a valid structure
            if "messages" in existing_thread and isinstance(
                existing_thread["messages"], list
            ):
                # Append new messages to the existing thread
                existing_messages = existing_thread["messages"]
                # Ensure each new message has time_state and time_value
                for message in new_messages:
                    if "role" in message and "content" in message:
                        # Add time_state and time_value if missing
                        message.setdefault(
                            "time_state", "Sent"
                            if message["role"] == "user" else "Received"
                        )
                        message.setdefault("time_value", current_time)
                        existing_messages.append(message)
                updated_thread = {
                    "id": thread_id,
                    "messages": existing_messages,
                    # Keep original creation time
                    "created": existing_thread["created"],
                    # Update timestamp for the last interaction
                    "last_updated": current_time
                }
            else:
                print(f"Invalid existing thread structure for thread {
                      thread_id}.")
                return
        else:
            # Ensure each new message has time_state and time_value
            for message in new_messages:
                if "role" in message and "content" in message:
                    message.setdefault(
                        "time_state", "Sent" if message["role"] == "user" else "Received"
                    )
                    message.setdefault("time_value", current_time)

            # Create a new thread with the initial messages
            updated_thread = {
                "id": thread_id,
                "messages": new_messages,
                "created": current_time,  # Set the creation time on first save
                "last_updated": current_time
            }

        # Save or update the thread in ChromaDB
        thread_collection.add(
            ids=[thread_id],
            documents=[json.dumps(updated_thread)]
        )
        print(f"Thread {thread_id} saved.")
    except Exception as e:
        print(f"Error saving thread: {e}")


# Retrieve thread by ID
def get_thread(thread_id):
    try:
        print(f"Thread collection data: {
              json.dumps(thread_collection.get(), indent=4)}")
        result = thread_collection.get()  # Fetch all saved threads

        # Assuming 'documents' contains the serialized thread data
        for thread in result['documents']:
            thread_data = json.loads(thread)  # Deserialize the document
            if thread_data['id'] == thread_id:
                return thread_data  # Return the full thread with messages and timestamps
        return None  # Return None if the thread is not found
    except Exception as e:
        print(f"Error retrieving thread: {e}")
        return None


# Delete a thread
def delete_thread(thread_id):
    thread_collection.delete(ids=[thread_id])
    print(f"Thread {thread_id} deleted.")


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

        if not validate_input(user_input):
            return jsonify({'error': 'No message provided'}), 400

        # Check if it's a new thread or a continuation
        # Get thread_id if continuing, else create a new one
        thread_id = data.get('thread_id') or str(uuid.uuid4())

        run = create_and_run_thread(user_input)
        if not run:
            return jsonify({'error': 'Failed to interact with assistant'}), 500

        completed_run = wait_for_completion(run)
        if not completed_run:
            return jsonify({'error': 'Run did not complete successfully'}), 500

        messages = list_thread_messages(completed_run.thread_id)
        if not messages:
            return jsonify({'error': 'No messages found in thread'}), 500

        assistant_message, conversation = process_messages(messages)

        # Save thread after first Luna response
        save_thread_after_first_reply(thread_id, conversation)

        print("Assistant response:", assistant_message)

        token_usage = get_token_usage(completed_run)

        return build_response(assistant_message, token_usage, thread_id)

    except Exception as e:
        print(f"Error occurred on line {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/get_threads', methods=['GET'])
def get_threads():
    """ API to get all saved threads """
    threads = get_all_threads()
    return jsonify({'threads': threads}), 200


def validate_input(user_input):
    """ Validate if the user input is present """
    return bool(user_input)


def create_and_run_thread(user_input):
    """ Create a thread and start the run """
    try:
        return create_thread_and_run(user_input)
    except Exception as e:
        print(f"Failed to create thread: {e}")
        return None


def wait_for_completion(run):
    """ Poll for the run's completion """
    try:
        return wait_for_run_completion(run.id, run.thread_id)
    except Exception as e:
        print(f"Failed to complete run: {e}")
        return None


# Update the process_messages function to include milliseconds
def process_messages(messages):
    conversation = []
    assistant_message = ""
    # Capture the time when Luna's reply is processed
    current_time = get_current_timestamp()

    for message in messages:
        message_text = extract_message_text(message)
        if message_text.strip():
            time_state = "Sent" if message.role == "user" else "Received"
            conversation.append({
                "role": message.role,
                "content": message_text,
                "time_state": time_state,
                "time_value": current_time
            })
        if message.role == "assistant":
            assistant_message += message_text
    return assistant_message, conversation


def extract_message_text(message):
    """ Extract text from message content blocks """
    message_text = ""
    i = 0  # Block counter
    for block in message.content:
        i += 1
        print(f"Row {i}: Processing block: {block}")
        message_text += process_block(block)
    return message_text


def process_block(block):
    """ Safely process a block to extract text """
    try:
        if hasattr(block, 'type') and block.type == "text":
            if hasattr(block, 'text') and hasattr(block.text, 'value'):
                text_value = block.text.value
                if isinstance(text_value, str):
                    return text_value
                else:
                    print(
                        f"Warning: Block's text value is not a string."
                        f"Block details: {block}"
                    )
            else:
                print(
                    f"Warning: Block missing 'text' or 'value' attribute."
                    f"Block details: {block}"
                )
        else:
            print(
                f"Skipping non-text block or invalid block type. Block details: {block}")
        return ""

    except Exception:
        print(f"Error occurred on line {traceback.format_exc()}")
        return ""


def get_token_usage(completed_run):
    """ Retrieve token usage information """
    token_usage = completed_run.usage
    return (
        f"Tokens used: {token_usage.total_tokens}"
        if token_usage else "Tokens used: unknown"
    )


def build_response(assistant_message, token_usage, thread_id):
    """ Build the final response to return to the client """
    return jsonify({
        'response': assistant_message,
        'tokens_used': token_usage,
        'thread_id': thread_id
    }), 200


if __name__ == '__main__':
    app.run(debug=True)
