import os
from flask import Flask, render_template, request, jsonify
import openai
import time
import uuid
import chromadb
import traceback

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

client = chromadb.Client()
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


# Save thread after Luna's first reply
def save_thread(thread_id, messages):
    # Ensure that both ids and documents are passed
    thread_collection.add(
        ids=[thread_id],  # Add the thread_id as the ID
        documents=[{
            "id": thread_id,
            "messages": messages,
            "last_updated": str(time.time())
        }]
    )
    print(f"Thread {thread_id} saved.")


# Retrieve thread by ID
def get_thread(thread_id):
    result = thread_collection.get(id=thread_id)
    if result:
        return result[0]["messages"]
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

        if not user_input:
            return jsonify({'error': 'No message provided'}), 400

        # Create a unique thread ID
        thread_id = str(uuid.uuid4())

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

        # Filter to find the assistant's message and store the entire conversation
        conversation = []
        assistant_message = ""

        # Initialize block counter
        i = 0

        for message in messages:
            message_text = ""
            for block in message.content:
                # Increment block counter
                i += 1

                # Log the block type and content for debugging purposes
                print(f"Row {i}: Processing block: {block}")

                # Safely access the 'text' and its 'value' attributes
                # using object notation;
                try:
                    if hasattr(block, 'type') and block.type == "text":
                        if hasattr(block, 'text') and hasattr(block.text, 'value'):
                            # Extract the value from the text object
                            text_value = block.text.value
                            if isinstance(text_value, str):
                                # Concatenate the valid text value
                                message_text += text_value
                            else:
                                print(
                                    f"Warning: Block's text value is not a string. "
                                    f"Block details: {block}"
                                )
                        else:
                            print(
                                "Warning: Block missing 'text' or 'value' attribute. "
                                "Block details: {}".format(block)
                            )
                    else:
                        print(
                            "Skipping non-text block or invalid block type."
                            "Block details: {}".format(block)
                        )
                except Exception as e:
                    # Print the line number along with the error message
                    print(f"Error occurred on line {traceback.format_exc()}")
                    return jsonify({'error': str(e)}), 500

            # Append the message to the conversation if text was successfully extracted
            if message_text.strip():  # Make sure it's not just whitespace
                conversation.append(
                    {"role": message.role, "content": message_text})

            if message.role == "assistant":
                assistant_message += message_text

        # Save the entire conversation into ChromaDB
        save_thread(thread_id, conversation)

        print("Assistant response:", assistant_message)

        # Get token usage from the run
        token_usage = completed_run.usage
        tokens_used = f"Tokens used: {
            token_usage.total_tokens}" if token_usage else "Tokens used: unknown"

        return jsonify({
            'response': assistant_message,
            'tokens_used': tokens_used,
            # Pass the thread ID back to the front-end for future interactions
            'thread_id': thread_id
        }), 200

    except Exception as e:
        # Print the error and the line where it occurred
        print(f"Error occurred on line {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
