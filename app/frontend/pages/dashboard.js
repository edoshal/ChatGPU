// Dashboard Page for ChatGPU Health

async function renderDashboard() {
    const { $, create, api, currentProfile } = window.__APP__;
    
    const container = $('#page-container');
    container.style.padding = '2rem';
    container.style.background = 'rgba(255, 255, 255, 0.95)';
    container.style.boxShadow = '0 8px 32px rgba(0, 0, 0, 0.1)';
    container.style.backdropFilter = 'blur(20px)';
    
    const profile = currentProfile();
    
    container.innerHTML = `
        <div class="page-header">
            <h1 class="page-title">
                <i class="fas fa-heartbeat"></i>
                Tình trạng sức khỏe
            </h1>
            <p class="page-subtitle">${profile ? `Hồ sơ: ${profile.profile_name}` : 'Chưa chọn hồ sơ'}</p>
        </div>
        
        <div id="dashboard-content" class="grid grid-2">
            <div class="loading text-center">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Đang tải dữ liệu...</p>
            </div>
        </div>
    `;
    
    try {
        // Load user stats and recent data
        const [profiles, recentChats] = await Promise.all([
            api('/profiles'),
            profile ? api(`/profiles/${profile.id}/chats`).catch(() => []) : Promise.resolve([])
        ]);
        
        renderDashboardContent(profiles, recentChats.slice(0, 5));
    } catch (error) {
        $('#dashboard-content').innerHTML = `
            <div class="col-span-2 text-center">
                <i class="fas fa-exclamation-triangle text-warning"></i>
                <h3>Không thể tải dữ liệu</h3>
                <p class="text-muted">${error.message}</p>
                <button class="btn btn-primary" onclick="window.location.reload()">
                    Thử lại
                </button>
            </div>
        `;
    }
}

