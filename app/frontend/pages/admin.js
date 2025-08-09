// Admin Page

async function renderAdmin() {
    const { $, currentUser } = window.__APP__;
    const user = currentUser();
    
    const container = $('#page-container');
    container.style.padding = '2rem';
    container.style.background = 'rgba(255, 255, 255, 0.95)';
    
    if (user?.role !== 'admin') {
        container.innerHTML = `
            <div class="text-center mt-4">
                <i class="fas fa-lock" style="font-size: 4rem; color: #dc3545;"></i>
                <h2>Không có quyền truy cập</h2>
                <p class="text-muted">Chỉ admin mới có thể truy cập trang này</p>
                <a href="#/dashboard" class="btn btn-primary">Về trang chủ</a>
            </div>
        `;
        return;
    }
    
    container.innerHTML = `
        <div class="page-header">
            <h1 class="page-title">
                <i class="fas fa-cog"></i>
                Quản trị hệ thống
            </h1>
            <p class="page-subtitle">Thống kê và quản lý hệ thống</p>
        </div>
        
        <div id="admin-stats" class="grid grid-2">
            <div class="text-center">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Đang tải thống kê...</p>
            </div>
        </div>
    `;
    
    try {
        const stats = await window.__APP__.api('/stats');
        renderAdminStats(stats);
    } catch (error) {
        $('#admin-stats').innerHTML = `
            <div class="text-center">
                <i class="fas fa-exclamation-triangle text-danger"></i>
                <h3>Không thể tải thống kê</h3>
                <p class="text-muted">${error.message}</p>
            </div>
        `;
    }
}

