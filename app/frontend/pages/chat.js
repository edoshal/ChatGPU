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
                    <button id="voice-button" class="btn" title="Bật chế độ chat giọng nói" type="button">
                        <i class="fas fa-microphone"></i>
                    </button>
                    <input type="text" id="chat-input" class="form-control" placeholder="Nhập tin nhắn hoặc ấn đè nút mic để ghi âm..." autocomplete="off">
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

    // Text với icon đặc biệt cho voice message
    if (message.content) {
        const textDiv = create('div', {
            className: 'chat-text',
            innerHTML: formatMessageContent(message.content)
        });

        // Thêm icon microphone cho voice messages
        if (message.auto_play_response || message.metadata?.voice_input) {
            const voiceIcon = create('i', {
                className: 'fas fa-microphone voice-message-icon',
                title: 'Tin nhắn bằng giọng nói'
            });
            textDiv.insertBefore(voiceIcon, textDiv.firstChild);
        }

        contentChildren.push(textDiv);
    }

    // Thêm nút TTS cho tin nhắn assistant có text
    if (!isUser && message.content && message.content.trim()) {
        contentChildren.push(
            create('div', { className: 'tts-controls' }, [
                // MMS-TTS-VIE button (Blue sound icon)
                create('button', {
                    className: 'tts-button mms-tts-button',
                    type: 'button',
                    onclick: (event) => playTextAsAudioMMS(message.content, event),
                    title: 'Phát audio (Facebook MMS-TTS-VIE)'
                }, [
                    create('i', { className: 'fas fa-volume-up' })
                ]),
                // Azure TTS button (original)
                create('button', {
                    className: 'tts-button azure-tts-button',
                    type: 'button',
                    onclick: (event) => playTextAsAudio(message.content, event),
                    title: 'Phát audio (Azure)'
                }, [
                    create('i', { className: 'fas fa-volume-up' })
                ])
            ])
        );
    }

    const bubble = create('div', { className: `chat-bubble ${isUser ? 'user' : 'assistant'}` }, contentChildren);

    return create('div', { className: `chat-message ${isUser ? 'user' : 'assistant'}` }, [
        ...((!isUser) ? [create('div', { className: 'chat-avatar assistant' }, [ create('i', { className: 'fas fa-robot' }) ])] : []),
        bubble,
        ...(isUser ? [create('div', { className: 'chat-avatar user' }, [ create('i', { className: 'fas fa-user' }) ])] : [])
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

// Biến global để quản lý audio
let currentAudio = null;
let currentTTSButton = null;

// Biến global để quản lý voice chat - Press & Hold mode
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let isPressedDown = false;

async function playTextAsAudio(text, event) {
    // Ngăn chặn default action và event propagation
    if (event) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
    }
    
    const { api } = window.__APP__;
    
    // Tìm button được click (event target)
    const button = event ? event.target.closest('.tts-button') : null;
    if (!button) return;

    // Nếu đang phát audio này, thì dừng
    if (currentAudio && currentTTSButton === button) {
        currentAudio.pause();
        currentAudio = null;
        currentTTSButton = null;
        button.innerHTML = '<i class="fas fa-volume-up"></i>';
        button.disabled = false;
        button.title = 'Phát audio';
        return;
    }

    // Dừng audio khác nếu đang phát
    if (currentAudio && currentTTSButton) {
        currentAudio.pause();
        currentAudio = null;
        currentTTSButton.innerHTML = '<i class="fas fa-volume-up"></i>';
        currentTTSButton.disabled = false;
        currentTTSButton.title = 'Phát audio';
    }

    try {
        // Hiển thị trạng thái đang tạo audio
        button.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i>';
        button.disabled = true;
        button.title = 'Đang tạo âm thanh...';

        // Gọi API để tạo audio
        const response = await api('/api/tts/generate', {
            method: 'POST',
            body: JSON.stringify({ text: text }),
            noLoading: true  // Không hiển thị loading global
        });

        if (response.success && response.audio_data_url) {
            // Hiển thị trạng thái đang tải audio
            button.innerHTML = '<i class="fas fa-download fa-pulse"></i>';
            button.title = 'Đang tải âm thanh...';

            // Tạo audio element
            currentAudio = new Audio(response.audio_data_url);
            currentTTSButton = button;

            // Sự kiện khi audio sẵn sàng phát
            currentAudio.addEventListener('canplaythrough', () => {
                button.innerHTML = '<i class="fas fa-play"></i>';
                button.title = 'Đang phát âm thanh - Click để dừng';
            });

            // Sự kiện khi audio bắt đầu phát
            currentAudio.addEventListener('play', () => {
                button.innerHTML = '<i class="fas fa-pause"></i>';
                button.title = 'Đang phát âm thanh - Click để dừng';
            });

            // Sự kiện khi audio kết thúc
            currentAudio.addEventListener('ended', () => {
                button.innerHTML = '<i class="fas fa-volume-up"></i>';
                button.disabled = false;
                button.title = 'Phát audio';
                currentAudio = null;
                currentTTSButton = null;
            });

            // Sự kiện khi có lỗi phát audio
            currentAudio.addEventListener('error', (e) => {
                button.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
                button.disabled = false;
                button.title = 'Lỗi phát audio - Click để thử lại';
                currentAudio = null;
                currentTTSButton = null;
                console.error('Error playing audio:', e);
            });

            // Bắt đầu phát audio
            try {
                await currentAudio.play();
                button.disabled = false;  // Cho phép click để dừng
            } catch (playError) {
                throw new Error('Không thể phát audio: ' + playError.message);
            }
            
        } else {
            throw new Error(response.detail || 'Không thể tạo audio');
        }

    } catch (error) {
        console.error('Error generating TTS:', error);
        button.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
        button.disabled = false;
        button.title = 'Lỗi - Click để thử lại';
        
        // Reset state
        currentAudio = null;
        currentTTSButton = null;
        
        // Hiển thị thông báo lỗi nhẹ nhàng
        const errorMsg = error.message || 'Không thể phát audio';
        console.warn('TTS Error:', errorMsg);
        
        // Tự động reset về trạng thái ban đầu sau 3 giây
        setTimeout(() => {
            if (button && button.innerHTML.includes('exclamation-triangle')) {
                button.innerHTML = '<i class="fas fa-volume-up"></i>';
                button.title = 'Phát audio';
            }
        }, 3000);
    }
}

async function playTextAsAudioMMS(text, event) {
    // Ngăn chặn default action và event propagation
    if (event) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
    }
    
    const { api } = window.__APP__;
    
    // Tìm button được click (event target)
    const button = event ? event.target.closest('.mms-tts-button') : null;
    if (!button) return;

    // Nếu đang phát audio này, thì dừng
    if (currentAudio && currentTTSButton === button) {
        currentAudio.pause();
        currentAudio = null;
        currentTTSButton = null;
        button.innerHTML = '<i class="fas fa-volume-up"></i>';
        button.disabled = false;
        button.title = 'Phát audio (Facebook MMS-TTS-VIE)';
        return;
    }

    // Dừng audio khác nếu đang phát
    if (currentAudio && currentTTSButton) {
        currentAudio.pause();
        currentAudio = null;
        currentTTSButton.innerHTML = currentTTSButton.classList.contains('mms-tts-button') ? 
            '<i class="fas fa-volume-up"></i>' : '<i class="fas fa-volume-up"></i>';
        currentTTSButton.disabled = false;
        currentTTSButton.title = currentTTSButton.classList.contains('mms-tts-button') ? 
            'Phát audio (Facebook MMS-TTS-VIE)' : 'Phát audio (Azure)';
    }

    try {
        // Hiển thị trạng thái đang tạo audio
        button.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i>';
        button.disabled = true;
        button.title = 'Đang tạo âm thanh (Facebook)...';

        // Gọi API để tạo audio
        const response = await api('/api/mms-tts/generate', {
            method: 'POST',
            body: JSON.stringify({ text: text }),
            noLoading: true  // Không hiển thị loading global
        });

        if (response.success && response.audio_data_url) {
            // Hiển thị trạng thái đang tải audio
            button.innerHTML = '<i class="fas fa-download fa-pulse"></i>';
            button.title = 'Đang tải âm thanh...';

            // Tạo audio element
            currentAudio = new Audio(response.audio_data_url);
            currentTTSButton = button;

            // Sự kiện khi audio sẵn sàng phát
            currentAudio.addEventListener('canplaythrough', () => {
                button.innerHTML = '<i class="fas fa-play"></i>';
                button.title = 'Đang phát âm thanh - Click để dừng';
            });

            // Sự kiện khi audio bắt đầu phát
            currentAudio.addEventListener('play', () => {
                button.innerHTML = '<i class="fas fa-pause"></i>';
                button.title = 'Đang phát âm thanh - Click để dừng';
            });

            // Sự kiện khi audio kết thúc
            currentAudio.addEventListener('ended', () => {
                button.innerHTML = '<i class="fas fa-volume-up"></i>';
                button.disabled = false;
                button.title = 'Phát audio (Facebook MMS-TTS-VIE)';
                currentAudio = null;
                currentTTSButton = null;
            });

            // Sự kiện khi có lỗi phát audio
            currentAudio.addEventListener('error', (e) => {
                button.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
                button.disabled = false;
                button.title = 'Lỗi phát audio - Click để thử lại';
                currentAudio = null;
                currentTTSButton = null;
                console.error('Error playing audio:', e);
            });

            // Bắt đầu phát audio
            try {
                await currentAudio.play();
                button.disabled = false;  // Cho phép click để dừng
            } catch (playError) {
                throw new Error('Không thể phát audio: ' + playError.message);
            }
            
        } else {
            throw new Error(response.detail || 'Không thể tạo audio');
        }

    } catch (error) {
        console.error('Error generating MMS-TTS:', error);
        button.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
        button.disabled = false;
        button.title = 'Lỗi - Click để thử lại';
        
        // Reset state
        currentAudio = null;
        currentTTSButton = null;
        
        // Hiển thị thông báo lỗi nhẹ nhàng
        const errorMsg = error.message || 'Không thể phát audio';
        console.warn('MMS-TTS Error:', errorMsg);
        
        // Tự động reset về trạng thái ban đầu sau 3 giây
        setTimeout(() => {
            if (button && button.innerHTML.includes('exclamation-triangle')) {
                button.innerHTML = '<i class="fas fa-volume-up"></i>';
                button.title = 'Phát audio (Facebook MMS-TTS-VIE)';
            }
        }, 3000);
    }
}

