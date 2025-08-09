// Profiles Management Page

async function renderProfiles() {
    const { $, create, api, showToast, navigateTo, setCurrentProfile } = window.__APP__;
    
    const container = $('#page-container');
    container.style.padding = '2rem';
    container.style.background = 'rgba(255, 255, 255, 0.95)';
    container.style.boxShadow = '0 8px 32px rgba(0, 0, 0, 0.1)';
    container.style.backdropFilter = 'blur(20px)';
    
    container.innerHTML = `
        <div class="page-header">
            <div class="d-flex justify-between align-center">
                <div>
                    <h1 class="page-title">
                        <i class="fas fa-user-circle"></i>
                        Quản lý hồ sơ sức khỏe
                    </h1>
                    <p class="page-subtitle">Tạo và quản lý các hồ sơ sức khỏe của bạn</p>
                </div>
                <button class="btn btn-primary" onclick="showCreateProfileModal()">
                    <i class="fas fa-plus"></i>
                    Tạo hồ sơ mới
                </button>
            </div>
        </div>
        
        <div id="profiles-list" class="grid grid-2">
            <div class="text-center">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Đang tải hồ sơ...</p>
            </div>
        </div>
    `;
    
    try {
        const profiles = await api('/profiles');
        renderProfilesList(profiles);
    } catch (error) {
        $('#profiles-list').innerHTML = `
            <div class="text-center">
                <i class="fas fa-exclamation-triangle text-danger"></i>
                <h3>Không thể tải hồ sơ</h3>
                <p class="text-muted">${error.message}</p>
            </div>
        `;
    }
}

function renderProfilesList(profiles) {
    const { create, currentProfile } = window.__APP__;
    const currentProfileId = currentProfile()?.id;
    
    const profilesList = $('#profiles-list');
    profilesList.innerHTML = '';
    
    if (profiles.length === 0) {
        profilesList.innerHTML = `
            <div class="card text-center" style="grid-column: 1 / -1;">
                <div class="card-body">
                    <i class="fas fa-user-plus" style="font-size: 3rem; color: #667eea; margin-bottom: 1rem;"></i>
                    <h3>Chưa có hồ sơ nào</h3>
                    <p class="text-muted">Tạo hồ sơ sức khỏe đầu tiên để bắt đầu sử dụng dịch vụ</p>
                    <button class="btn btn-primary" onclick="showCreateProfileModal()">
                        Tạo hồ sơ đầu tiên
                    </button>
                </div>
            </div>
        `;
        return;
    }
    
    profiles.forEach(profile => {
        // Parse conditions_json if it's a string
        let parsedJson = {};
        if (profile.conditions_json) {
            if (typeof profile.conditions_json === 'string') {
                try { parsedJson = JSON.parse(profile.conditions_json); } catch { parsedJson = {}; }
            } else {
                parsedJson = profile.conditions_json || {};
            }
        }
        const isActive = profile.id === currentProfileId;
        const profileCard = create('div', { 
            className: `card ${isActive ? 'border-primary' : ''}`,
            style: isActive ? 'border-color: #667eea; border-width: 2px;' : ''
        }, [
            create('div', { className: 'card-header' }, [
                create('div', { className: 'd-flex justify-between align-center' }, [
                    create('h4', { className: 'card-title' }, [
                        profile.profile_name,
                        profile.is_default ? create('span', { 
                            className: 'badge',
                            style: 'margin-left: 0.5rem; background: #28a745; color: white; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem;'
                        }, 'Mặc định') : null,
                        isActive ? create('span', { 
                            className: 'badge',
                            style: 'margin-left: 0.5rem; background: #667eea; color: white; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem;'
                        }, 'Đang sử dụng') : null
                    ]),
                    create('div', { className: 'd-flex align-center' }, [
                        !isActive ? create('button', { 
                            className: 'btn btn-sm btn-primary',
                            onclick: () => switchToProfile(profile),
                            style: 'margin-right: 0.5rem;'
                        }, 'Chuyển đến') : null,
                        create('button', { 
                            className: 'btn btn-sm btn-secondary',
                            onclick: () => showEditProfileModal(profile)
                        }, 'Sửa'),
                        create('button', { 
                            className: 'btn btn-sm btn-danger',
                            style: 'margin-left: 0.5rem;',
                            onclick: () => confirmDeleteProfile(profile)
                        }, 'Xóa')
                    ])
                ])
            ]),
            create('div', { className: 'card-body' }, [
                profile.age ? create('p', {}, [
                    create('strong', {}, 'Tuổi: '),
                    profile.age.toString()
                ]) : null,
                profile.gender ? create('p', {}, [
                    create('strong', {}, 'Giới tính: '),
                    profile.gender === 'male' ? 'Nam' : profile.gender === 'female' ? 'Nữ' : 'Khác'
                ]) : null,
                profile.weight ? create('p', {}, [
                    create('strong', {}, 'Cân nặng: '),
                    `${profile.weight} kg`
                ]) : null,
                profile.height ? create('p', {}, [
                    create('strong', {}, 'Chiều cao: '),
                    `${profile.height} cm`
                ]) : null,
                profile.conditions_text ? create('div', { className: 'mb-2' }, [
                    create('strong', {}, 'Tình trạng sức khỏe:'),
                    create('p', { className: 'text-muted' }, profile.conditions_text)
                ]) : null,
                (parsedJson && parsedJson.conditions_list && parsedJson.conditions_list.length) ?
                    create('div', {}, [
                        create('strong', {}, 'Bệnh lý:'),
                        create('ul', {}, parsedJson.conditions_list.map(x => create('li', {}, x)))
                    ]) : null ,
                create('small', { className: 'text-muted' }, [
                    'Cập nhật: ',
                    new Date(profile.updated_at).toLocaleString('vi-VN')
                ])
            ])
        ]);
        
        profilesList.appendChild(profileCard);
    });
}

