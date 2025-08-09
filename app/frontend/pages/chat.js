// Chat Page

let currentSessionId = null;
let chatMessages = [];

async function renderChat() {
    const { $, api, currentProfile } = window.__APP__;
    const profile = currentProfile();
    
    const container = $('#page-container');
    container.style.padding = '2rem';
    container.style.background = 'rgba(255, 255, 255, 0.95)';
    // Gắn class chuyên dụng cho trang chat để kiểm soát scroll
    container.classList.add('chat-page');
    
    if (!profile) {
        container.innerHTML = `
            <div class="text-center mt-4">
                <i class="fas fa-user-circle" style="font-size: 4rem; color: #667eea;"></i>
                <h2>Chưa chọn hồ sơ sức khỏe</h2>
                <p class="text-muted">Vui lòng chọn hoặc tạo hồ sơ sức khỏe để bắt đầu tư vấn</p>
                <a href="#/profiles" class="btn btn-primary">
                    <i class="fas fa-arrow-right"></i>
                    Đến trang hồ sơ
                </a>
            </div>
        `;
        return;
    }
    
    container.innerHTML = `
        <div class="page-header">
            <h1 class="page-title">
                <i class="fas fa-comments"></i>
                Chat sức khỏe
            </h1>
            <p class="page-subtitle">Hồ sơ: ${profile.profile_name}</p>
        </div>
        
        <div class="card chat-card">
            <div class="card-header">
                <h3 class="card-title">
                    <i class="fas fa-robot"></i>
                    Trợ lý tư vấn sức khỏe
                </h3>
                <small class="text-muted">Hỏi về thực phẩm hoặc chia sẻ tình trạng sức khỏe của bạn</small>
            </div>
            <div class="card-body" style="flex: 1; display: flex; flex-direction: column;">
                <div id="chat-messages" style="flex: 1; overflow-y: auto; margin-bottom: 1rem; padding: 1rem; background: #f8f9fa; border-radius: 8px;">
                    <div class="chat-message bot-message">
                        <div class="message-avatar">
                            <i class="fas fa-robot"></i>
                        </div>
                        <div class="message-content">
                            <strong>Trợ lý sức khỏe</strong>
                            <p>Xin chào! Tôi là chuyên gia tư vấn sức khỏe và dinh dưỡng của bạn. Tôi có thể:</p>
                            <ul>
                                <li><strong>Tư vấn thực phẩm:</strong> Đánh giá mọi loại thực phẩm dựa trên tình trạng sức khỏe của bạn</li>
                                <li><strong>Cập nhật hồ sơ:</strong> Tự động ghi nhận thông tin sức khỏe mới bạn chia sẻ</li>
                                <li><strong>Khuyến nghị cụ thể:</strong> Lượng ăn, cách chế biến, thời điểm phù hợp</li>
                                <li><strong>Thực phẩm đặc biệt:</strong> Tra cứu món ăn địa phương/đặc sản khi cần</li>
                            </ul>
                            <p><em>Ví dụ: "Tôi bị tiểu đường, có nên ăn chuối không?" hoặc "Tôi vừa tăng 2kg trong tháng này"</em></p>
                        </div>
                    </div>
                </div>
                <div id="chat-input-area">
                    <div class="input-group">
                        <input type="text" id="chat-input" class="form-control" placeholder="Nhập tin nhắn của bạn...">
                        <button id="send-button" class="btn btn-primary">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                    </div>
                    <div id="typing-indicator" style="display: none; margin-top: 0.5rem; color: #6c757d;">
                        <small><i class="fas fa-circle-notch fa-spin"></i> Trợ lý đang soạn tin nhắn...</small>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Load existing chat session (retry once if needed)
    await loadChatSession();
    if (!currentSessionId) {
        await new Promise(r => setTimeout(r, 200));
        await loadChatSession();
    }
    
    // Setup event listeners
    setupChatEventListeners();
}

async function loadChatSession() {
    const { api, currentProfile } = window.__APP__;
    const profile = currentProfile();
    
    try {
        // Get existing chat sessions
        const sessions = await api(`/api/profiles/${profile.id}/chats`);
        
        if (sessions.length === 0) {
            // Create new session (correct POST usage)
            const newSession = await api(`/api/profiles/${profile.id}/chats`, {
                method: 'POST'
            });
            currentSessionId = newSession.session_id;
        } else {
            currentSessionId = sessions[0].id;
        }
        
        // Guard: ensure we have a valid session id before requesting messages
        if (!currentSessionId) {
            console.warn('Chat session chưa sẵn sàng. Sẽ thử lại sau.');
            return;
        }
        
        // Load messages for the session
        const messages = await api(`/api/chats/${currentSessionId}/messages`);
        chatMessages = Array.isArray(messages) ? messages : [];
        displayMessages();
        
    } catch (error) {
        console.error('Error loading chat session:', error);
    }
}

function displayMessages() {
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) return;
    
    // Keep the welcome message and add chat history
    const welcomeMessage = messagesContainer.querySelector('.bot-message');
    messagesContainer.innerHTML = '';
    messagesContainer.appendChild(welcomeMessage);
    
    chatMessages.forEach(msg => {
        const messageEl = createMessageElement(msg);
        messagesContainer.appendChild(messageEl);
    });
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function createMessageElement(message) {
    const { create } = window.__APP__;
    const isUser = message.message_type === 'user';
    
    return create('div', { 
        className: `chat-message ${isUser ? 'user-message' : 'bot-message'}`,
        style: `margin-bottom: 1rem; display: flex; ${isUser ? 'justify-content: flex-end;' : ''}`
    }, [
        !isUser ? create('div', { 
            className: 'message-avatar',
            style: 'width: 40px; height: 40px; border-radius: 50%; background: #667eea; color: white; display: flex; align-items: center; justify-content: center; margin-right: 0.5rem; flex-shrink: 0;'
        }, [
            create('i', { className: 'fas fa-robot' })
        ]) : '',
        create('div', { 
            className: 'message-content',
            style: `max-width: 70%; padding: 0.75rem 1rem; border-radius: 18px; ${isUser ? 'background: #667eea; color: white; margin-left: auto;' : 'background: white; border: 1px solid #e9ecef;'}`
        }, [
            !isUser ? create('strong', { style: 'color: #667eea; font-size: 0.875rem;' }, 'Trợ lý sức khỏe') : '',
            create('div', { 
                style: 'white-space: pre-wrap; line-height: 1.4;',
                innerHTML: formatMessageContent(message.content)
            })
        ]),
        isUser ? create('div', { 
            className: 'message-avatar',
            style: 'width: 40px; height: 40px; border-radius: 50%; background: #28a745; color: white; display: flex; align-items: center; justify-content: center; margin-left: 0.5rem; flex-shrink: 0;'
        }, [
            create('i', { className: 'fas fa-user' })
        ]) : ''
    ]);
}

function formatMessageContent(content) {
    // Basic formatting for AI responses
    return content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // Bold
        .replace(/\*(.*?)\*/g, '<em>$1</em>')              // Italic
        .replace(/\n/g, '<br>')                            // Line breaks
        .replace(/(\d+)\.\s/g, '<br>$1. ')                 // Numbered lists
        .replace(/- (.*?)(<br>|$)/g, '<br>• $1$2');        // Bullet points
}

function setupChatEventListeners() {
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    
    if (!chatInput || !sendButton) return;
    
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            e.stopPropagation();
            sendMessage();
        }
    });
    
    sendButton.addEventListener('click', sendMessage);
}

async function sendMessage() {
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const typingIndicator = document.getElementById('typing-indicator');
    const messagesContainer = document.getElementById('chat-messages');
    
    if (!chatInput || !sendButton || !currentSessionId) return;
    
    const message = chatInput.value.trim();
    if (!message) return;
    
    try {
        // Disable input
        chatInput.disabled = true;
        sendButton.disabled = true;
        typingIndicator.style.display = 'block';
        
        // Clear input
        chatInput.value = '';
        
        // Add user message to display
        const userMessage = {
            content: message,
            message_type: 'user',
            timestamp: new Date().toISOString()
        };
        
        const userMessageEl = createMessageElement(userMessage);
        messagesContainer.appendChild(userMessageEl);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Send to API
        const { api } = window.__APP__;
        const response = await api(`/api/chats/${currentSessionId}/messages`, {
            method: 'POST',
            body: JSON.stringify({
                content: message,
                message_type: 'text'
            })
        });
        
        // Add AI response to display
        const aiMessage = {
            content: response.ai_response,
            message_type: 'assistant',
            timestamp: new Date().toISOString()
        };
        
        const aiMessageEl = createMessageElement(aiMessage);
        messagesContainer.appendChild(aiMessageEl);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Update messages array
        chatMessages.push(userMessage, aiMessage);
        
    } catch (error) {
        console.error('Error sending message:', error);
        
        // Show error message
        const errorMessage = {
            content: 'Xin lỗi, có lỗi xảy ra khi xử lý tin nhắn. Vui lòng thử lại.',
            message_type: 'assistant',
            timestamp: new Date().toISOString()
        };
        
        const errorMessageEl = createMessageElement(errorMessage);
        messagesContainer.appendChild(errorMessageEl);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
    } finally {
        // Re-enable input
        chatInput.disabled = false;
        sendButton.disabled = false;
        typingIndicator.style.display = 'none';
        chatInput.focus();
    }
}