// Voice Chat Functions
// Press & Hold functions
function startPressToTalk() {
    if (isPressedDown || isRecording) return;
    
    console.log('Press-to-talk started');
    isPressedDown = true;
    
    const voiceButton = document.getElementById('voice-button');
    const chatInput = document.getElementById('chat-input');
    
    // Visual feedback
    voiceButton.classList.add('voice-active', 'recording');
    voiceButton.innerHTML = '<i class="fas fa-microphone"></i>';
    voiceButton.title = 'Đang ghi âm... Thả ra để gửi';
    
    // Show recording status
    if (chatInput) {
        chatInput.placeholder = 'Đang ghi âm... Thả nút để gửi';
    }
    
    // Start recording immediately
    startRecording();
}

function stopPressToTalk() {
    if (!isPressedDown) return;
    
    console.log('Press-to-talk stopped');
    isPressedDown = false;
    
    // Stop recording first
    if (isRecording) {
        stopRecording();
    }
    
    // UI will be reset in stopRecording(), but ensure it's reset here too
    setTimeout(() => {
        const voiceButton = document.getElementById('voice-button');
        const chatInput = document.getElementById('chat-input');
        const sendButton = document.getElementById('send-button');
        
        // Reset visual
        if (voiceButton) {
            voiceButton.classList.remove('voice-active', 'recording');
            voiceButton.innerHTML = '<i class="fas fa-microphone-slash"></i>';
            voiceButton.title = 'Ấn đè để ghi âm';
        }
        
        if (sendButton) {
            sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
            sendButton.classList.remove('recording');
            sendButton.title = 'Gửi tin nhắn';
        }
        
        if (chatInput) {
            chatInput.placeholder = 'Nhập tin nhắn hoặc ấn đè nút mic để ghi âm...';
        }
    }, 100); // Small delay to ensure stopRecording completes
}

