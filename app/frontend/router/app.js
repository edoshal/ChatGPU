// ChatGPU Health App Router & Core Functions

let currentUser = null;
let currentProfile = null;
let authToken = null;

// Utilities
function $(selector) { return document.querySelector(selector); }
function $$(selector) { return document.querySelectorAll(selector); }

function create(tag, props = {}, children = []) {
    const element = document.createElement(tag);
    Object.assign(element, props);
    
    // Helper to flatten and append children
    function appendChild(child) {
        if (!child && child !== 0) return; // Skip falsy values except 0
        
        if (Array.isArray(child)) {
            // Flatten arrays
            child.forEach(appendChild);
        } else if (typeof child === 'string' || typeof child === 'number') {
            element.appendChild(document.createTextNode(String(child)));
        } else if (child instanceof Node) {
            element.appendChild(child);
        } else {
            console.warn('Invalid child type:', typeof child, child);
        }
    }
    
    if (typeof children === 'string' || typeof children === 'number') {
        element.textContent = String(children);
    } else if (Array.isArray(children)) {
        children.forEach(appendChild);
    } else if (children) {
        appendChild(children);
    }
    
    return element;
}

function showLoading() {
    $('#loading-overlay').classList.remove('hidden');
}

function hideLoading() {
    $('#loading-overlay').classList.add('hidden');
}

function showToast(message, type = 'success', duration = 5000) {
    const container = $('#toast-container');
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    
    const toast = create('div', { className: `toast ${type}` }, [
        create('i', { className: `toast-icon fas ${icons[type] || icons.success}` }),
        create('div', { className: 'toast-content' }, [message]),
        create('button', { 
            className: 'toast-close',
            innerHTML: '&times;',
            onclick: () => toast.remove()
        })
    ]);
    
    container.appendChild(toast);
    setTimeout(() => toast.remove(), duration);
}

// API Functions
async function api(endpoint, options = {}) {
    const { noLoading, ...opts } = options || {};
    const config = {
        headers: {
            'Content-Type': 'application/json',
            ...opts.headers
        },
        ...opts
    };
    
    if (authToken) {
        config.headers.Authorization = `Bearer ${authToken}`;
    }
    
    const url = endpoint.startsWith('/api/') ? endpoint : `/api${endpoint}`;
    
    try {
        if (!noLoading) showLoading();
        const response = await fetch(url, config);
        let data = null;
        try { data = await response.json(); } catch(e) {}
        
        if (!response.ok) {
            const detail = (data && (data.detail || data.message)) || `HTTP ${response.status}`;
            throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
        }
        
        return data ?? {};
    } catch (error) {
        console.error('API Error:', error);
        showToast(error.message || 'Có lỗi xảy ra', 'error');
        throw error;
    } finally {
        if (!noLoading) hideLoading();
    }
}

async function apiForm(endpoint, formData, options = {}) {
    const { noLoading, ...opts } = options || {};
    const config = {
        method: 'POST',
        body: formData,
        headers: {}
    };
    
    if (authToken) {
        config.headers.Authorization = `Bearer ${authToken}`;
    }
    
    const url = endpoint.startsWith('/api/') ? endpoint : `/api${endpoint}`;
    
    try {
        if (!noLoading) showLoading();
        const response = await fetch(url, config);
        let data = null;
        try { data = await response.json(); } catch(e) {}
        
        if (!response.ok) {
            const detail = (data && (data.detail || data.message)) || `HTTP ${response.status}`;
            throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
        }
        
        return data ?? {};
    } catch (error) {
        console.error('API Error:', error);
        showToast(error.message || 'Có lỗi xảy ra', 'error');
        throw error;
    } finally {
        if (!noLoading) hideLoading();
    }
}

// Auth Management
function setAuthToken(token) {
    authToken = token;
    if (token) {
        localStorage.setItem('auth_token', token);
    } else {
        localStorage.removeItem('auth_token');
    }
}

function getAuthToken() {
    return localStorage.getItem('auth_token');
}

function setCurrentProfile(profile) {
    currentProfile = profile;
    if (profile) {
        localStorage.setItem('current_profile_id', profile.id);
        updateProfileDisplay();
    } else {
        localStorage.removeItem('current_profile_id');
    }
}

function getCurrentProfileId() {
    return localStorage.getItem('current_profile_id');
}

async function loadCurrentUser() {
    try {
        const user = await api('/me');
        currentUser = user;
        updateUserDisplay();
        
    const storedId = getCurrentProfileId();
    if (storedId) {
        await loadCurrentProfile();
    } else if (user && user.default_profile_id) {
        try {
            const prof = await api(`/profiles/${user.default_profile_id}`);
            setCurrentProfile(prof);
        } catch (e) {}
    }
        
        return user;
    } catch (error) {
        console.error('Failed to load user:', error);
        logout();
        return null;
    }
}

async function loadCurrentProfile() {
    const profileId = getCurrentProfileId();
    if (!profileId) return null;
    
    try {
        const profile = await api(`/profiles/${profileId}`);
        currentProfile = profile;
        updateProfileDisplay();
        
        // Dispatch custom event for profile update
        window.dispatchEvent(new CustomEvent('profileUpdated', { detail: profile }));
        
        // Refresh dashboard if currently on dashboard page
        const currentPath = getCurrentRoute();
        if (currentPath === '/dashboard') {
            setTimeout(() => {
                const { renderDashboard } = window;
                if (renderDashboard) renderDashboard();
            }, 100); // Small delay to ensure profile is updated
        }
        
        return profile;
    } catch (error) {
        console.error('Failed to load profile:', error);
        localStorage.removeItem('current_profile_id');
        return null;
    }
}

