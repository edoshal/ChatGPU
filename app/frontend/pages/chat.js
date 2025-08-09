// Chat Page

let currentSessionId = null;
let chatMessages = [];

function resizeChatLayout() {
    const card = document.querySelector('.chat-card');
    const cardBody = card ? card.querySelector('.card-body') : null;
    const messages = document.getElementById('chat-messages');
    const inputArea = document.getElementById('chat-input-area');
    if (!cardBody || !messages || !inputArea) return;

    // Tính chiều cao còn lại dựa trên viewport để luôn nhìn thấy input
    const bodyTop = cardBody.getBoundingClientRect().top;
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
    const inputHeight = inputArea.offsetHeight;
    const verticalPadding = 24; // buffer
    const available = Math.max(140, viewportHeight - bodyTop - inputHeight - verticalPadding);

    messages.style.height = `${available}px`;
    messages.style.maxHeight = `${available}px`;
}

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
        <div class="card-header">
            <h3 class="card-title">
                <i class="fas fa-robot"></i>
                Trợ lý tư vấn sức khỏe
            </h3>
            <small class="text-muted">Hỏi về thực phẩm hoặc chia sẻ tình trạng sức khỏe của bạn</small>
        </div>
        <div class="card-body" style="flex: 1; display: flex; flex-direction: column; height: calc(100% - 30px);">
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
                <div id="image-preview" style="display: none; margin-bottom: 0.5rem;">
                    <div style="position: relative; display: inline-block;">
                        <img id="preview-image" style="max-width: 200px; max-height: 150px; border-radius: 8px; border: 1px solid #ddd;">
                        <button id="remove-image" style="position: absolute; top: -8px; right: -8px; background: #dc3545; color: white; border: none; border-radius: 50%; width: 24px; height: 24px; font-size: 12px; cursor: pointer;" type="button">×</button>
                    </div>
                </div>
                <div id="chat-form" class="input-group">
                    <input type="text" id="chat-input" class="form-control" placeholder="Nhập tin nhắn của bạn..." autocomplete="off">
                    <input type="file" id="image-upload" accept="image/*" style="display: none;">
                    <button id="image-button" class="btn btn-secondary" title="Tải ảnh thực phẩm" type="button">
                        <i class="fas fa-camera"></i>
                    </button>
                    <button id="send-button" class="btn btn-primary" type="button">
                        <i class="fas fa-paper-plane"></i>
                    </button>
                </div>
                <div id="typing-indicator" style="display: none; margin-top: 0.5rem; color: #6c757d;">
                    <small><i class="fas fa-circle-notch fa-spin"></i> Trợ lý đang soạn tin nhắn...</small>
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

    // Debug log
    console.log('Chat input element:', document.getElementById('chat-input'));
    console.log('Send button element:', document.getElementById('send-button'));
    console.log('Image button element:', document.getElementById('image-button'));

    // Resize layout để bảo đảm ô nhập luôn hiển thị
    resizeChatLayout();
    window.addEventListener('resize', resizeChatLayout);
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
    const isUser = (message.role === 'user') || (message.message_type === 'user'); // fallback cũ
    const hasImage = message.metadata && message.metadata.has_image;

    const contentChildren = [];

    // Image (nếu có)
    if (hasImage && message.metadata.image_data) {
        contentChildren.push(
            create('img', {
                className: 'chat-image',
                src: `data:image/jpeg;base64,${message.metadata.image_data}`,
                onclick: () => {
                    const newTab = window.open();
                    newTab.document.write(`<img src=\"data:image/jpeg;base64,${message.metadata.image_data}\" style=\"max-width:100%;height:auto\">`);
                }
            })
        );
    }

    // Text
    if (message.content) {
        contentChildren.push(
            create('div', {
                className: 'chat-text',
                innerHTML: formatMessageContent(message.content)
            })
        );
    }

    const bubble = create('div', { className: `chat-bubble ${isUser ? 'user' : 'assistant'}` }, contentChildren);

    return create('div', { className: `chat-message ${isUser ? 'user' : 'assistant'}` }, [
        !isUser ? create('div', { className: 'chat-avatar assistant' }, [ create('i', { className: 'fas fa-robot' }) ]) : '',
        bubble,
        isUser ? create('div', { className: 'chat-avatar user' }, [ create('i', { className: 'fas fa-user' }) ]) : ''
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

let selectedImageData = null;

function setupChatEventListeners() {
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const imageButton = document.getElementById('image-button');
    const imageUpload = document.getElementById('image-upload');
    const removeImageButton = document.getElementById('remove-image');
    const chatForm = document.getElementById('chat-form');

    // Không còn form submit; chặn Enter ở cấp tài liệu khi focus ở input
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && document.activeElement && document.activeElement.id === 'chat-input' && !e.shiftKey) {
            e.preventDefault();
            e.stopPropagation();
            sendMessage();
        }
    }, true);

    // Enter trong input (không Shift) sẽ gửi
    if (chatInput) {
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                e.stopPropagation();
                sendMessage();
            }
        });
    }

    // Click gửi
    if (sendButton) sendButton.addEventListener('click', sendMessage);

    // Image upload functionality
    if (imageButton && imageUpload) {
        imageButton.addEventListener('click', () => {
            imageUpload.click();
        });

        imageUpload.addEventListener('change', handleImageUpload);
    }

    if (removeImageButton) {
        removeImageButton.addEventListener('click', removeSelectedImage);
    }
}

