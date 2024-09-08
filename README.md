
# MyChatApp

**MyChatApp** is a web-based chat application that allows users to interact with the OpenAI-powered assistant, Luna. Users can start new threads, re-engage old conversations, and view saved chat threads from previous sessions. Built with Flask, OpenAI API, and ChromaDB for thread management, this application enables seamless chat-based interaction.

## Features

- **Start New Threads**: Users can initiate new conversations with Luna.
- **Re-engage Previous Conversations**: Users can select saved threads from the sidebar and continue their chat from where they left off.
- **Session Management**: Each session maintains its thread history, allowing users to continue their chats across sessions.
- **Real-time Assistant Interaction**: Powered by OpenAI, MyChatApp responds intelligently to user inputs within each conversation thread.

## Requirements

### Python Version:
- Python 3.10+

### Install Dependencies:

1. Install required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

### Environment Variables:

Ensure the following environment variables are set before running the application:

- `OPENAI_API_KEY`: Your OpenAI API key to interact with the assistant.
- `ASSISTANT_ID`: The OpenAI assistant ID used for conversation.
- `MCA_SESSION`: Secret key for session management.

You can set these in a `.env` file or export them directly:

```bash
export OPENAI_API_KEY=your_openai_api_key
export ASSISTANT_ID=your_assistant_id
export MCA_SESSION=your_secret_key
```

## Installation

1. **Clone the repository**:

    ```bash
    git clone https://github.com/coldcanuk/MyChatApp.git
    cd MyChatApp
    ```

2. **Create a virtual environment** (optional but recommended):

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

4. **Set up environment variables** as explained above.

5. **Run the application**:

    ```bash
    python3 app.py
    ```

    The application will be served on `http://127.0.0.1:5000`.

## Usage

### Start New Conversation

- On the main page, simply type a message to start a new thread.
- The thread will automatically be created, and you can chat with Luna, the OpenAI-powered assistant.

### Continue Previous Conversation

- Select any previous thread from the **Saved Threads** section on the sidebar to continue the conversation.

### Start a New Session

- If no thread is active in the current session, the application will automatically create a new thread for you to start chatting.

## Project Structure

```
MyChatApp/
│
├── app.py                  # Main Flask app code
├── requirements.txt         # List of dependencies
├── templates/
│   └── index.html           # Main HTML file for the UI
├── static/
│   ├── CSS/
│   │   └── styles.css       # Custom styles for the app
│   └── js/
│       └── chat.js          # JavaScript code for front-end chat interactions
├── README.md                # Documentation file (you are here!)
└── .env                     # Environment variables (optional)
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a pull request

## License

Distributed under the MIT License. See `LICENSE` for more information.

---

Happy chatting with Luna! 🚀
