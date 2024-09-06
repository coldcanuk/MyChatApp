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

function startNewThread() {
    // Clear the chat box
    const chatBox = document.getElementById('chat-box');
    chatBox.innerHTML = '';

    // Reset other elements or states if needed
    // 1. Reset token usage display
    document.getElementById('token-usage').innerText = "Tokens used: 0";

    // Perhaps log the event or notify the user
    console.log("New thread started!");
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
