// Authentication Page for ChatGPU Health

function renderAuth() {
    const { $, create, api, setAuthToken, loadCurrentUser, navigateTo } = window.__APP__;
    
    const container = $('#page-container');
    container.innerHTML = '';
    
    // Hide main container styling
    container.style.padding = '0';
    container.style.background = 'transparent';
    container.style.boxShadow = 'none';
    container.style.backdropFilter = 'none';
    
    const authContainer = create('div', { className: 'auth-container' }, [
        create('div', { className: 'auth-card' }, [
            create('div', { className: 'auth-header' }, [
                create('h1', { className: 'auth-title' }, 'ChatGPU Health'),
                create('p', { className: 'auth-subtitle' }, 'Tư vấn dinh dưỡng thông minh')
            ]),
            
            create('div', { className: 'auth-tabs' }, [
                create('div', { 
                    className: 'auth-tab active',
                    id: 'login-tab',
                    onclick: () => switchAuthTab('login')
                }, 'Đăng nhập'),
                create('div', { 
                    className: 'auth-tab',
                    id: 'register-tab',
                    onclick: () => switchAuthTab('register')
                }, 'Đăng ký')
            ]),
            
            // Login Form
            create('form', { 
                id: 'login-form',
                className: 'auth-form',
                onsubmit: handleLogin
            }, [
                create('div', { className: 'form-group' }, [
                    create('label', { className: 'form-label' }, 'Email'),
                    create('input', { 
                        type: 'email',
                        className: 'form-control',
                        name: 'email',
                        required: true,
                        placeholder: 'example@email.com'
                    })
                ]),
                create('div', { className: 'form-group' }, [
                    create('label', { className: 'form-label' }, 'Mật khẩu'),
                    create('input', { 
                        type: 'password',
                        className: 'form-control',
                        name: 'password',
                        required: true,
                        placeholder: '••••••••'
                    })
                ]),
                create('button', { 
                    type: 'submit',
                    className: 'btn btn-primary w-full'
                }, [
                    create('i', { className: 'fas fa-sign-in-alt' }),
                    ' Đăng nhập'
                ])
            ]),
            
            // Register Form
            create('form', { 
                id: 'register-form',
                className: 'auth-form hidden',
                onsubmit: handleRegister
            }, [
                create('div', { className: 'form-group' }, [
                    create('label', { className: 'form-label' }, 'Họ và tên'),
                    create('input', { 
                        type: 'text',
                        className: 'form-control',
                        name: 'full_name',
                        required: true,
                        placeholder: 'Nguyễn Văn A'
                    })
                ]),
                create('div', { className: 'form-group' }, [
                    create('label', { className: 'form-label' }, 'Email'),
                    create('input', { 
                        type: 'email',
                        className: 'form-control',
                        name: 'email',
                        required: true,
                        placeholder: 'example@email.com'
                    })
                ]),
                create('div', { className: 'form-group' }, [
                    create('label', { className: 'form-label' }, 'Mật khẩu'),
                    create('input', { 
                        type: 'password',
                        className: 'form-control',
                        name: 'password',
                        required: true,
                        minLength: 6,
                        placeholder: 'Tối thiểu 6 ký tự'
                    })
                ]),
                create('div', { className: 'form-group' }, [
                    create('label', { className: 'form-label' }, 'Xác nhận mật khẩu'),
                    create('input', { 
                        type: 'password',
                        className: 'form-control',
                        name: 'confirm_password',
                        required: true,
                        placeholder: 'Nhập lại mật khẩu'
                    })
                ]),
                create('button', { 
                    type: 'submit',
                    className: 'btn btn-primary w-full'
                }, [
                    create('i', { className: 'fas fa-user-plus' }),
                    ' Đăng ký'
                ])
            ]),
            
            // Demo Account Info
            create('div', { 
                className: 'auth-demo',
                style: 'margin-top: 2rem; padding: 1rem; background: #f8f9fa; border-radius: 8px; text-align: center;'
            }, [
                create('small', { className: 'text-muted' }, [
                    '💡 Tài khoản demo: ',
                    create('br'),
                    create('strong', {}, 'admin@example.com / admin123')
                ])
            ])
        ])
    ]);
    
    container.appendChild(authContainer);
}

function switchAuthTab(tab) {
    const { $ } = window.__APP__;
    
    // Update tabs
    $('#login-tab').classList.remove('active');
    $('#register-tab').classList.remove('active');
    $(`#${tab}-tab`).classList.add('active');
    
    // Update forms
    $('#login-form').classList.add('hidden');
    $('#register-form').classList.add('hidden');
    $(`#${tab}-form`).classList.remove('hidden');
}

async function handleLogin(e) {
    e.preventDefault();
    const { api, setAuthToken, loadCurrentUser, navigateTo, showToast } = window.__APP__;
    
    const formData = new FormData(e.target);
    const data = {
        email: formData.get('email'),
        password: formData.get('password')
    };
    
    try {
        const result = await api('/auth/login', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        setAuthToken(result.token);
        await loadCurrentUser();
        
        showToast('Đăng nhập thành công!');
        navigateTo('/dashboard');
    } catch (error) {
        // Error already handled by api function
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const { api, setAuthToken, loadCurrentUser, navigateTo, showToast } = window.__APP__;
    
    const formData = new FormData(e.target);
    const password = formData.get('password');
    const confirmPassword = formData.get('confirm_password');
    
    if (password !== confirmPassword) {
        showToast('Mật khẩu xác nhận không khớp', 'error');
        return;
    }
    
    const data = {
        email: formData.get('email'),
        password: password,
        full_name: formData.get('full_name')
    };
    
    try {
        const result = await api('/auth/register', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        setAuthToken(result.token);
        await loadCurrentUser();
        
        showToast('Đăng ký thành công! Chào mừng bạn đến với ChatGPU Health!');
        navigateTo('/dashboard');
    } catch (error) {
        // Error already handled by api function
    }
}