async function startRecording() {
    if (isRecording) {
        stopRecording();
        return;
    }

    try {
        console.log('🎤 Starting Web Audio API recording...');
        
        // Kiểm tra browser support
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error('Browser không hỗ trợ ghi âm');
        }
        
        // Ưu tiên Web Audio API cho quality tốt hơn
        if (!window.AudioContext && !window.webkitAudioContext) {
            throw new Error('Browser không hỗ trợ Web Audio API');
        }
        
        // Xin quyền microphone với settings tối ưu cho Azure Speech
        console.log('Requesting microphone permission...');
        const stream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                sampleRate: 16000,  // Fixed 16kHz cho Azure
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            } 
        });
        
        console.log('✅ Microphone access granted');
        
        // Tạo AudioContext và setup Web Audio API recording
        const audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: 16000  // Force 16kHz
        });
        
        const source = audioContext.createMediaStreamSource(stream);
        
        // Sử dụng ScriptProcessorNode để capture raw audio data
        const bufferSize = 4096;
        const recorder = audioContext.createScriptProcessor(bufferSize, 1, 1);
        
        // Store audio data
        window.recordedData = [];
        window.recordingStream = stream;
        window.audioContext = audioContext;
        window.audioRecorder = recorder;
        
        recorder.onaudioprocess = (event) => {
            const inputBuffer = event.inputBuffer;
            const inputData = inputBuffer.getChannelData(0);
            
            // Copy data (Float32Array)
            const buffer = new Float32Array(inputData.length);
            buffer.set(inputData);
            window.recordedData.push(buffer);
            
            console.log(`📊 Audio chunk: ${inputData.length} samples`);
        };
        
        // Connect audio nodes
        source.connect(recorder);
        recorder.connect(audioContext.destination);
        
        console.log('✅ Web Audio API recording started');
        isRecording = true;

    } catch (error) {
        console.error('Error starting recording:', error);
        alert('Không thể truy cập microphone. Vui lòng cho phép quyền truy cập microphone.');
    }
}