async function switchToProfile(profile) {
    const { setCurrentProfile, showToast, loadUserProfiles } = window.__APP__;
    
    setCurrentProfile(profile);
    await loadUserProfiles();
    showToast(`Đã chuyển sang hồ sơ: ${profile.profile_name}`);
    
    // Reload profiles list to update active status
    const profiles = await window.__APP__.api('/profiles');
    renderProfilesList(profiles);
}

function showCreateProfileModal() {
    const { create, showModal } = window.__APP__;
    
    const form = create('form', { id: 'create-profile-form' }, [
        create('div', { className: 'form-group' }, [
            create('label', { className: 'form-label' }, 'Tên hồ sơ *'),
            create('input', { 
                type: 'text',
                className: 'form-control',
                name: 'profile_name',
                required: true,
                placeholder: 'VD: Hồ sơ của tôi'
            })
        ]),
        create('div', { className: 'grid grid-2' }, [
            create('div', { className: 'form-group' }, [
                create('label', { className: 'form-label' }, 'Tuổi'),
                create('input', { 
                    type: 'number',
                    className: 'form-control',
                    name: 'age',
                    min: 0,
                    max: 120,
                    placeholder: '25'
                })
            ]),
            create('div', { className: 'form-group' }, [
                create('label', { className: 'form-label' }, 'Giới tính'),
                create('select', { className: 'form-control form-select', name: 'gender' }, [
                    create('option', { value: '' }, 'Chọn giới tính'),
                    create('option', { value: 'male' }, 'Nam'),
                    create('option', { value: 'female' }, 'Nữ'),
                    create('option', { value: 'other' }, 'Khác')
                ])
            ])
        ]),
        create('div', { className: 'grid grid-2' }, [
            create('div', { className: 'form-group' }, [
                create('label', { className: 'form-label' }, 'Cân nặng (kg)'),
                create('input', { 
                    type: 'number',
                    className: 'form-control',
                    name: 'weight',
                    step: 0.1,
                    placeholder: '65.5'
                })
            ]),
            create('div', { className: 'form-group' }, [
                create('label', { className: 'form-label' }, 'Chiều cao (cm)'),
                create('input', { 
                    type: 'number',
                    className: 'form-control',
                    name: 'height',
                    step: 0.1,
                    placeholder: '170'
                })
            ])
        ]),
        create('div', { className: 'form-group' }, [
            create('label', { className: 'form-label' }, 'Tình trạng sức khỏe'),
            create('textarea', { 
                className: 'form-control',
                name: 'conditions_text',
                rows: 3,
                placeholder: 'Mô tả các vấn đề sức khỏe, bệnh lý, dị ứng... (nếu có)'
            })
        ]),
        create('div', { className: 'form-group' }, [
            create('label', { className: 'form-label' }, 'Bệnh lý (mỗi dòng một mục)'),
            create('textarea', { 
                className: 'form-control',
                name: 'conditions_list',
                rows: 3,
                placeholder: 'Ví dụ:\nTăng huyết áp\nĐái tháo đường type 2\nRối loạn mỡ máu'
            })
        ]),
        create('div', { className: 'form-group' }, [
            create('label', { className: 'd-flex align-center' }, [
                create('input', { 
                    type: 'checkbox',
                    name: 'is_default',
                    style: 'margin-right: 0.5rem;'
                }),
                'Đặt làm hồ sơ mặc định'
            ])
        ])
    ]);
    
    showModal('Tạo hồ sơ sức khỏe mới', form, [
        create('button', { 
            className: 'btn btn-secondary',
            onclick: () => $('#modal-container').classList.add('hidden')
        }, 'Hủy'),
        create('button', { 
            className: 'btn btn-primary',
            onclick: handleCreateProfile
        }, 'Tạo hồ sơ')
    ]);
}

