const chatToggle = document.getElementById('chat-toggle');
const chatPopup = document.getElementById('chat-popup');
const chatOverlay = document.getElementById('chat-overlay');
const closeChat = document.getElementById('close-chat');
const chatInput = document.getElementById('chat-input');
const sendMessage = document.getElementById('send-message');
const chatMessages = document.getElementById('chat-messages');
const chatBody = document.querySelector('.chat-body');

function toggleChat() {
    chatPopup.style.display = chatPopup.style.display === 'none' ? 'flex' : 'none';
    chatOverlay.style.display = chatOverlay.style.display === 'none' ? 'block' : 'none';
    chatToggle.style.display = chatPopup.style.display === 'none' ? 'block' : 'none';
}

function addMessage(sender, text) {
    const message = document.createElement('div');
    message.className = `message ${sender}`;
    message.innerHTML = text;
    chatMessages.appendChild(message);
    chatBody.scrollTop = chatBody.scrollHeight;
}

function handleSendMessage() {
    const message = chatInput.value.trim();
    if (message) {
        addMessage('user', message);
        chatInput.value = '';

        fetch('http://localhost:5000/orchestrator/process_request', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ request: message }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                addMessage('bot', `<p>Error: ${data.error}</p>`);
            } else {
                addMessage('bot', data.response);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            addMessage('bot', '<p>An error occurred while processing the request.</p>');
        });
    }
}

// Event listeners
chatToggle.addEventListener('click', toggleChat);
closeChat.addEventListener('click', toggleChat);
chatOverlay.addEventListener('click', toggleChat);
sendMessage.addEventListener('click', handleSendMessage);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleSendMessage();
});