function stopRecording() {
    if (!isRecording) return;
    
    console.log('🛑 Stopping Web Audio API recording...');
    
    try {
        // Disconnect audio nodes
        if (window.audioRecorder) {
            window.audioRecorder.disconnect();
        }
        
        // Stop audio context
        if (window.audioContext) {
            window.audioContext.close();
        }
        
        // Stop stream
        if (window.recordingStream) {
            window.recordingStream.getTracks().forEach(track => track.stop());
        }
        
        isRecording = false;
        
        // Reset UI buttons
        const voiceButton = document.getElementById('voice-button');
        const sendButton = document.getElementById('send-button');
        
        if (voiceButton) {
            voiceButton.classList.remove('voice-active', 'recording');
            voiceButton.innerHTML = '<i class="fas fa-microphone-slash"></i>';
            voiceButton.title = 'Ấn đè để ghi âm';
        }
        
        if (sendButton) {
            sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
            sendButton.classList.remove('recording');
            sendButton.title = 'Gửi tin nhắn';
        }
        
        // Reset chat input placeholder
        const chatInput = document.getElementById('chat-input');
        if (chatInput) {
            chatInput.placeholder = 'Nhập tin nhắn hoặc ấn đè nút mic để ghi âm...';
        }
        
        // Process recorded data
        if (window.recordedData && window.recordedData.length > 0) {
            console.log(`📊 Processing ${window.recordedData.length} audio chunks...`);
            
            // Combine all chunks
            const totalLength = window.recordedData.reduce((sum, chunk) => sum + chunk.length, 0);
            const combinedData = new Float32Array(totalLength);
            
            let offset = 0;
            for (const chunk of window.recordedData) {
                combinedData.set(chunk, offset);
                offset += chunk.length;
            }
            
            console.log(`🎵 Total samples: ${totalLength}, Duration: ${(totalLength / 16000).toFixed(2)}s`);
            
            // Convert to WAV
            const wavBlob = createWavBlob(combinedData, 16000);
            console.log(`💾 Created WAV blob: ${wavBlob.size} bytes`);
            
            // Clean up
            window.recordedData = [];
            
            // Process the WAV
            processRecordedWav(wavBlob);
        } else {
            console.error('❌ No audio data recorded');
        }
        
    } catch (error) {
        console.error('Error stopping recording:', error);
        isRecording = false;
        
        // Reset UI on error
        const voiceButton = document.getElementById('voice-button');
        const sendButton = document.getElementById('send-button');
        const chatInput = document.getElementById('chat-input');
        
        if (voiceButton) {
            voiceButton.classList.remove('voice-active', 'recording');
            voiceButton.innerHTML = '<i class="fas fa-microphone-slash"></i>';
            voiceButton.title = 'Ấn đè để ghi âm';
        }
        
        if (sendButton) {
            sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
            sendButton.classList.remove('recording');
            sendButton.title = 'Gửi tin nhắn';
        }
        
        if (chatInput) {
            chatInput.placeholder = 'Nhập tin nhắn hoặc ấn đè nút mic để ghi âm...';
        }
    }
}

