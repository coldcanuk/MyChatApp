// Global variable to store the current thread ID
let currentThreadId = null;

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
    .then(response => response.json())
    .then(data => {
        const threadsList = document.getElementById('threads-list');
        threadsList.innerHTML = ''; // Clear placeholder threads

        if (!data.threads || data.threads.length === 0) {
            threadsList.innerText = 'No threads available'; // Display message if no threads found
            console.log('No threads found.');
            return;
        }

        console.log("Retrieved threads:", data.threads); // Debugging log

        // Populate saved threads list
        data.threads.forEach((threadId, index) => {
            const threadItem = document.createElement('li');
            threadItem.innerText = `${index + 1}. Thread ${threadId}`;
            threadItem.addEventListener('click', () => loadThread(threadId));
            threadsList.appendChild(threadItem);
        });
    })
    .catch(err => {
        console.error('Error loading threads:', err);
        const threadsList = document.getElementById('threads-list');
        threadsList.innerText = 'Error loading threads';
    });
}


function sendMessage(message) {
    const requestData = {
        message: message,
        thread_id: currentThreadId // Ensure the current thread ID is sent
    };

    fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            addMessageToChat(data.response, 'left');
            document.getElementById('token-usage').innerText = data.tokens_used;

            // If this is the first message, set the thread ID for the session
            if (!currentThreadId) {
                currentThreadId = data.thread_id;
            }

            updateSavedThreads(currentThreadId);
        }
    })
    .catch(err => {
        console.error('Error sending message:', err);
        alert('Error sending message. Please try again.');
    });
}

// Function to update the saved threads list
function updateSavedThreads(threadId) {
    const threadsList = document.getElementById('threads-list');
    const existingThread = [...threadsList.children].find(item => item.innerText.includes(threadId));

    if (!existingThread) {
        const newThreadItem = document.createElement('li');
        newThreadItem.innerText = `Thread ${threadId}`;
        newThreadItem.addEventListener('click', () => loadThread(threadId));
        threadsList.appendChild(newThreadItem);  // Add new thread to the list
    }
}

function loadThread(threadId) {
    console.log(`Loading thread: ${threadId}`);
    fetch(`/load_thread/${threadId}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        const chatBox = document.getElementById('chat-box');
        chatBox.innerHTML = '';  // Clear the chat box

        data.messages.forEach(message => {
            const align = message.role === 'user' ? 'right' : 'left';
            addMessageToChat(message.content, align);  // Load each message into the chat box
        });
    })
    .catch(err => {
        console.error('Error loading thread:', err);
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
