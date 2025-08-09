// Foods Page

async function renderFoods() {
    const { $, currentUser } = window.__APP__;
    const user = currentUser();
    
    const container = $('#page-container');
    container.style.padding = '2rem';
    container.style.background = 'rgba(255, 255, 255, 0.95)';
    
    const isAdmin = user?.role === 'admin';
    
    container.innerHTML = `
        <div class="page-header">
            <div class="d-flex justify-between align-center">
                <div>
                    <h1 class="page-title">
                        <i class="fas fa-seedling"></i>
                        Cơ sở dữ liệu thực phẩm
                    </h1>
                    <p class="page-subtitle">Tra cứu thông tin dinh dưỡng và chống chỉ định</p>
                </div>
                ${isAdmin ? `
                    <button class="btn btn-primary" onclick="showCreateFoodModal()">
                        <i class="fas fa-plus"></i>
                        Thêm thực phẩm
                    </button>
                ` : ''}
            </div>
        </div>
        
        <div class="card mb-3">
            <div class="card-body">
                <div class="d-flex align-center">
                    <input type="text" 
                           class="form-control" 
                           id="food-search" 
                           placeholder="Tìm kiếm thực phẩm..."
                           style="margin-right: 1rem;">
                    <button class="btn btn-primary" onclick="searchFoods()">
                        <i class="fas fa-search"></i>
                        Tìm kiếm
                    </button>
                </div>
            </div>
        </div>
        
        <div id="foods-list" class="grid grid-3">
            <div class="text-center">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Đang tải thực phẩm...</p>
            </div>
        </div>
    `;
    
    // Set up search
    $('#food-search').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchFoods();
        }
    });
    
    // Load initial foods
    try {
        const foods = await window.__APP__.api('/foods?limit=20');
        renderFoodsList(foods);
    } catch (error) {
        $('#foods-list').innerHTML = `
            <div class="text-center">
                <i class="fas fa-exclamation-triangle text-danger"></i>
                <h3>Không thể tải thực phẩm</h3>
                <p class="text-muted">${error.message}</p>
            </div>
        `;
    }
}

function renderFoodsList(foods) {
    const { create, currentUser } = window.__APP__;
    const user = currentUser();
    const isAdmin = user?.role === 'admin';
    
    const foodsList = $('#foods-list');
    foodsList.innerHTML = '';
    
    if (foods.length === 0) {
        foodsList.innerHTML = `
            <div class="card text-center" style="grid-column: 1 / -1;">
                <div class="card-body">
                    <i class="fas fa-search" style="font-size: 3rem; color: #667eea; margin-bottom: 1rem;"></i>
                    <h3>Không tìm thấy thực phẩm</h3>
                    <p class="text-muted">Thử tìm kiếm với từ khóa khác</p>
                </div>
            </div>
        `;
        return;
    }
    
    foods.forEach(food => {
        const foodCard = create('div', { className: 'card' }, [
            create('div', { className: 'card-header' }, [
                create('div', { className: 'd-flex justify-between align-center' }, [
                    create('h4', { className: 'card-title' }, food.name),
                    isAdmin ? create('button', { 
                        className: 'btn btn-sm btn-secondary',
                        onclick: () => showEditFoodModal(food)
                    }, 'Sửa') : ''
                ])
            ]),
            create('div', { className: 'card-body' }, [
                food.category ? create('p', {}, [
                    create('strong', {}, 'Loại: '),
                    food.category
                ]) : '',
                food.contraindications?.length > 0 ? create('div', { className: 'mb-2' }, [
                    create('strong', { className: 'text-danger' }, 'Chống chỉ định:'),
                    create('ul', { className: 'text-danger' }, 
                        food.contraindications.map(item => 
                            create('li', {}, item)
                        )
                    )
                ]) : '',
                food.benefits?.length > 0 ? create('div', { className: 'mb-2' }, [
                    create('strong', { className: 'text-success' }, 'Lợi ích:'),
                    create('ul', { className: 'text-success' }, 
                        food.benefits.slice(0, 3).map(item => 
                            create('li', {}, item)
                        )
                    )
                ]) : '',
                food.preparation_notes ? create('p', { className: 'text-muted' }, [
                    create('strong', {}, 'Ghi chú: '),
                    food.preparation_notes
                ]) : ''
            ])
        ]);
        
        foodsList.appendChild(foodCard);
    });
}