// WAV Creation Functions
function createWavBlob(audioData, sampleRate) {
    const length = audioData.length;
    const buffer = new ArrayBuffer(44 + length * 2);
    const view = new DataView(buffer);
    
    // WAV header
    const writeString = (offset, string) => {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    };
    
    writeString(0, 'RIFF');
    view.setUint32(4, 36 + length * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);  // PCM
    view.setUint16(22, 1, true);  // Mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(36, 'data');
    view.setUint32(40, length * 2, true);
    
    // Convert float32 to int16
    let offset = 44;
    for (let i = 0; i < length; i++) {
        const sample = Math.max(-1, Math.min(1, audioData[i]));
        view.setInt16(offset, sample * 0x7FFF, true);
        offset += 2;
    }
    
    return new Blob([buffer], { type: 'audio/wav' });
}

async function processRecordedWav(wavBlob) {
    console.log('🎵 Processing recorded WAV for immediate send...');
    
    try {
        // Quick audio validation
        const isValid = await testAudioPlayback(wavBlob);
        
        if (isValid) {
            console.log('✅ WAV audio valid, sending immediately...');
            // Send directly without preview
            await processVoiceInput(wavBlob);
        } else {
            console.error('WAV audio không hợp lệ');
            alert('WAV audio ghi được có vấn đề. Vui lòng thử lại.');
        }
    } catch (error) {
        console.error('Error processing WAV:', error);
        alert('Lỗi xử lý audio WAV: ' + error.message);
    }
}

// Audio testing and playback utilities
// Quick audio validation (simplified for immediate send)
async function testAudioPlayback(audioBlob) {
    console.log('🔍 Quick audio validation...');
    
    // Basic checks
    if (!audioBlob || audioBlob.size === 0) {
        console.error('❌ Empty audio blob');
        return false;
    }
    
    if (audioBlob.size < 1000) { // Less than 1KB is probably too small
        console.warn('⚠️ Audio blob very small:', audioBlob.size, 'bytes');
        return false;
    }
    
    console.log('✅ Audio blob seems valid:', audioBlob.size, 'bytes');
    return true;
}

// Audio conversion utility (not used anymore - direct WAV recording)
async function convertToWav(audioBlob) {
    return new Promise((resolve, reject) => {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const fileReader = new FileReader();
        
        fileReader.onload = async function(e) {
            try {
                const arrayBuffer = e.target.result;
                const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
                
                // Convert to WAV
                const wavBuffer = audioBufferToWav(audioBuffer);
                const wavBlob = new Blob([wavBuffer], { type: 'audio/wav' });
                
                resolve(wavBlob);
            } catch (error) {
                reject(error);
            }
        };
        
        fileReader.onerror = () => reject(new Error('Failed to read audio file'));
        fileReader.readAsArrayBuffer(audioBlob);
    });
}

function audioBufferToWav(buffer) {
    const length = buffer.length;
    const numberOfChannels = buffer.numberOfChannels;
    const sampleRate = buffer.sampleRate;
    const bytesPerSample = 2;
    const blockAlign = numberOfChannels * bytesPerSample;
    const byteRate = sampleRate * blockAlign;
    const dataSize = length * blockAlign;
    const bufferSize = 44 + dataSize;
    
    const arrayBuffer = new ArrayBuffer(bufferSize);
    const view = new DataView(arrayBuffer);
    
    // WAV header
    const writeString = (offset, string) => {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    };
    
    writeString(0, 'RIFF');
    view.setUint32(4, bufferSize - 8, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numberOfChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bytesPerSample * 8, true);
    writeString(36, 'data');
    view.setUint32(40, dataSize, true);
    
    // Convert audio data
    let offset = 44;
    for (let i = 0; i < length; i++) {
        for (let channel = 0; channel < numberOfChannels; channel++) {
            const sample = Math.max(-1, Math.min(1, buffer.getChannelData(channel)[i]));
            view.setInt16(offset, sample * 0x7FFF, true);
            offset += 2;
        }
    }
    
    return arrayBuffer;
}