function renderDashboardContent(profiles, recentChats) {
    const { create, navigateTo } = window.__APP__;
    const profile = window.__APP__.currentProfile();
    const parsed = (() => {
        const cj = profile && profile.conditions_json ? profile.conditions_json : {};
        if (typeof cj === 'string') {
            try { return JSON.parse(cj); } catch { return {}; }
        }
        return cj || {};
    })();
    const conditionsList = Array.isArray(parsed.conditions_list) ? parsed.conditions_list : [];
    const bmi = (() => {
        if (!profile || !profile.weight || !profile.height) return null;
        const h = Number(profile.height) / 100;
        if (!h) return null;
        const value = Number(profile.weight) / (h * h);
        return isFinite(value) ? Math.round(value * 10) / 10 : null;
    })();
    
    const dashboardContent = $('#dashboard-content');
    dashboardContent.innerHTML = '';
    
    // Health Status Card
    const statsCard = create('div', { className: 'card' }, [
        create('div', { className: 'card-header' }, [
            create('h3', { className: 'card-title' }, [
                create('i', { className: 'fas fa-notes-medical' }),
                ' Tình trạng hiện tại'
            ])
        ]),
        create('div', { className: 'card-body' }, [
            profile && profile.conditions_text
                ? create('div', { className: 'mb-3' }, [
                    create('div', { className: 'text-muted' }, profile.conditions_text)
                ])
                : create('div', { className: 'text-muted mb-3' }, 'Chưa có mô tả tình trạng.'),
            conditionsList.length
                ? create('div', { className: 'mb-3' }, [
                    create('strong', {}, 'Bệnh lý: '),
                    create('div', {}, conditionsList.map(name => 
                        create('span', {
                            className: 'badge',
                            style: 'display:inline-block;margin-right:8px;margin-bottom:6px;background:#eef2ff;color:#4f46e5;padding:6px 10px;border-radius:9999px;font-weight:600;'
                        }, name)
                    ))
                ])
                : '',
            create('div', { className: 'grid grid-3' }, [
                create('div', {}, [
                    create('div', { className: 'text-muted mb-1' }, 'Tuổi'),
                    create('div', { className: 'text-lg' }, profile?.age ?? '-')
                ]),
                create('div', {}, [
                    create('div', { className: 'text-muted mb-1' }, 'Giới tính'),
                    create('div', { className: 'text-lg' }, profile?.gender === 'male' ? 'Nam' : profile?.gender === 'female' ? 'Nữ' : (profile?.gender ? 'Khác' : '-'))
                ]),
                create('div', {}, [
                    create('div', { className: 'text-muted mb-1' }, 'BMI'),
                    create('div', { className: 'text-lg' }, bmi ?? '-')
                ]),
                create('div', {}, [
                    create('div', { className: 'text-muted mb-1' }, 'Cân nặng'),
                    create('div', { className: 'text-lg' }, profile?.weight ? `${profile.weight} kg` : '-')
                ]),
                create('div', {}, [
                    create('div', { className: 'text-muted mb-1' }, 'Chiều cao'),
                    create('div', { className: 'text-lg' }, profile?.height ? `${profile.height} cm` : '-')
                ])
            ])
        ])
    ]);
    
    // Profile Status Card
    const profileCard = create('div', { className: 'card' }, [
        create('div', { className: 'card-header' }, [
            create('h3', { className: 'card-title' }, [
                create('i', { className: 'fas fa-user-circle' }),
                ' Hồ sơ sức khỏe'
            ]),
            create('button', { 
                className: 'btn btn-sm btn-primary',
                onclick: () => navigateTo('/profiles')
            }, 'Quản lý')
        ]),
        create('div', { className: 'card-body' }, 
            profile ? [
                create('div', { className: 'mb-2' }, [
                    create('strong', {}, 'Hồ sơ hiện tại: '),
                    profile.profile_name
                ]),
                profile.age ? create('div', { className: 'mb-2' }, [
                    create('strong', {}, 'Tuổi: '),
                    profile.age.toString()
                ]) : '',
                profile.gender ? create('div', { className: 'mb-2' }, [
                    create('strong', {}, 'Giới tính: '),
                    profile.gender === 'male' ? 'Nam' : profile.gender === 'female' ? 'Nữ' : 'Khác'
                ]) : '',
                profile.conditions_text ? create('div', { className: 'mb-2' }, [
                    create('strong', {}, 'Tình trạng sức khỏe: '),
                    create('div', { className: 'text-muted' }, profile.conditions_text)
                ]) : ''
            ] : [
                create('div', { className: 'text-center text-muted' }, [
                    create('i', { className: 'fas fa-exclamation-circle' }),
                    create('p', {}, 'Chưa chọn hồ sơ sức khỏe'),
                    create('button', { 
                        className: 'btn btn-primary',
                        onclick: () => navigateTo('/profiles')
                    }, 'Tạo hồ sơ đầu tiên')
                ])
            ]
        )
    ]);
    
    // Quick Actions Card
    const actionsCard = create('div', { className: 'card' }, [
        create('div', { className: 'card-header' }, [
            create('h3', { className: 'card-title' }, [
                create('i', { className: 'fas fa-stethoscope' }),
                ' Tư vấn sức khỏe'
            ])
        ]),
        create('div', { className: 'card-body' }, [
            create('div', { className: 'grid grid-2' }, [
                create('button', { 
                    className: 'btn btn-primary',
                    onclick: () => navigateTo('/chat'),
                    disabled: !profile
                }, [
                    create('i', { className: 'fas fa-comments' }),
                    ' Mở chat sức khỏe'
                ]),
                create('button', { 
                    className: 'btn btn-success',
                    onclick: () => navigateTo('/profiles')
                }, [
                    create('i', { className: 'fas fa-user-plus' }),
                    ' Tạo hồ sơ mới'
                ]),
                create('button', { 
                    className: 'btn btn-secondary',
                    onclick: () => navigateTo('/foods'),
                    disabled: !profile
                }, [
                    create('i', { className: 'fas fa-search' }),
                    ' Tra cứu thực phẩm'
                ])
            ])
        ])
    ]);
    
    // Disease Status Card
    const diseaseCard = create('div', { className: 'card' }, [
        create('div', { className: 'card-header' }, [
            create('h3', { className: 'card-title' }, [
                create('i', { className: 'fas fa-viruses' }),
                ' Tình trạng bệnh lý'
            ])
        ]),
        create('div', { className: 'card-body' }, [
            conditionsList.length
                ? create('div', {}, conditionsList.map(name => 
                    create('span', {
                        className: 'badge',
                        style: 'display:inline-block;margin-right:8px;margin-bottom:6px;background:#fde68a;color:#92400e;padding:6px 10px;border-radius:9999px;font-weight:600;'
                    }, name)
                ))
                : create('div', { className: 'text-muted' }, 'Chưa có bệnh lý được khai báo.')
        ])
    ]);

    // Health Overview Card
    const bmiCategory = (() => {
        if (bmi == null) return '-';
        if (bmi < 18.5) return 'Gầy';
        if (bmi < 23) return 'Bình thường';
        if (bmi < 25) return 'Thừa cân';
        if (bmi < 30) return 'Tiền béo phì';
        return 'Béo phì';
    })();
    const overviewCard = create('div', { className: 'card' }, [
        create('div', { className: 'card-header' }, [
            create('h3', { className: 'card-title' }, [
                create('i', { className: 'fas fa-chart-line' }),
                ' Tổng quan sức khỏe'
            ])
        ]),
        create('div', { className: 'card-body' }, [
            create('div', { className: 'grid grid-2' }, [
                create('div', {}, [
                    create('div', { className: 'text-muted mb-1' }, 'BMI'),
                    create('div', { className: 'text-xl' }, bmi ?? '-')
                ]),
                create('div', {}, [
                    create('div', { className: 'text-muted mb-1' }, 'Phân loại'),
                    create('div', { className: 'text-xl' }, bmiCategory)
                ])
            ]),
            create('div', { className: 'mt-2 text-muted' },
                (bmi == null)
                    ? 'Chưa đủ dữ liệu để tính BMI. Hãy bổ sung cân nặng/chiều cao.'
                    : (bmi < 18.5
                        ? 'Bạn đang dưới ngưỡng cân nặng khuyến nghị. Hãy tham khảo chuyên gia dinh dưỡng.'
                        : (bmi <= 25
                            ? 'Chỉ số BMI trong khoảng lành mạnh. Tiếp tục duy trì thói quen tốt.'
                            : 'BMI cao hơn mức khuyến nghị. Cân nhắc điều chỉnh chế độ ăn/luyện tập.'))
            )
        ])
    ]);

    // Recent Activity Card
    const activityCard = create('div', { className: 'card' }, [
        create('div', { className: 'card-header' }, [
            create('h3', { className: 'card-title' }, [
                create('i', { className: 'fas fa-history' }),
                ' Tư vấn gần đây'
            ])
        ]),
        create('div', { className: 'card-body' }, 
            (recentChats.length > 0) ? [
                // Recent chats
                create('h5', { className: 'mb-2' }, 'Phiên tư vấn gần nhất:'),
                ...recentChats.map(chat => 
                    create('div', { 
                        className: 'mb-2 p-2',
                        style: 'border-left: 3px solid #667eea; background: #f8f9fa; border-radius: 4px;'
                    }, [
                        create('div', { className: 'font-semibold' }, chat.session_name || 'Phiên tư vấn'),
                        create('small', { className: 'text-muted' }, 
                            new Date(chat.last_message_at).toLocaleString('vi-VN')
                        )
                    ])
                )
            ] : [
                create('div', { className: 'text-center text-muted' }, [
                    create('i', { className: 'fas fa-inbox' }),
                    create('p', {}, 'Chưa có hoạt động nào')
                ])
            ]
        )
    ]);
    
    // Add all cards to dashboard
    [statsCard, diseaseCard, overviewCard, profileCard, actionsCard, activityCard].forEach(card => {
        dashboardContent.appendChild(card);
    });
}