function renderAdminStats(stats) {
    const { create } = window.__APP__;
    
    const adminStats = $('#admin-stats');
    adminStats.innerHTML = '';
    
    // System Stats Card
    const systemCard = create('div', { className: 'card' }, [
        create('div', { className: 'card-header' }, [
            create('h3', { className: 'card-title' }, [
                create('i', { className: 'fas fa-chart-bar' }),
                ' Thống kê hệ thống'
            ])
        ]),
        create('div', { className: 'card-body' }, [
            create('div', { className: 'grid grid-3' }, [
                create('div', { className: 'text-center' }, [
                    create('div', { 
                        style: 'font-size: 2rem; font-weight: bold; color: #667eea;'
                    }, stats.users.toString()),
                    create('div', { className: 'text-muted' }, 'Người dùng')
                ]),
                create('div', { className: 'text-center' }, [
                    create('div', { 
                        style: 'font-size: 2rem; font-weight: bold; color: #28a745;'
                    }, stats.health_profiles.toString()),
                    create('div', { className: 'text-muted' }, 'Hồ sơ sức khỏe')
                ]),
                create('div', { className: 'text-center' }, [
                    create('div', { 
                        style: 'font-size: 2rem; font-weight: bold; color: #ffc107;'
                    }, stats.foods.toString()),
                    create('div', { className: 'text-muted' }, 'Thực phẩm')
                ])
            ]),
            create('hr', { style: 'margin: 1.5rem 0;' }),
            create('div', { className: 'grid grid-2' }, [
                create('div', { className: 'text-center' }, [
                    create('div', { 
                        style: 'font-size: 1.5rem; font-weight: bold; color: #17a2b8;'
                    }, stats.documents.toString()),
                    create('div', { className: 'text-muted' }, 'Tài liệu y tế')
                ]),
                create('div', { className: 'text-center' }, [
                    create('div', { 
                        style: 'font-size: 1.5rem; font-weight: bold; color: #6f42c1;'
                    }, stats.chat_sessions.toString()),
                    create('div', { className: 'text-muted' }, 'Phiên tư vấn')
                ])
            ])
        ])
    ]);
    
    // Quick Actions Card
    const actionsCard = create('div', { className: 'card' }, [
        create('div', { className: 'card-header' }, [
            create('h3', { className: 'card-title' }, [
                create('i', { className: 'fas fa-tools' }),
                ' Thao tác quản trị'
            ])
        ]),
        create('div', { className: 'card-body' }, [
            create('div', { className: 'grid grid-2' }, [
                create('button', { 
                    className: 'btn btn-primary',
                    onclick: () => window.__APP__.navigateTo('/foods')
                }, [
                    create('i', { className: 'fas fa-seedling' }),
                    ' Quản lý thực phẩm'
                ]),
                create('button', { 
                    className: 'btn btn-secondary',
                    onclick: () => window.location.reload()
                }, [
                    create('i', { className: 'fas fa-sync-alt' }),
                    ' Làm mới thống kê'
                ]),
                create('button', { 
                    className: 'btn btn-info',
                    onclick: () => showSystemInfo()
                }, [
                    create('i', { className: 'fas fa-info-circle' }),
                    ' Thông tin hệ thống'
                ]),
                create('button', { 
                    className: 'btn btn-warning',
                    onclick: () => exportData()
                }, [
                    create('i', { className: 'fas fa-download' }),
                    ' Xuất dữ liệu'
                ])
            ])
        ])
    ]);
    
    // System Health Card
    const healthCard = create('div', { className: 'card', style: 'grid-column: 1 / -1;' }, [
        create('div', { className: 'card-header' }, [
            create('h3', { className: 'card-title' }, [
                create('i', { className: 'fas fa-heartbeat' }),
                ' Tình trạng hệ thống'
            ])
        ]),
        create('div', { className: 'card-body' }, [
            create('div', { className: 'grid grid-4' }, [
                create('div', { className: 'text-center' }, [
                    create('div', { 
                        className: 'text-success',
                        style: 'font-size: 2rem;'
                    }, [
                        create('i', { className: 'fas fa-check-circle' })
                    ]),
                    create('div', { className: 'mt-2' }, 'API Server'),
                    create('small', { className: 'text-muted' }, 'Hoạt động bình thường')
                ]),
                create('div', { className: 'text-center' }, [
                    create('div', { 
                        className: 'text-success',
                        style: 'font-size: 2rem;'
                    }, [
                        create('i', { className: 'fas fa-database' })
                    ]),
                    create('div', { className: 'mt-2' }, 'Database'),
                    create('small', { className: 'text-muted' }, 'Kết nối ổn định')
                ]),
                create('div', { className: 'text-center' }, [
                    create('div', { 
                        className: 'text-warning',
                        style: 'font-size: 2rem;'
                    }, [
                        create('i', { className: 'fas fa-robot' })
                    ]),
                    create('div', { className: 'mt-2' }, 'AI Service'),
                    create('small', { className: 'text-muted' }, 'Cần cấu hình Azure')
                ]),
                create('div', { className: 'text-center' }, [
                    create('div', { 
                        className: 'text-success',
                        style: 'font-size: 2rem;'
                    }, [
                        create('i', { className: 'fas fa-shield-alt' })
                    ]),
                    create('div', { className: 'mt-2' }, 'Security'),
                    create('small', { className: 'text-muted' }, 'JWT hoạt động')
                ])
            ])
        ])
    ]);
    
    [systemCard, actionsCard, healthCard].forEach(card => {
        adminStats.appendChild(card);
    });
}

function showSystemInfo() {
    const { create } = window.__APP__;
    
    const info = create('div', {}, [
        create('p', {}, [
            create('strong', {}, 'Phiên bản: '),
            '2.0.0'
        ]),
        create('p', {}, [
            create('strong', {}, 'Framework: '),
            'FastAPI + SQLite + Vanilla JS'
        ]),
        create('p', {}, [
            create('strong', {}, 'Tính năng chính: '),
            'Multi-user, Health profiles, AI chat, Document analysis'
        ]),
        create('p', {}, [
            create('strong', {}, 'Bảo mật: '),
            'JWT Authentication, Role-based access'
        ])
    ]);
    
    window.__APP__.showModal('Thông tin hệ thống', info, [
        create('button', { 
            className: 'btn btn-primary',
            onclick: () => $('#modal-container').classList.add('hidden')
        }, 'Đóng')
    ]);
}

function exportData() {
    window.__APP__.showToast('Tính năng xuất dữ liệu đang phát triển', 'info');
}

// Global functions
window.showSystemInfo = showSystemInfo;
window.exportData = exportData;