async function processVoiceInput(audioBlob) {
    const messagesContainer = document.getElementById('chat-messages');
    const typingIndicator = document.getElementById('typing-indicator');

    try {
        // Hiển thị trạng thái đang xử lý với animation
        typingIndicator.style.display = 'block';
        typingIndicator.innerHTML = '<small><i class="fas fa-microphone-alt fa-pulse"></i> Đang nhận diện giọng nói...</small>';

        // Process voice recognition
        const result = await processVoiceRecognition(audioBlob);
        await handleVoiceResult(result, messagesContainer, typingIndicator);
        
    } catch (error) {
        console.error('Voice processing error:', error);
        
        // Thông báo lỗi với hướng dẫn cụ thể
        let errorContent = 'Xin lỗi, tôi không thể nhận diện được giọng nói của bạn.';
        
        if (error.message.includes('audio')) {
            errorContent += '\n\n💡 Hướng dẫn:\n• Kiểm tra microphone đã bật chưa\n• Nói rõ ràng và to hơn\n• Ghi âm từ 1-3 giây';
        } else if (error.message.includes('nhận diện')) {
            errorContent += '\n\n💡 Có thể thử:\n• Nói chậm hơn và rõ ràng\n• Kiểm tra âm lượng microphone\n• Hoặc gõ tin nhắn bình thường';
        }
        
        const errorMessage = {
            role: 'assistant', 
            content: errorContent,
            message_type: 'text',
            timestamp: new Date().toISOString()
        };
        const errorMessageEl = createMessageElement(errorMessage);
        messagesContainer.appendChild(errorMessageEl);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    } finally {
        typingIndicator.style.display = 'none';
    }
}

async function processVoiceRecognition(audioBlob) {
    const { api } = window.__APP__;
    
    // Debug: Kiểm tra audio blob
    console.log('Audio blob size:', audioBlob.size, 'bytes');
    console.log('Audio blob type:', audioBlob.type);
    
    if (audioBlob.size === 0) {
        throw new Error('Không có dữ liệu audio để gửi');
    }
    
    // Azure Speech Service hỗ trợ WebM, không cần convert
    let processedBlob = audioBlob;
    let filename = 'voice_input.webm';
    
    // Note: Đã test - Azure Speech Service hoạt động tốt với WebM
    console.log('Using original WebM format (Azure supports it)');

    // Thử cách tiếp cận FormData trước
    try {
        const formData = new FormData();
        formData.append('audio_file', processedBlob, filename);
        
        // Debug: Kiểm tra FormData
        console.log('FormData entries:');
        for (let [key, value] of formData.entries()) {
            console.log(`${key}:`, value);
            if (value instanceof File || value instanceof Blob) {
                console.log(`  - Size: ${value.size} bytes`);
                console.log(`  - Type: ${value.type}`);
                console.log(`  - Name: ${value.name || 'unnamed'}`);
            }
        }

        // Gửi audio để nhận diện - sử dụng fetch trực tiếp với FormData
        const authToken = window.__APP__.authToken || localStorage.getItem('auth_token');
        console.log('Auth token:', authToken ? 'Present' : 'Missing');
        const response = await fetch('/api/speech/recognize', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            },
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        const result = await response.json();
        
        return result;
        
    } catch (formDataError) {
        console.warn('FormData approach failed:', formDataError);
        
        // Fallback: Chuyển sang base64 approach
        console.log('Trying base64 approach...');
        
        const base64Audio = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result.split(',')[1]);
            reader.onerror = reject;
            reader.readAsDataURL(processedBlob); // Sử dụng processed blob (có thể đã convert WAV)
        });
        
        const result = await api('/api/speech/recognize-base64', {
            method: 'POST',
            body: JSON.stringify({
                audio_data: base64Audio,
                mime_type: processedBlob.type || audioBlob.type // Sử dụng type của processed blob
            }),
            noLoading: true
        });
        
        return result;
    }
}

