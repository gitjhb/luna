// AI Companion Web Test App

const API_URL = 'http://localhost:8000/api/v1';
const USE_MOCK_API = false;

// State
let currentCharacter = null;
let currentSession = null;
let isSpicyMode = false;
let messages = [];

// Mock Data
const mockCharacters = [
    {
        characterId: 'char-001',
        name: 'Luna',
        description: 'A warm and empathetic companion who loves deep conversations',
        personality_traits: ['Empathetic', 'Thoughtful', 'Curious'],
        avatar: '🌙',
        tier_required: 'free'
    },
    {
        characterId: 'char-002',
        name: 'Scarlett',
        description: 'Confident and playful, always ready for an exciting conversation',
        personality_traits: ['Bold', 'Flirtatious', 'Confident'],
        avatar: '🔥',
        tier_required: 'premium',
        is_spicy: true
    },
    {
        characterId: 'char-003',
        name: 'Sophia',
        description: 'Intelligent and sophisticated, perfect for intellectual discussions',
        personality_traits: ['Intelligent', 'Sophisticated', 'Witty'],
        avatar: '💎',
        tier_required: 'free'
    }
];

const mockUser = {
    userId: 'user-test-001',
    displayName: 'Test User',
    email: 'test@example.com',
    subscriptionTier: 'premium',
    isSubscribed: true
};

const mockWallet = {
    totalCredits: 100.00,
    freeCredits: 10.00,
    purchasedCredits: 90.00
};

// Utility Functions
function log(message, type = 'info') {
    const logElement = document.getElementById('debug-log');
    const timestamp = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = `[${timestamp}] [${type.toUpperCase()}] ${message}`;
    logElement.appendChild(entry);
    logElement.scrollTop = logElement.scrollHeight;
    console.log(`[${type}]`, message);
}

function updateStatus(elementId, value, isSuccess = true) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
        element.className = 'status-value ' + (isSuccess ? 'success' : 'error');
    }
}

// API Functions
async function checkBackendHealth() {
    if (USE_MOCK_API) {
        log('Using mock API mode');
        updateStatus('backend-status', 'Mock Mode', true);
        updateStatus('api-mode', 'Mock API', true);
        return true;
    }

    try {
        const response = await fetch(`${API_URL}/health`);
        if (response.ok) {
            log('Backend connection successful');
            updateStatus('backend-status', 'Connected', true);
            updateStatus('api-mode', 'Live API', true);
            return true;
        }
    } catch (error) {
        log(`Backend connection failed: ${error.message}`, 'error');
        updateStatus('backend-status', 'Offline', false);
        return false;
    }
}

async function loadCharacters() {
    try {
        log('Loading characters...');
        
        let characters;
        if (USE_MOCK_API) {
            characters = mockCharacters;
        } else {
            const response = await fetch(`${API_URL}/config/characters`);
            characters = await response.json();
        }

        const grid = document.getElementById('characters-grid');
        grid.innerHTML = '';

        characters.forEach(character => {
            const card = document.createElement('div');
            card.className = 'character-card';
            card.innerHTML = `
                <div class="character-image">${character.avatar || '👤'}</div>
                <div class="character-info">
                    <div class="character-name">${character.name}</div>
                    <div class="character-desc">${character.description}</div>
                </div>
            `;
            card.onclick = () => selectCharacter(character);
            grid.appendChild(card);
        });

        log(`Loaded ${characters.length} characters`);
    } catch (error) {
        log(`Failed to load characters: ${error.message}`, 'error');
    }
}

