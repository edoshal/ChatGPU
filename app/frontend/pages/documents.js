// Documents Page

async function renderDocuments() {
    const { $, currentProfile } = window.__APP__;
    const profile = currentProfile();
    
    const container = $('#page-container');
    container.style.padding = '2rem';
    container.style.background = 'rgba(255, 255, 255, 0.95)';
    
    if (!profile) {
        container.innerHTML = `
            <div class="text-center mt-4">
                <i class="fas fa-user-circle" style="font-size: 4rem; color: #667eea;"></i>
                <h2>Chưa chọn hồ sơ sức khỏe</h2>
                <p class="text-muted">Vui lòng chọn hoặc tạo hồ sơ sức khỏe để upload tài liệu</p>
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
            <div class="d-flex justify-between align-center">
                <div>
                    <h1 class="page-title">
                        <i class="fas fa-file-medical"></i>
                        Tài liệu y tế
                    </h1>
                    <p class="page-subtitle">Hồ sơ: ${profile.profile_name}</p>
                </div>
                <button class="btn btn-primary" onclick="showUploadModal()">
                    <i class="fas fa-upload"></i>
                    Upload tài liệu
                </button>
            </div>
        </div>
        
        <div id="documents-list">
            <div class="text-center">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Đang tải tài liệu...</p>
            </div>
        </div>
    `;
    
    try {
        const documents = await window.__APP__.api(`/profiles/${profile.id}/documents`);
        renderDocumentsList(documents);
    } catch (error) {
        $('#documents-list').innerHTML = `
            <div class="text-center">
                <i class="fas fa-exclamation-triangle text-danger"></i>
                <h3>Không thể tải tài liệu</h3>
                <p class="text-muted">${error.message}</p>
            </div>
        `;
    }
}

function renderDocumentsList(documents) {
    const { create } = window.__APP__;
    const documentsList = $('#documents-list');
    
    if (documents.length === 0) {
        documentsList.innerHTML = `
            <div class="card text-center">
                <div class="card-body">
                    <i class="fas fa-file-upload" style="font-size: 3rem; color: #667eea; margin-bottom: 1rem;"></i>
                    <h3>Chưa có tài liệu nào</h3>
                    <p class="text-muted">Upload tài liệu y tế để AI phân tích và tóm tắt</p>
                    <button class="btn btn-primary" onclick="showUploadModal()">
                        Upload tài liệu đầu tiên
                    </button>
                </div>
            </div>
        `;
        return;
    }
    
    documentsList.innerHTML = '';
    const grid = create('div', { className: 'grid grid-2' });
    
    documents.forEach(doc => {
        const docCard = create('div', { className: 'card' }, [
            create('div', { className: 'card-header' }, [
                create('h4', { className: 'card-title' }, [
                    create('i', { className: 'fas fa-file-pdf text-danger' }),
                    ` ${doc.filename}`
                ])
            ]),
            create('div', { className: 'card-body' }, [
                doc.ai_summary ? create('div', { className: 'mb-3' }, [
                    create('strong', {}, 'Tóm tắt AI:'),
                    create('p', { className: 'text-muted' }, doc.ai_summary)
                ]) : '',
                create('div', { className: 'd-flex justify-between align-center' }, [
                    create('small', { className: 'text-muted' }, [
                        'Upload: ',
                        new Date(doc.uploaded_at).toLocaleString('vi-VN')
                    ]),
                    doc.file_size ? create('small', { className: 'text-muted' }, 
                        `${(doc.file_size / 1024).toFixed(1)} KB`
                    ) : ''
                ])
            ])
        ]);
        
        grid.appendChild(docCard);
    });
    
    documentsList.appendChild(grid);
}

function showUploadModal() {
    const { create } = window.__APP__;
    
    const form = create('form', { id: 'upload-form', enctype: 'multipart/form-data' }, [
        create('div', { className: 'form-group' }, [
            create('label', { className: 'form-label' }, 'Chọn file PDF'),
            create('input', { 
                type: 'file',
                className: 'form-control',
                name: 'file',
                accept: '.pdf',
                required: true
            })
        ]),
        create('p', { className: 'text-muted' }, 'Chỉ hỗ trợ file PDF. AI sẽ tự động phân tích và tóm tắt nội dung.')
    ]);
    
    window.__APP__.showModal('Upload tài liệu y tế', form, [
        create('button', { 
            className: 'btn btn-secondary',
            onclick: () => $('#modal-container').classList.add('hidden')
        }, 'Hủy'),
        create('button', { 
            className: 'btn btn-primary',
            onclick: handleUpload
        }, 'Upload')
    ]);
}

async function handleUpload() {
    const { apiForm, showToast, currentProfile } = window.__APP__;
    const profile = currentProfile();
    
    const form = $('#upload-form');
    const formData = new FormData(form);
    
    try {
        await apiForm(`/profiles/${profile.id}/documents`, formData);
        
        $('#modal-container').classList.add('hidden');
        showToast('Upload tài liệu thành công!');
        
        // Reload documents
        renderDocuments();
    } catch (error) {
        // Error already handled by apiForm
    }
}

// Global functions
window.showUploadModal = showUploadModal;
window.handleUpload = handleUpload;