function updateUserDisplay() {
    const userNameEl = $('#user-name');
    if (userNameEl && currentUser) {
        userNameEl.textContent = currentUser.full_name;
    }
    
    const adminNav = $('#admin-nav');
    // Toggle foods in dropdown for admin only
    const foodsDropdown = document.getElementById('foods-dropdown-item');
    if (foodsDropdown) {
        if (currentUser?.role === 'admin') foodsDropdown.classList.remove('hidden');
        else foodsDropdown.classList.add('hidden');
    }
}

function updateProfileDisplay() {
    const profileNameEl = $('#current-profile-name');
    const profileSelector = $('#profile-selector');
    
    if (profileNameEl && currentProfile) {
        profileNameEl.textContent = currentProfile.profile_name;
        profileSelector?.classList.remove('hidden');
    } else if (profileNameEl) {
        profileNameEl.textContent = 'Chọn hồ sơ';
        profileSelector?.classList.add('hidden');
    }
}

function logout() {
    setAuthToken(null);
    setCurrentProfile(null);
    currentUser = null;
    navigateTo('/auth');
}

// Router
const routes = {
    '/auth': () => renderAuth(),
    '/dashboard': () => renderDashboard(),
    // '/profiles': () => renderProfiles(), // Ẩn khỏi navbar; vẫn giữ route nếu cần truy cập từ nơi khác
    '/chat': () => renderChat(),
    '/documents': () => renderDocuments(),
    '/foods': () => renderFoods(),
    '/admin': () => renderAdmin(),
    '/settings': () => renderSettings()
};

function navigateTo(path) {
    window.location.hash = path;
}

function getCurrentRoute() {
    return window.location.hash.slice(1) || '/dashboard';
}

async function handleRoute() {
    const path = getCurrentRoute();
    const container = $('#page-container');
    
    if (!container) return;
    
    const token = getAuthToken();
    if (!token && path !== '/auth') {
        navigateTo('/auth');
        return;
    }
    
    if (token && !currentUser) {
        await loadCurrentUser();
    }
    
    if (token && currentUser) {
        $('#navbar').classList.remove('hidden');
        $('#mobile-nav').classList.remove('hidden');
        updateNavigation(path);
        // Nếu vào trang chat mà chưa có profile hiện tại, tự load mặc định
        if (path === '/chat' && !currentProfile) {
            await loadCurrentProfile();
        }
    } else {
        $('#navbar').classList.add('hidden');
        $('#mobile-nav').classList.add('hidden');
    }
    
    const renderFunction = routes[path];
    if (renderFunction) {
        try {
            await renderFunction();
        } catch (error) {
            console.error('Route error:', error);
            container.innerHTML = `
                <div class="text-center mt-2">
                    <h2>Có lỗi xảy ra</h2>
                    <p class="text-muted">${error.message}</p>
                    <button class="btn btn-primary" onclick="window.location.reload()">
                        Tải lại trang
                    </button>
                </div>
            `;
        }
    } else {
        container.innerHTML = `
            <div class="text-center mt-2">
                <h2>Trang không tìm thấy</h2>
                <p class="text-muted">Đường dẫn "${path}" không tồn tại.</p>
                <a href="#/dashboard" class="btn btn-primary">Về trang chủ</a>
            </div>
        `;
    }
}

function updateNavigation(currentPath) {
    $$('.nav-link').forEach(link => {
        const route = link.getAttribute('data-route');
        if (route) {
            if (`/${route}` === currentPath) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        }
    });
    
    $$('.mobile-nav-item').forEach(link => {
        const route = link.getAttribute('data-route');
        if (route) {
            if (`/${route}` === currentPath) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        }
    });
}

// Profile Management
async function loadUserProfiles() {
    try {
        const profiles = await api('/profiles');
        const profileList = $('#profile-list');
        
        if (profileList) {
            profileList.innerHTML = '';
            profiles.forEach(profile => {
                const item = create('div', {
                    className: `profile-item ${profile.id == getCurrentProfileId() ? 'active' : ''}`,
                    onclick: () => switchProfile(profile)
                }, [
                    create('i', { className: 'fas fa-user-circle' }),
                    create('span', {}, ` ${profile.profile_name}`),
                    ...(profile.is_default ? [create('small', { className: 'text-muted' }, ' (Mặc định)')] : [])
                ]);
                profileList.appendChild(item);
            });
        }
        
        return profiles;
    } catch (error) {
        console.error('Failed to load profiles:', error);
        return [];
    }
}

async function switchProfile(profile) {
    setCurrentProfile(profile);
    await loadUserProfiles();
    showToast(`Đã chuyển sang hồ sơ: ${profile.profile_name}`);
    await handleRoute();
}

async function createNewProfile() {
    const profileName = prompt('Tên hồ sơ mới:');
    if (!profileName?.trim()) return;
    
    try {
        await api('/profiles', {
            method: 'POST',
            body: JSON.stringify({
                profile_name: profileName.trim(),
                is_default: false
            })
        });
        
        showToast('Tạo hồ sơ thành công');
        await loadUserProfiles();
    } catch (error) {
        // Error already handled by api function
    }
}

// Global Functions
window.logout = logout;
window.createNewProfile = createNewProfile;
window.navigateTo = navigateTo;

// Initialize App
function initializeApp() {
    authToken = getAuthToken();
    window.addEventListener('hashchange', handleRoute);
    handleRoute();
    
    if (authToken) {
        loadUserProfiles();
    }
}

// Export for modules
window.__APP__ = {
    $, $$, create, showLoading, hideLoading, showToast,
    api, apiForm, navigateTo, setAuthToken, setCurrentProfile,
    loadCurrentUser, loadCurrentProfile, loadUserProfiles, switchProfile,
    getCurrentRoute, 
    currentUser: () => currentUser, 
    currentProfile: () => currentProfile
};

// Auto-init
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    initializeApp();
}