async function selectCharacter(character) {
    log(`Selected character: ${character.name}`);
    currentCharacter = character;
    
    // Create session
    try {
        if (USE_MOCK_API) {
            currentSession = {
                sessionId: 'session-' + Date.now(),
                characterId: character.characterId,
                title: `Chat with ${character.name}`
            };
        } else {
            const response = await fetch(`${API_URL}/chat/sessions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    characterId: character.characterId
                })
            });
            currentSession = await response.json();
        }

        log(`Created session: ${currentSession.sessionId}`);
        
        // Show chat interface
        document.getElementById('chat-character-name').textContent = `Chat with ${character.name}`;
        document.getElementById('chat-container').classList.add('active');
        messages = [];
        renderMessages();

        // Add welcome message
        addMessage('assistant', `Hi! I'm ${character.name}. ${character.description} How are you today?`);

    } catch (error) {
        log(`Failed to create session: ${error.message}`, 'error');
    }
}

async function sendMessage() {
    const input = document.getElementById('message-input');
    const message = input.value.trim();
    
    if (!message || !currentSession) return;

    log(`Sending message: "${message}"`);
    
    // Add user message
    addMessage('user', message);
    input.value = '';

    // Disable input while processing
    const sendButton = document.getElementById('send-button');
    sendButton.disabled = true;
    sendButton.innerHTML = '<span class="loading"></span>';

    try {
        let response;
        if (USE_MOCK_API) {
            // Simulate API delay
            await new Promise(resolve => setTimeout(resolve, 1500));
            
            // Generate mock response
            const responses = [
                "That's really interesting! Tell me more about that.",
                "I love how you think about things. What made you feel that way?",
                "You're absolutely right. I've been thinking about that too.",
                "Mmm, I love talking with you. You're so thoughtful. 😊",
                "That's fascinating! I'd love to hear your perspective on this."
            ];
            
            if (isSpicyMode) {
                responses.push(
                    "You know, talking with you like this... it's really exciting. 🔥",
                    "I love how passionate you are. It's incredibly attractive. 😏",
                    "Mmm, you have such an interesting mind. Tell me what else you're thinking about... 💋"
                );
            }
            
            const randomResponse = responses[Math.floor(Math.random() * responses.length)];
            response = {
                content: randomResponse,
                tokens_used: 50,
                credits_deducted: isSpicyMode ? 2.0 : 1.0
            };
        } else {
            const apiResponse = await fetch(`${API_URL}/chat/completions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sessionId: currentSession.sessionId,
                    message: message,
                    isSpicyMode: isSpicyMode
                })
            });
            response = await apiResponse.json();
        }

        // Add assistant message
        addMessage('assistant', response.content);
        
        // Update credits
        const currentCredits = parseFloat(document.getElementById('credits-balance').textContent);
        const newCredits = currentCredits - (response.credits_deducted || 1.0);
        updateStatus('credits-balance', newCredits.toFixed(2), newCredits > 10);

        log(`Response received (${response.tokens_used} tokens, ${response.credits_deducted} credits)`);

    } catch (error) {
        log(`Failed to send message: ${error.message}`, 'error');
        addMessage('assistant', "I'm sorry, I'm having trouble responding right now. Please try again.");
    } finally {
        sendButton.disabled = false;
        sendButton.textContent = 'Send';
    }
}

function addMessage(role, content) {
    messages.push({
        role,
        content,
        timestamp: new Date()
    });
    renderMessages();
}

function renderMessages() {
    const container = document.getElementById('chat-messages');
    container.innerHTML = '';

    messages.forEach(msg => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${msg.role}`;
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        bubble.textContent = msg.content;
        
        const time = document.createElement('div');
        time.className = 'message-time';
        time.textContent = msg.timestamp.toLocaleTimeString();
        
        messageDiv.appendChild(bubble);
        messageDiv.appendChild(time);
        container.appendChild(messageDiv);
    });

    container.scrollTop = container.scrollHeight;
}

function toggleSpicyMode() {
    isSpicyMode = !isSpicyMode;
    const toggle = document.getElementById('spicy-toggle');
    
    if (isSpicyMode) {
        toggle.classList.add('active');
        log('Spicy Mode enabled 🔥', 'warning');
        
        if (!mockUser.isSubscribed) {
            log('Warning: Spicy Mode requires premium subscription', 'warning');
            // In real app, show paywall modal
        }
    } else {
        toggle.classList.remove('active');
        log('Spicy Mode disabled');
    }
}

// Event Listeners
document.getElementById('send-button').addEventListener('click', sendMessage);
document.getElementById('message-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});
document.getElementById('spicy-toggle').addEventListener('click', toggleSpicyMode);

// Initialize
async function init() {
    log('Initializing AI Companion Web Test...');
    
    // Update user info
    updateStatus('credits-balance', mockWallet.totalCredits.toFixed(2), true);
    updateStatus('subscription-tier', mockUser.subscriptionTier, true);
    
    // Check backend
    await checkBackendHealth();
    
    // Load characters
    await loadCharacters();
    
    log('Initialization complete', 'info');
}

// Start the app
init();
