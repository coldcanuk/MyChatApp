document.getElementById('send-btn').addEventListener('click', function () {
    const message = document.getElementById('message-input').value;
    if (message) {
        addMessageToChat(message, 'right');  // Immediately add user's message
        document.getElementById('message-input').value = '';  // Clear input field
        sendMessage(message);  // Then send the message to the server
    }
});

document.getElementById('message-input').addEventListener('keypress', function (event) {
    if (event.key === "Enter") {
        event.preventDefault();
        const message = document.getElementById('message-input').value;
        if (message) {
            addMessageToChat(message, 'right');  // Immediately add user's message
            document.getElementById('message-input').value = '';  // Clear input field
            sendMessage(message);  // Then send the message to the server
        }
    }
});

document.getElementById('message-input').addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && e.shiftKey) {
        const cursorPosition = this.selectionStart;
        this.value = this.value.substring(0, cursorPosition) + '\n' + this.value.substring(cursorPosition);
        this.selectionStart = this.selectionEnd = cursorPosition + 1;
        e.preventDefault();
    }
});

document.getElementById('new-thread-btn').addEventListener('click', function() {
    startNewThread();
});

document.addEventListener('DOMContentLoaded', function () {
    loadSavedThreads();  // Load threads on page load
});

function loadSavedThreads() {
    fetch('/get_threads', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to fetch threads');
        }
        return response.json();
    })
    .then(data => {
        const threadsList = document.getElementById('threads-list');
        threadsList.innerHTML = '';  // Clear placeholder threads

        if (!data.threads || data.threads.length === 0) {
            threadsList.innerText = 'No threads available';  // Display message if no threads found
            console.log('No threads found.');
            return;
        }

        console.log("Retrieved threads:", data.threads);  // Debugging log to check thread IDs

        data.threads.forEach(threadId => {
            const threadItem = document.createElement('li');
            // Adding a simple message for now. You can adjust the format.
            threadItem.innerText = `Thread ${threadId}`;
            threadItem.addEventListener('click', () => loadThread(threadId));  // Load thread on click
            threadsList.appendChild(threadItem);
        });
    })
    .catch(err => {
        console.error('Error loading threads:', err);
        const threadsList = document.getElementById('threads-list');
        threadsList.innerText = 'Error loading threads';  // Display error message in the list
    });
}

function startNewThread() {
    // Clear the chat box and initiate a new thread
    const chatBox = document.getElementById('chat-box');
    chatBox.innerHTML = '';

    // Clear the token usage and notify of new thread creation
    document.getElementById('token-usage').innerText = "Tokens used: 0";
    console.log("New thread started!");

    // Optionally, you can create a placeholder for the new thread here if needed
}

function sendMessage(message) {
    fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: message })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            addMessageToChat(data.response, 'left');  // Add Luna's response
            document.getElementById('token-usage').innerText = data.tokens_used;
        }
    })
    .catch(err => {
        console.error('Error sending message:', err);
        alert('Error sending message. Please try again.');
    });
}

function addMessageToChat(message, align) {
    const chatBox = document.getElementById('chat-box');
    const messageDiv = document.createElement('div');
    messageDiv.className = align === 'right' ? 'right-message' : 'left-message';  // Use correct alignment classes
    messageDiv.innerText = message;
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;  // Auto-scroll to the bottom
}

function loadThread(threadId) {
    console.log(`Loading thread: ${threadId}`);
    // Logic to fetch and load the conversation with the given threadId
    // You'll need to implement backend handling for this based on how you stored threads
}

document.getElementById('theme-toggle').addEventListener('change', function () {
    if (this.checked) {
        document.body.classList.replace('light-mode', 'dark-mode');
    } else {
        document.body.classList.replace('dark-mode', 'light-mode');
    }
});

// Expandable Assistants
const assistantsToggle = document.getElementById('assistants-toggle');
const assistantsList = document.getElementById('assistants-list');
assistantsToggle.addEventListener('click', function () {
    assistantsList.classList.toggle('collapsed');
    assistantsToggle.innerHTML = assistantsList.classList.contains('collapsed') ?
        'Saved Assistants &#9656;' : 'Saved Assistants &#9662;';
});

// Expandable Chats
const chatsToggle = document.getElementById('chats-toggle');
const chatsList = document.getElementById('threads-list');
chatsToggle.addEventListener('click', function () {
    chatsList.classList.toggle('collapsed');
    chatsToggle.innerHTML = chatsList.classList.contains('collapsed') ?
        'Saved Threads &#9656;' : 'Saved Threads &#9662;';
});

// Textarea auto-growth
const textarea = document.getElementById('message-input');
textarea.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = `${Math.min(this.scrollHeight, 100)}px`;
});

// Helper function to format the timestamp (if you want to display last_updated or any time info)
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
}