async function searchFoods() {
    const query = $('#food-search').value.trim();
    
    try {
        const foods = await window.__APP__.api(`/foods?query=${encodeURIComponent(query)}&limit=20`);
        renderFoodsList(foods);
    } catch (error) {
        window.__APP__.showToast(`Lỗi tìm kiếm: ${error.message}`, 'error');
    }
}

function showCreateFoodModal() {
    const { create } = window.__APP__;
    
    const form = create('form', { id: 'create-food-form' }, [
        create('div', { className: 'form-group' }, [
            create('label', { className: 'form-label' }, 'Tên thực phẩm *'),
            create('input', { 
                type: 'text',
                className: 'form-control',
                name: 'name',
                required: true,
                placeholder: 'VD: Cà rót'
            })
        ]),
        create('div', { className: 'grid grid-2' }, [
            create('div', { className: 'form-group' }, [
                create('label', { className: 'form-label' }, 'Loại'),
                create('input', { 
                    type: 'text',
                    className: 'form-control',
                    name: 'category',
                    placeholder: 'VD: Rau củ'
                })
            ]),
            create('div', { className: 'form-group' }, [
                create('label', { className: 'form-label' }, 'Phân loại chi tiết'),
                create('input', { 
                    type: 'text',
                    className: 'form-control',
                    name: 'subcategory',
                    placeholder: 'VD: Rau củ quả'
                })
            ])
        ]),
        create('div', { className: 'form-group' }, [
            create('label', { className: 'form-label' }, 'Chống chỉ định (mỗi dòng một mục)'),
            create('textarea', { 
                className: 'form-control',
                name: 'contraindications',
                rows: 3,
                placeholder: 'VD:\\nNgười bị dạ dày\\nPhụ nữ mang thai'
            })
        ]),
        create('div', { className: 'form-group' }, [
            create('label', { className: 'form-label' }, 'Lợi ích (mỗi dòng một mục)'),
            create('textarea', { 
                className: 'form-control',
                name: 'benefits',
                rows: 3,
                placeholder: 'VD:\\nGiàu vitamin C\\nTốt cho tim mạch'
            })
        ]),
        create('div', { className: 'form-group' }, [
            create('label', { className: 'form-label' }, 'Ghi chú chế biến'),
            create('textarea', { 
                className: 'form-control',
                name: 'preparation_notes',
                rows: 2,
                placeholder: 'Cách chế biến, bảo quản...'
            })
        ])
    ]);
    
    window.__APP__.showModal('Thêm thực phẩm mới', form, [
        create('button', { 
            className: 'btn btn-secondary',
            onclick: () => $('#modal-container').classList.add('hidden')
        }, 'Hủy'),
        create('button', { 
            className: 'btn btn-primary',
            onclick: handleCreateFood
        }, 'Thêm thực phẩm')
    ]);
}

async function handleCreateFood() {
    const { api, showToast } = window.__APP__;
    
    const form = $('#create-food-form');
    const formData = new FormData(form);
    
    const data = {
        name: formData.get('name'),
        category: formData.get('category') || null,
        subcategory: formData.get('subcategory') || null,
        contraindications: formData.get('contraindications') 
            ? formData.get('contraindications').split('\\n').filter(x => x.trim())
            : [],
        benefits: formData.get('benefits')
            ? formData.get('benefits').split('\\n').filter(x => x.trim())
            : [],
        preparation_notes: formData.get('preparation_notes') || null
    };
    
    try {
        await api('/foods', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        $('#modal-container').classList.add('hidden');
        showToast('Thêm thực phẩm thành công!');
        
        // Reload foods
        renderFoods();
    } catch (error) {
        // Error already handled by api function
    }
}

// Global functions
window.searchFoods = searchFoods;
window.showCreateFoodModal = showCreateFoodModal;
window.handleCreateFood = handleCreateFood;