function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
        alert('Vui lòng chọn file ảnh');
        return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
        alert('Kích thước ảnh quá lớn. Vui lòng chọn ảnh nhỏ hơn 5MB');
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        const base64Data = e.target.result.split(',')[1]; // Remove data:image/...;base64, prefix
        selectedImageData = base64Data;

        // Show preview
        const previewContainer = document.getElementById('image-preview');
        const previewImage = document.getElementById('preview-image');

        previewImage.src = e.target.result;
        previewContainer.style.display = 'block';

        // Clear file input for next use
        event.target.value = '';
        resizeChatLayout();
    };

    reader.readAsDataURL(file);
}

function removeSelectedImage() {
    selectedImageData = null;
    const previewContainer = document.getElementById('image-preview');
    previewContainer.style.display = 'none';
    resizeChatLayout();
}

async function sendMessage() {
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const typingIndicator = document.getElementById('typing-indicator');
    const messagesContainer = document.getElementById('chat-messages');

    if (!chatInput || !sendButton || !currentSessionId) return;

    const message = chatInput.value.trim();
    if (!message && !selectedImageData) return;

    try {
        // Disable input
        chatInput.disabled = true;
        sendButton.disabled = true;
        typingIndicator.style.display = 'block';
        typingIndicator.innerHTML = '<small><i class="fas fa-circle-notch fa-spin"></i> Trợ lý đang trả lời...</small>';

        // Clear input
        chatInput.value = '';

        // Local echo: user message
        const userMessage = {
            role: 'user',
            content: message,
            message_type: (selectedImageData ? 'image' : 'text'),
            timestamp: new Date().toISOString()
        };
        if (selectedImageData) {
            userMessage.metadata = { has_image: true, image_data: selectedImageData };
        }
        const userMessageEl = createMessageElement(userMessage);
        messagesContainer.appendChild(userMessageEl);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Prepare request
        const { api } = window.__APP__;
        const requestData = { content: message, message_type: userMessage.message_type };
        if (userMessage.message_type === 'image') requestData.image_data = userMessage.metadata.image_data;

        // Clear selected image after sending (UI)
        if (selectedImageData) removeSelectedImage();

        // Send to API
        const response = await api(`/api/chats/${currentSessionId}/messages`, {
            method: 'POST',
            body: JSON.stringify(requestData),
            noLoading: true
        });

        // AI response
        const aiMessage = {
            role: 'assistant',
            content: response.ai_response,
            message_type: 'text',
            timestamp: new Date().toISOString()
        };
        const aiMessageEl = createMessageElement(aiMessage);
        messagesContainer.appendChild(aiMessageEl);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        chatMessages.push(userMessage, aiMessage);
    } catch (error) {
        console.error('Error sending message:', error);
        const errorMessage = {
            role: 'assistant',
            content: 'Xin lỗi, có lỗi xảy ra khi xử lý tin nhắn. Vui lòng thử lại.',
            message_type: 'text',
            timestamp: new Date().toISOString()
        };
        const errorMessageEl = createMessageElement(errorMessage);
        messagesContainer.appendChild(errorMessageEl);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    } finally {
        chatInput.disabled = false;
        sendButton.disabled = false;
        typingIndicator.style.display = 'none';
        chatInput.focus();
        resizeChatLayout();
    }
}