async function handleVoiceResult(result, messagesContainer, typingIndicator) {
    const { api } = window.__APP__;
    
    try {
        if (result.success && result.text.trim()) {
            // Hiển thị tin nhắn user (voice)
            // Debug recognition result
            console.log('🎤 Recognition result:', result.text);
            if (result.confidence) {
                console.log('🎯 Confidence:', result.confidence);
            }
            
            // Show warning for potentially incorrect recognition
            let displayText = result.text;
            if (result.text.length < 3 || result.text === 'Phẩy.' || result.text === '.') {
                displayText = `${result.text} ⚠️ (có thể nhận diện sai)`;
            }
            
            const userMessage = {
                role: 'user',
                content: displayText,
                message_type: 'text',
                timestamp: new Date().toISOString(),
                metadata: { 
                    voice_input: true,
                    original_recognition: result.text,
                    confidence: result.confidence || null
                }
            };
            
            const userMessageEl = createMessageElement(userMessage);
            messagesContainer.appendChild(userMessageEl);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            // Gửi tin nhắn với auto-play enabled
            typingIndicator.innerHTML = '<small><i class="fas fa-robot fa-pulse"></i> Trợ lý đang trả lời...</small>';
            
            const chatResponse = await api(`/api/chats/${currentSessionId}/messages`, {
                method: 'POST',
                body: JSON.stringify({ 
                    content: result.text, 
                    message_type: 'text', // Sử dụng 'text' type, đánh dấu bằng metadata
                    auto_play_response: true  // Tự động phát audio
                }),
                noLoading: true
            });

            // Hiển thị AI response
            const aiMessage = {
                role: 'assistant',
                content: chatResponse.ai_response,
                message_type: 'text',
                timestamp: new Date().toISOString()
            };
            
            const aiMessageEl = createMessageElement(aiMessage);
            messagesContainer.appendChild(aiMessageEl);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            // Tự động phát audio nếu có
            if (chatResponse.auto_play_audio) {
                try {
                    typingIndicator.innerHTML = '<small><i class="fas fa-volume-up fa-pulse"></i> Đang phát âm thanh...</small>';
                    
                    const autoAudio = new Audio(chatResponse.auto_play_audio);
                    
                    autoAudio.onended = () => {
                        typingIndicator.style.display = 'none';
                    };
                    
                    autoAudio.onerror = () => {
                        typingIndicator.style.display = 'none';
                    };
                    
                    await autoAudio.play();
                } catch (playError) {
                    console.warn('Auto-play failed:', playError);
                    typingIndicator.style.display = 'none';
                }
            } else {
                typingIndicator.style.display = 'none';
            }

            // Reload profile data if needed
            if (window.__APP__ && window.__APP__.loadCurrentProfile) {
                try {
                    await window.__APP__.loadCurrentProfile();
                } catch (e) {
                    console.warn('Failed to refresh profile data:', e);
                }
            }

        } else {
            throw new Error(result.error || 'Không thể nhận diện được giọng nói');
        }

    } catch (error) {
        console.error('Voice processing error:', error);
        
        // Hiển thị thông báo lỗi
        const errorMessage = {
            role: 'assistant',
            content: 'Xin lỗi, tôi không thể nhận diện được giọng nói của bạn. Vui lòng thử lại hoặc gõ tin nhắn.',
            message_type: 'text',
            timestamp: new Date().toISOString()
        };
        const errorMessageEl = createMessageElement(errorMessage);
        messagesContainer.appendChild(errorMessageEl);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    } finally {
        typingIndicator.style.display = 'none';
    }
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

    // Click gửi - chỉ cho text message
    if (sendButton) {
        sendButton.addEventListener('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            sendMessage();
        });
    }

    // Voice button - Press & Hold
    const voiceButton = document.getElementById('voice-button');
    if (voiceButton) {
        // Mouse events
        voiceButton.addEventListener('mousedown', (event) => {
            event.preventDefault();
            startPressToTalk();
        });
        
        voiceButton.addEventListener('mouseup', (event) => {
            event.preventDefault();
            stopPressToTalk();
        });
        
        voiceButton.addEventListener('mouseleave', (event) => {
            // Stop recording if mouse leaves button while pressed
            if (isPressedDown) {
                stopPressToTalk();
            }
        });
        
        // Touch events for mobile
        voiceButton.addEventListener('touchstart', (event) => {
            event.preventDefault();
            startPressToTalk();
        });
        
        voiceButton.addEventListener('touchend', (event) => {
            event.preventDefault();
            stopPressToTalk();
        });
        
        voiceButton.addEventListener('touchcancel', (event) => {
            // Stop if touch is cancelled
            if (isPressedDown) {
                stopPressToTalk();
            }
        });
    }

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
        
        // Reload current profile data in case AI updated health status
        if (window.__APP__ && window.__APP__.loadCurrentProfile) {
            try {
                await window.__APP__.loadCurrentProfile();
                console.log('Profile data refreshed after chat update');
            } catch (e) {
                console.warn('Failed to refresh profile data:', e);
            }
        }
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