async function handleCreateProfile() {
    const { api, showToast } = window.__APP__;
    
    const form = $('#create-profile-form');
    const formData = new FormData(form);
    
    const data = {
        profile_name: formData.get('profile_name'),
        age: formData.get('age') ? parseInt(formData.get('age')) : null,
        gender: formData.get('gender') || null,
        weight: formData.get('weight') ? parseFloat(formData.get('weight')) : null,
        height: formData.get('height') ? parseFloat(formData.get('height')) : null,
        conditions_text: formData.get('conditions_text') || '',
        is_default: formData.has('is_default'),
        conditions_list: (formData.get('conditions_list') || '').split('\n').map(s => s.trim()).filter(Boolean)
    };
    
    try {
        await api('/profiles', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        $('#modal-container').classList.add('hidden');
        showToast('Tạo hồ sơ thành công!');
        
        // Reload profiles
        renderProfiles();
    } catch (error) {
        // Error already handled by api function
    }
}

// Global functions
window.showCreateProfileModal = showCreateProfileModal;
window.handleCreateProfile = handleCreateProfile;
window.showEditProfileModal = showEditProfileModal;
window.handleUpdateProfile = handleUpdateProfile;
window.addConditionItem = addConditionItem;
window.removeConditionItem = removeConditionItem;

function showEditProfileModal(profile){
    const { create, showModal } = window.__APP__;
    // Parse json list
    let parsedJson = {};
    if (profile.conditions_json){
        if (typeof profile.conditions_json === 'string'){
            try { parsedJson = JSON.parse(profile.conditions_json); } catch { parsedJson = {}; }
        } else parsedJson = profile.conditions_json;
    }
    const list = Array.isArray(parsedJson.conditions_list) ? parsedJson.conditions_list : [];
    
    const form = create('form', { id: 'edit-profile-form', 'data-id': profile.id }, [
        create('div', { className: 'form-group' }, [
            create('label', { className: 'form-label' }, 'Tên hồ sơ *'),
            create('input', { type: 'text', className: 'form-control', name: 'profile_name', required: true, value: profile.profile_name })
        ]),
        create('div', { className: 'grid grid-2' }, [
            create('div', { className: 'form-group' }, [
                create('label', { className: 'form-label' }, 'Tuổi'),
                create('input', { type: 'number', className: 'form-control', name: 'age', min: 0, max: 120, value: profile.age ?? '' })
            ]),
            create('div', { className: 'form-group' }, [
                create('label', { className: 'form-label' }, 'Giới tính'),
                (() => {
                    const sel = create('select', { className: 'form-control form-select', name: 'gender' }, [
                        create('option', { value: '' }, 'Chọn giới tính'),
                        create('option', { value: 'male' }, 'Nam'),
                        create('option', { value: 'female' }, 'Nữ'),
                        create('option', { value: 'other' }, 'Khác')
                    ]);
                    sel.value = profile.gender || '';
                    return sel;
                })()
            ])
        ]),
        create('div', { className: 'grid grid-2' }, [
            create('div', { className: 'form-group' }, [
                create('label', { className: 'form-label' }, 'Cân nặng (kg)'),
                create('input', { type: 'number', className: 'form-control', name: 'weight', step: 0.1, value: profile.weight ?? '' })
            ]),
            create('div', { className: 'form-group' }, [
                create('label', { className: 'form-label' }, 'Chiều cao (cm)'),
                create('input', { type: 'number', className: 'form-control', name: 'height', step: 0.1, value: profile.height ?? '' })
            ])
        ]),
        create('div', { className: 'form-group' }, [
            create('label', { className: 'form-label' }, 'Tình trạng sức khỏe'),
            create('textarea', { className: 'form-control', name: 'conditions_text', rows: 3, value: profile.conditions_text || '' })
        ]),
        // Conditions manager
        create('div', { className: 'form-group' }, [
            create('label', { className: 'form-label' }, 'Quản lý bệnh lý'),
            create('div', { className: 'd-flex align-center mb-2' }, [
                create('input', { id: 'edit-condition-input', type: 'text', className: 'form-control', placeholder: 'Nhập bệnh lý, Enter để thêm', onkeypress: (e) => { if (e.key === 'Enter'){ e.preventDefault(); addConditionItem(); } } }),
                create('button', { type: 'button', className: 'btn btn-primary', style: 'margin-left:8px;', onclick: addConditionItem }, [ create('i', { className: 'fas fa-plus' }), ' Thêm' ])
            ]),
            create('div', { id: 'edit-conditions-tags' }, list.map((name, idx) => create('span', {
                className: 'badge',
                style: 'display:inline-block;margin-right:8px;margin-bottom:6px;background:#eef2ff;color:#4f46e5;padding:6px 10px;border-radius:9999px;font-weight:600;'
            }, [ name, create('button', { type: 'button', style: 'margin-left:6px;background:transparent;border:none;color:#ef4444;cursor:pointer;', onclick: () => removeConditionItem(idx) }, '×') ]))),
            // Hidden textarea to keep list as newline for submit fallback
            create('textarea', { id: 'edit-conditions-list', className: 'd-none', rows: 3 }, list.join('\n'))
        ])
    ]);

    showModal('Sửa hồ sơ sức khỏe', form, [
        create('button', { className: 'btn btn-secondary', onclick: () => document.getElementById('modal-container').classList.add('hidden') }, 'Hủy'),
        create('button', { className: 'btn btn-primary', onclick: handleUpdateProfile }, 'Lưu')
    ]);
}

function addConditionItem(){
    const input = document.getElementById('edit-condition-input');
    const tags = document.getElementById('edit-conditions-tags');
    const hidden = document.getElementById('edit-conditions-list');
    if (!input || !tags || !hidden) return;
    const value = (input.value || '').trim();
    if (!value) return;
    const arr = (hidden.value || '').split('\n').map(s => s.trim()).filter(Boolean);
    arr.push(value);
    hidden.value = arr.join('\n');
    const idx = arr.length - 1;
    const span = document.createElement('span');
    span.className = 'badge';
    span.style = 'display:inline-block;margin-right:8px;margin-bottom:6px;background:#eef2ff;color:#4f46e5;padding:6px 10px;border-radius:9999px;font-weight:600;';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.style = 'margin-left:6px;background:transparent;border:none;color:#ef4444;cursor:pointer;';
    btn.textContent = '×';
    btn.onclick = () => removeConditionItem(idx);
    span.textContent = value;
    span.appendChild(btn);
    tags.appendChild(span);
    input.value = '';
}

function removeConditionItem(idx){
    const hidden = document.getElementById('edit-conditions-list');
    const tags = document.getElementById('edit-conditions-tags');
    if (!hidden || !tags) return;
    const arr = (hidden.value || '').split('\n').map(s => s.trim()).filter(Boolean);
    if (idx < 0 || idx >= arr.length) return;
    arr.splice(idx, 1);
    hidden.value = arr.join('\n');
    // Re-render tags quickly
    tags.innerHTML = '';
    arr.forEach((name, newIdx) => {
        const span = document.createElement('span');
        span.className = 'badge';
        span.style = 'display:inline-block;margin-right:8px;margin-bottom:6px;background:#eef2ff;color:#4f46e5;padding:6px 10px;border-radius:9999px;font-weight:600;';
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.style = 'margin-left:6px;background:transparent;border:none;color:#ef4444;cursor:pointer;';
        btn.textContent = '×';
        btn.onclick = () => removeConditionItem(newIdx);
        span.textContent = name;
        span.appendChild(btn);
        tags.appendChild(span);
    });
}

async function handleUpdateProfile(){
    const { api, showToast } = window.__APP__;
    const form = document.getElementById('edit-profile-form');
    if (!form) return;
    const profileId = form.getAttribute('data-id');
    const fd = new FormData(form);
    const data = {
        profile_name: fd.get('profile_name') || undefined,
        age: fd.get('age') ? parseInt(fd.get('age')) : undefined,
        gender: fd.get('gender') || undefined,
        weight: fd.get('weight') ? parseFloat(fd.get('weight')) : undefined,
        height: fd.get('height') ? parseFloat(fd.get('height')) : undefined,
        conditions_text: fd.get('conditions_text') || undefined,
        conditions_list: (document.getElementById('edit-conditions-list')?.value || '').split('\n').map(s => s.trim()).filter(Boolean)
    };
    try{
        await api(`/profiles/${profileId}`, { method: 'PUT', body: JSON.stringify(data) });
        document.getElementById('modal-container').classList.add('hidden');
        showToast('Đã cập nhật hồ sơ');
        renderProfiles();
    }catch(e){}
}

function confirmDeleteProfile(profile){
    const { create, showModal } = window.__APP__;
    const content = create('div', {}, 'Bạn có chắc muốn xóa hồ sơ này? Thao tác không thể hoàn tác.');
    showModal('Xác nhận xóa hồ sơ', content, [
        create('button', { className: 'btn btn-secondary', onclick: () => document.getElementById('modal-container').classList.add('hidden') }, 'Hủy'),
        create('button', { className: 'btn btn-danger', onclick: () => deleteProfile(profile.id) }, 'Xóa')
    ]);
}

async function deleteProfile(profileId){
    const { api, showToast } = window.__APP__;
    try{
        await api(`/profiles/${profileId}`, { method: 'DELETE' });
        document.getElementById('modal-container').classList.add('hidden');
        showToast('Đã xóa hồ sơ');
        renderProfiles();
    }catch(e){}
}