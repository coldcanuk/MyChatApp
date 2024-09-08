import os
from flask import Flask, render_template, request, jsonify
import openai
import time
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
        # (e.g., based on thread_id existence check)
        if not get_thread(thread_id):
            save_thread(thread_id, conversation)
            print(f"Thread {thread_id} saved after first reply.")
    except Exception as e:
        print(f"Error saving thread after first reply: {e}")


# Save thread after Luna's first reply
def save_thread(thread_id, messages):
    valid_messages = []

    for message in messages:
        if isinstance(message['content'], str):
            valid_messages.append(message)
        else:
            message_content = extract_message_text(message)
            if message_content:
                valid_messages.append(
                    {
                        "role": message['role'], "content": message_content
                    }
                )

    try:
        # Debugging: Print what you're about to save
        print(f"Saving thread with data: {
            json.dumps(
                {
                    'id': thread_id,
                    'messages': valid_messages,
                    'last_updated': str(time.time())
                }, indent=4
            )}"
        )
        # Convert the valid_messages list into a JSON string before saving
        thread_collection.add(
            ids=[thread_id],
            documents=[json.dumps({
                "id": thread_id,
                "messages": valid_messages,
                "last_updated": str(time.time())
            })]
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
        # ChromaDB returns documents in a specific format, adjust accordingly:
        # assuming result['documents'] is the correct field
        for thread in result['documents']:
            if thread['id'] == thread_id:
                return thread["messages"]
        return []  # Return an empty list if the thread is not found
    except Exception as e:
        print(f"Error retrieving thread: {e}")
        return []


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


def process_messages(messages):
    """ Process messages and extract the assistant's response """
    conversation = []
    assistant_message = ""
    for message in messages:
        message_text = extract_message_text(message)
        if message_text.strip():
            conversation.append(
                {"role": message.role, "content": message_text})
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
