/**
 * Health Planning Page
 * Quản lý kế hoạch sức khỏe cá nhân
 */

export function renderHealthPlans() {
    const content = createHealthPlansPage();
    document.getElementById('page-container').innerHTML = content;
    initHealthPlansPage();
}

export function createHealthPlansPage() {
    return `
        <div class="health-plans-page">
            <div class="page-header">
                <h1><i class="fas fa-heartbeat"></i> Kế Hoạch Sức Khỏe</h1>
                <button class="btn btn-primary" id="create-plan-btn">
                    <i class="fas fa-plus"></i> Tạo Kế Hoạch Mới
                </button>
            </div>

            <!-- Plans List -->
            <div class="plans-section">
                <h2>Kế Hoạch Hiện Tại</h2>
                <div id="plans-list" class="plans-grid">
                    <div class="loading">Đang tải...</div>
                </div>
            </div>

            <!-- Weekly Timeline -->
            <div class="weekly-section">
                <h2>Lịch Tập Theo Tuần</h2>
                <div id="weekly-timeline" class="weekly-timeline">
                    <div class="loading">Đang tải lịch tuần...</div>
                </div>
            </div>

            <!-- Daily Progress -->
            <div class="daily-section">
                <h2>Tiến Độ Hôm Nay</h2>
                <div id="daily-progress" class="progress-card">
                    <div class="loading">Đang tải...</div>
                </div>
            </div>

            <!-- Activity & Meal Logs -->
            <div class="logs-section">
                <div class="logs-grid">
                    <div class="activity-logs">
                        <div class="logs-header">
                            <h3><i class="fas fa-running"></i> Hoạt Động Gần Đây</h3>
                            <button class="btn btn-sm btn-outline-primary" id="auto-match-btn" title="Tự động liên kết với kế hoạch">
                                <i class="fas fa-link"></i> Liên kết tự động
                            </button>
                        </div>
                        <div id="activity-logs-list"></div>
                    </div>
                    <div class="meal-logs">
                        <h3><i class="fas fa-utensils"></i> Bữa Ăn Gần Đây</h3>
                        <div id="meal-logs-list"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Create Plan Modal -->
        <div id="create-plan-modal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Tạo Kế Hoạch Sức Khỏe Mới</h3>
                    <button class="modal-close" type="button">&times;</button>
                </div>
                <form id="create-plan-form">
                    <!-- Current Status Section -->
                    <div class="form-section">
                        <h4><i class="fas fa-user"></i> Tình Trạng Hiện Tại</h4>
                        <div class="current-status">
                            <div class="status-item">
                                <label>Cân nặng hiện tại:</label>
                                <div class="status-value">
                                    <input type="number" id="current-weight" step="0.1" min="20" max="300" inputmode="decimal" placeholder="Chưa có">
                                    <span class="unit">kg</span>
                                </div>
                            </div>
                            <div class="status-item">
                                <label>Chiều cao:</label>
                                <div class="status-value">
                                    <input type="number" id="current-height" step="0.1" min="50" max="250" inputmode="decimal" placeholder="Chưa có">
                                    <span class="unit">cm</span>
                                </div>
                            </div>
                            <div class="status-item">
                                <label>Tuổi:</label>
                                <div class="status-value">
                                    <input type="number" id="current-age" min="1" max="120" inputmode="numeric" placeholder="Chưa có">
                                    <span class="unit">tuổi</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Plan Details Section -->
                    <div class="form-section">
                        <h4><i class="fas fa-target"></i> Chi Tiết Kế Hoạch</h4>
                        
                        <div class="form-group">
                            <label for="plan-title">Tên Kế Hoạch:</label>
                            <input type="text" id="plan-title" name="title" required 
                                   placeholder="VD: Tăng cân lên 55kg trong 3 tháng">
                        </div>

                        <div class="form-row">
                            <div class="form-group w-full">
                                <label>Mục Tiêu (chọn nhiều):</label>
                                <div class="badge-input-group">
                                    <div id="selected-goals" class="badge-container"></div>
                                    <div class="add-badge-input">
                                        <button type="button" class="add-badge-btn" id="add-goal-btn">
                                            <i class="fas fa-plus"></i> Thêm mục tiêu
                                        </button>
                                        <div class="autocomplete-container" id="goal-autocomplete" style="display: none;">
                                            <input type="text" id="goal-input" placeholder="Nhập mục tiêu...">
                                            <div class="autocomplete-suggestions" id="goal-suggestions"></div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="form-row">
                            <div class="form-group">
                                <label for="target-value">Giá Trị Mục Tiêu:</label>
                                <input type="number" id="target-value" name="target_value" 
                                       step="0.1" required placeholder="55">
                            </div>
                            <div class="form-group">
                                <label for="target-unit">Đơn Vị:</label>
                                <select id="target-unit" name="target_unit" required>
                                    <option value="kg">kg (cân nặng)</option>
                                    <option value="cm">cm (chiều cao)</option>
                                    <option value="%">% (tỷ lệ cơ/mỡ)</option>
                                    <option value="bmi">BMI</option>
                                    <option value="minutes">phút (thời gian tập)</option>
                                    <option value="reps">lần (số lần tập)</option>
                                    <option value="sets">sets (số bộ tập)</option>
                                    <option value="mmHg">mmHg (huyết áp)</option>
                                    <option value="mg/dl">mg/dL (đường huyết)</option>
                                </select>
                            </div>
                        </div>

                        <div class="form-row">
                            <div class="form-group">
                                <label for="duration-days">Thời Gian (ngày):</label>
                                <select id="duration-days" name="duration_days" required>
                                    <option value="">-- Chọn thời gian --</option>
                                    <option value="7">1 tuần</option>
                                    <option value="14">2 tuần</option>
                                    <option value="30">1 tháng</option>
                                    <option value="60">2 tháng</option>
                                    <option value="90">3 tháng</option>
                                    <option value="120">4 tháng</option>
                                    <option value="180">6 tháng</option>
                                    <option value="365">1 năm</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="start-date">Ngày Bắt Đầu:</label>
                                <input type="date" id="start-date" name="start_date" required>
                            </div>
                        </div>
                    </div>

                    <!-- Activities Section -->
                    <div class="form-section">
                        <h4><i class="fas fa-running"></i> Hoạt Động Có Thể Thực Hiện</h4>
                        <div class="badge-input-group">
                            <div id="selected-activities" class="badge-container"></div>
                            <div class="add-badge-input">
                                <button type="button" class="add-badge-btn" id="add-activity-btn">
                                    <i class="fas fa-plus"></i> Thêm hoạt động
                                </button>
                                <div class="autocomplete-container" id="activity-autocomplete" style="display: none;">
                                    <input type="text" id="activity-input" placeholder="Nhập tên hoạt động...">
                                    <div class="autocomplete-suggestions" id="activity-suggestions"></div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Dietary Restrictions Section (Ẩn - để AI tự quyết định) -->

                    <div class="form-actions">
                        <button type="button" class="btn btn-secondary" data-dismiss="modal">Hủy</button>
                        <button type="submit" class="btn btn-primary">Tạo Kế Hoạch</button>
                    </div>
                </form>
            </div>
        </div>

        <!-- Plan Detail Modal -->
        <div id="plan-detail-modal" class="modal">
            <div class="modal-content modal-large">
                <div class="modal-header">
                    <h3 id="plan-detail-title">Chi Tiết Kế Hoạch</h3>
                    <span class="close">&times;</span>
                </div>
                <div id="plan-detail-content">
                    <!-- Dynamic content -->
                </div>
            </div>
        </div>
    `;
}

export function initHealthPlansPage() {
    const profileId = getCurrentProfileId();
    if (!profileId) {
        // Chưa có hồ sơ hiện tại: hiển thị trạng thái rỗng thân thiện và không gọi API
        const plansList = document.getElementById('plans-list');
        if (plansList) plansList.innerHTML = '<div class="empty-state">Hãy chọn hoặc tạo hồ sơ trước</div>';
        const daily = document.getElementById('daily-progress');
        if (daily) daily.innerHTML = '<div class="empty-state">Chưa có hồ sơ để hiển thị</div>';
        const act = document.getElementById('activity-logs-list');
        if (act) act.innerHTML = '<p class="empty">Chưa có hồ sơ</p>';
        const meals = document.getElementById('meal-logs-list');
        if (meals) meals.innerHTML = '<p class="empty">Chưa có hồ sơ</p>';
    } else {
        loadPlans();
        loadMonthlyTimeline();
        loadDailyProgress();
        loadActivityLogs();
        loadMealLogs();
    }
    initEventListeners();
    loadCurrentProfile();
    
    // Set default start date to today
    document.getElementById('start-date').value = new Date().toISOString().split('T')[0];
}

// Available activities and restrictions data
const AVAILABLE_GOALS = [
    { value: 'weight_gain', label: 'Tăng cân' },
    { value: 'weight_loss', label: 'Giảm cân' },
    { value: 'weight_maintain', label: 'Duy trì cân nặng' },
    { value: 'muscle_gain', label: 'Tăng cơ bắp' },
    { value: 'fat_loss', label: 'Giảm mỡ' },
    { value: 'body_recomp', label: 'Tái tạo cơ thể' },
    { value: 'endurance', label: 'Tăng sức bền' },
    { value: 'strength', label: 'Tăng sức mạnh' },
    { value: 'flexibility', label: 'Tăng dẻo dai' },
    { value: 'recovery', label: 'Phục hồi' },
    { value: 'height_growth', label: 'Phát triển chiều cao' },
    { value: 'healthy_growth', label: 'Phát triển toàn diện' },
    { value: 'bone_health', label: 'Xương khớp' },
    { value: 'balance', label: 'Thăng bằng' },
    { value: 'cognitive', label: 'Trí não' },
    { value: 'diabetes_control', label: 'Kiểm soát tiểu đường' },
    { value: 'blood_pressure', label: 'Huyết áp' },
    { value: 'heart_health', label: 'Tim mạch' }
];
const AVAILABLE_ACTIVITIES = [
    'Bơi lội', 'Chạy bộ', 'Tập gym', 'Đá bóng', 'Cầu lông', 'Yoga', 'Đi bộ',
    'Tennis', 'Bóng rổ', 'Bóng chuyền', 'Cano/kayak', 'Leo núi', 'Đạp xe', 'Nhảy dây',
    'Pilates', 'Aerôbic', 'Zumba', 'CrossFit', 'Boxing', 'Martial Arts', 'Dance',
    'Quần vợt', 'Bóng bàn', 'Golf', 'Tập xà', 'Weightlifting', 'Cardio',
    'HIIT', 'Stretching', 'Meditation', 'Thái cực', 'Qi Gong'
];

const AVAILABLE_RESTRICTIONS = [
    'Chay', 'Không sữa', 'Không gluten', 'Ít muối', 'Tiểu đường',
    'Không đường', 'Không chất béo trans', 'Thực phẩm hữu cơ', 'Paleo',
    'Keto', 'Mediterranean', 'DASH', 'Không caffeine', 'Không rượu',
    'Không đồ ăn nhanh', 'Không thịt đỏ', 'Không hải sản', 'Không đậu phộng',
    'Không trứng', 'Không đậu nành', 'Không MSG', 'Halal', 'Kosher'
];

// Selected items storage
let selectedActivities = [];
let selectedRestrictions = [];
let selectedGoals = [];

function getGoalLabelByValue(value) {
    const found = AVAILABLE_GOALS.find(g => g.value === value);
    return found ? found.label : value;
}

function getGoalValueByLabel(label) {
    const found = AVAILABLE_GOALS.find(g => g.label.toLowerCase() === label.toLowerCase());
    return found ? found.value : label; // fallback: use label as value
}

function initEventListeners() {
    // Create plan button
    document.getElementById('create-plan-btn').addEventListener('click', () => {
        showModal('create-plan-modal');
        loadCurrentProfile(); // Reload profile data when opening modal
    });

    // Create plan form
    document.getElementById('create-plan-form').addEventListener('submit', handleCreatePlan);

    // Modal close buttons
    document.querySelectorAll('.modal .modal-close, [data-dismiss="modal"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal');
            hideModal(modal.id);
        });
    });

    // Close modal on outside click
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            hideModal(e.target.id);
        }
    });

    // Badge input handlers (activities + goals)
    setupBadgeInputs();

    // Goal multi-select handlers
    document.getElementById('add-goal-btn').addEventListener('click', () => showAutocomplete('goal'));
    setupAutocomplete('goal', AVAILABLE_GOALS.map(g => g.label), selectedGoals, 'selected-goals');

    // Current status update handlers
    document.getElementById('current-weight').addEventListener('change', updateProfileField);
    document.getElementById('current-height').addEventListener('change', updateProfileField);
    document.getElementById('current-age').addEventListener('change', updateProfileField);
    
    // Auto-match activities button
    document.getElementById('auto-match-btn').addEventListener('click', autoMatchActivities);
}

async function loadPlans() {
    try {
        const profileId = getCurrentProfileId();
        if (!profileId) {
            return;
        }

        const response = await fetch(`/api/profiles/${profileId}/health-plans`, {
            headers: {
                'Authorization': `Bearer ${getToken()}`
            }
        });

        if (response.ok) {
            const plans = await response.json();
            renderPlans(plans);
        } else {
            throw new Error('Failed to load plans');
        }
    } catch (error) {
        console.error('Error loading plans:', error);
        document.getElementById('plans-list').innerHTML = 
            '<div class="error">Không thể tải kế hoạch</div>';
    }
}

function renderPlans(plans) {
    const container = document.getElementById('plans-list');
    
    if (plans.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-clipboard-list"></i>
                <h3>Chưa có kế hoạch nào</h3>
                <p>Hãy tạo kế hoạch sức khỏe đầu tiên của bạn! Chúng tôi sẽ giúp bạn xây dựng lộ trình phù hợp với tuổi tác và mục tiêu của bạn.</p>
                <div class="age-suggestions">
                    <h4>Gợi ý theo độ tuổi:</h4>
                    <div class="age-cards">
                        <div class="age-card" onclick="suggestPlanForAge('teen')">
                            <i class="fas fa-child"></i>
                            <span>13-18 tuổi</span>
                            <small>Phát triển chiều cao, cân nặng cân đối</small>
                        </div>
                        <div class="age-card" onclick="suggestPlanForAge('adult')">
                            <i class="fas fa-user"></i>
                            <span>19-40 tuổi</span>
                            <small>Tăng cơ, giảm mỡ, thể hình đẹp</small>
                        </div>
                        <div class="age-card" onclick="suggestPlanForAge('middle')">
                            <i class="fas fa-user-tie"></i>
                            <span>40-60 tuổi</span>
                            <small>Duy trì sức khỏe, phòng bệnh</small>
                        </div>
                        <div class="age-card" onclick="suggestPlanForAge('senior')">
                            <i class="fas fa-user-alt"></i>
                            <span>60+ tuổi</span>
                            <small>Xương khớp, thăng bằng, trí nhớ</small>
                        </div>
                    </div>
                </div>
            </div>
        `;
        return;
    }

    container.innerHTML = plans.map(plan => `
        <div class="plan-card ${plan.status}" data-plan-id="${plan.id}">
            <div class="plan-header">
                <h3>${plan.title}</h3>
                <span class="status-badge status-${plan.status}">${getStatusText(plan.status)}</span>
            </div>
            <div class="plan-info">
                <div class="goal">
                    <strong>${getGoalTypeText(plan.goal_type)}:</strong> 
                    ${plan.target_value} ${plan.target_unit}
                </div>
                <div class="progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${(plan.current_progress / plan.target_value * 100).toFixed(1)}%"></div>
                    </div>
                    <span class="progress-text">${plan.current_progress}/${plan.target_value} ${plan.target_unit}</span>
                </div>
                <div class="dates">
                    <span><i class="fas fa-calendar-start"></i> ${formatDate(plan.start_date)}</span>
                    <span><i class="fas fa-calendar-end"></i> ${formatDate(plan.end_date)}</span>
                </div>
            </div>
            <div class="plan-footer">
                <button class="btn-icon adjust" title="Điều chỉnh" onclick="adjustPlan(${plan.id})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn-icon delete" title="Xóa kế hoạch" onclick="deletePlan(${plan.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

async function loadDailyProgress() {
    try {
        const profileId = getCurrentProfileId();
        if (!profileId) {
            return;
        }
        const plans = await fetch(`/api/profiles/${profileId}/health-plans?status=active`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        }).then(r => r.json());

        if (plans.length === 0) {
            document.getElementById('daily-progress').innerHTML = 
                '<div class="empty-state">Không có kế hoạch đang hoạt động</div>';
            return;
        }

        const activePlan = plans[0];
        const today = new Date().toISOString().split('T')[0];
        
        const dailySummary = await fetch(`/api/health-plans/${activePlan.id}/daily/${today}`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        }).then(r => r.json());

        renderDailyProgress(dailySummary, activePlan);
    } catch (error) {
        console.error('Error loading daily progress:', error);
        document.getElementById('daily-progress').innerHTML = 
            '<div class="error">Không thể tải tiến độ hôm nay</div>';
    }
}

function renderDailyProgress(summary, plan) {
    const container = document.getElementById('daily-progress');
    const completionRate = summary.completion_rate || 0;
    
    container.innerHTML = `
        <div class="progress-overview">
            <h3>${plan.title}</h3>
            <div class="completion-circle">
                <svg class="progress-ring" width="120" height="120">
                    <circle cx="60" cy="60" r="54" stroke="#e6e6e6" stroke-width="8" fill="transparent"/>
                    <circle cx="60" cy="60" r="54" stroke="#4CAF50" stroke-width="8" fill="transparent"
                            stroke-dasharray="339.292" stroke-dashoffset="${339.292 - (339.292 * completionRate / 100)}"
                            transform="rotate(-90 60 60)"/>
                </svg>
                <div class="percentage">${completionRate.toFixed(0)}%</div>
            </div>
        </div>
        
        <div class="daily-stats">
            <div class="stat">
                <h4>Hoạt Động</h4>
                <p>${summary.activities ? summary.activities.filter(a => a.is_completed).length : 0}/${summary.activities ? summary.activities.length : 0}</p>
            </div>
            <div class="stat">
                <h4>Bữa Ăn</h4>
                <p>${summary.meals ? summary.meals.filter(m => m.is_completed).length : 0}/${summary.meals ? summary.meals.length : 0}</p>
            </div>
            <div class="stat">
                <h4>Calories Mục Tiêu</h4>
                <p>${summary.total_calories_target || 0} kcal</p>
            </div>
        </div>
    `;
}

async function loadActivityLogs() {
    try {
        const profileId = getCurrentProfileId();
        if (!profileId) {
            return;
        }
        const logs = await fetch(`/api/profiles/${profileId}/activity-logs?limit=10`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        }).then(r => r.json());

        renderActivityLogs(logs);
    } catch (error) {
        console.error('Error loading activity logs:', error);
    }
}

function renderActivityLogs(logs) {
    const container = document.getElementById('activity-logs-list');
    
    if (logs.length === 0) {
        container.innerHTML = '<p class="empty">Chưa có hoạt động nào</p>';
        return;
    }

    container.innerHTML = logs.map(log => `
        <div class="log-item">
            <div class="log-icon">
                <i class="fas ${getActivityIcon(log.activity_type)}"></i>
            </div>
            <div class="log-content">
                <strong>${log.activity_name}</strong>
                <div class="log-details">
                    ${log.duration_minutes} phút • ${log.intensity} • 
                    ${log.calories_burned ? Math.round(log.calories_burned) + ' kcal' : 'N/A'}
                </div>
                <div class="log-date">${formatDate(log.date)}</div>
            </div>
            <div class="log-actions">
                <button class="btn-delete" onclick="deleteActivityLog(${log.id})" title="Xóa hoạt động">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

async function loadMealLogs() {
    try {
        const profileId = getCurrentProfileId();
        if (!profileId) {
            return;
        }
        const logs = await fetch(`/api/profiles/${profileId}/meal-logs?limit=10`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        }).then(r => r.json());

        renderMealLogs(logs);
    } catch (error) {
        console.error('Error loading meal logs:', error);
    }
}

function renderMealLogs(logs) {
    const container = document.getElementById('meal-logs-list');
    
    if (logs.length === 0) {
        container.innerHTML = '<p class="empty">Chưa có bữa ăn nào</p>';
        return;
    }

    container.innerHTML = logs.map(log => `
        <div class="log-item">
            <div class="log-icon">
                <i class="fas ${getMealIcon(log.meal_type)}"></i>
            </div>
            <div class="log-content">
                <strong>${getMealTypeText(log.meal_type)}</strong>
                <div class="log-details">
                    ${log.food_items ? log.food_items.length : 0} món • 
                    ${log.total_calories ? Math.round(log.total_calories) + ' kcal' : 'N/A'}
                </div>
                <div class="log-date">${formatDate(log.date)}</div>
            </div>
            <div class="log-actions">
                <button class="btn-delete" onclick="deleteMealLog(${log.id})" title="Xóa bữa ăn">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

async function handleCreatePlan(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    // Determine primary goal for API (first selected), and add others into notes
    const primaryGoalLabel = selectedGoals[0] || 'Tăng cân';
    const primaryGoal = getGoalValueByLabel(primaryGoalLabel);
    const extraGoals = selectedGoals.slice(1);

    const planData = {
        title: formData.get('title'),
        goal_type: primaryGoal,
        target_value: parseFloat(formData.get('target_value')),
        target_unit: formData.get('target_unit'),
        duration_days: parseInt(formData.get('duration_days')),
        start_date: formData.get('start_date'),
        available_activities: selectedActivities,
        dietary_restrictions: selectedRestrictions,
        notes: extraGoals.length ? `Mục tiêu bổ sung: ${extraGoals.join(', ')}` : undefined
    };

    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalBtnHtml = submitBtn ? submitBtn.innerHTML : '';
    try {
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Đang tạo...';
        }
        showModalLoading('create-plan-modal');
        const profileId = getCurrentProfileId();
        const response = await fetch(`/api/profiles/${profileId}/health-plans`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getToken()}`
            },
            body: JSON.stringify(planData)
        });

        if (response.ok) {
            const result = await response.json();
            hideModal('create-plan-modal');
            showSuccess('Tạo kế hoạch thành công!');
            
            // Load data với error handling
            try {
                await loadPlans();
            } catch (error) {
                console.error('Error loading plans:', error);
            }
            
            try {
                await loadDailyProgress();
            } catch (error) {
                console.error('Error loading daily progress:', error);
            }
            
            try {
                await loadMonthlyTimeline();
            } catch (error) {
                console.error('Error loading monthly timeline:', error);
            }
            
            // Reset form
            e.target.reset();
            selectedActivities = [];
            selectedRestrictions = [];
            renderBadges('selected-activities', [], 'activity');
            renderBadges('selected-restrictions', [], 'restriction');
            document.getElementById('start-date').value = new Date().toISOString().split('T')[0];
            loadCurrentProfile();
        } else {
            const error = await response.json();
            showError(error.detail || 'Không thể tạo kế hoạch');
        }
    } catch (error) {
        console.error('Error creating plan:', error);
        showError('Lỗi kết nối. Vui lòng thử lại.');
    } finally {
        hideModalLoading('create-plan-modal');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnHtml || 'Tạo Kế Hoạch';
        }
    }
}

// Delete functions
async function deleteActivityLog(logId) {
    if (!confirm('Bạn có chắc muốn xóa hoạt động này?')) {
        return;
    }

    try {
        const profileId = getCurrentProfileId();
        const response = await fetch(`/api/profiles/${profileId}/activity-logs/${logId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${getToken()}`
            }
        });

        if (response.ok) {
            showSuccess('Xóa hoạt động thành công!');
            loadActivityLogs(); // Reload activity logs
            loadDailyProgress(); // Refresh daily progress
        } else {
            const error = await response.json();
            showError(error.detail || 'Không thể xóa hoạt động');
        }
    } catch (error) {
        console.error('Error deleting activity log:', error);
        showError('Lỗi kết nối. Vui lòng thử lại.');
    }
}

async function deleteMealLog(logId) {
    if (!confirm('Bạn có chắc muốn xóa bữa ăn này?')) {
        return;
    }

    try {
        const profileId = getCurrentProfileId();
        const response = await fetch(`/api/profiles/${profileId}/meal-logs/${logId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${getToken()}`
            }
        });

        if (response.ok) {
            showSuccess('Xóa bữa ăn thành công!');
            loadMealLogs(); // Reload meal logs
            loadDailyProgress(); // Refresh daily progress
        } else {
            const error = await response.json();
            showError(error.detail || 'Không thể xóa bữa ăn');
        }
    } catch (error) {
        console.error('Error deleting meal log:', error);
        showError('Lỗi kết nối. Vui lòng thử lại.');
    }
}

// Auto-match activities with plan
async function autoMatchActivities() {
    const btn = document.getElementById('auto-match-btn');
    const originalHtml = btn.innerHTML;
    
    try {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang liên kết...';
        
        const profileId = getCurrentProfileId();
        const response = await fetch(`/api/profiles/${profileId}/auto-match-activities?days_back=14`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getToken()}`
            }
        });

        if (response.ok) {
            const result = await response.json();
            showSuccess(`${result.message} (Kiểm tra: ${result.total_checked} hoạt động)`);
            
            // Refresh data to show updated progress
            loadDailyProgress();
            loadMonthlyTimeline();
            loadActivityLogs();
        } else {
            const error = await response.json();
            showError(error.detail || 'Không thể liên kết hoạt động');
        }
    } catch (error) {
        console.error('Error auto-matching activities:', error);
        showError('Lỗi kết nối. Vui lòng thử lại.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
    }
}

// Global functions for UI interactions
// Đã bỏ nút xem chi tiết để hiển thị trực tiếp trong thẻ

window.deleteActivityLog = deleteActivityLog;
window.deleteMealLog = deleteMealLog;
window.autoMatchActivities = autoMatchActivities;

window.adjustPlan = async function(planId) {
    try {
        const profileId = getCurrentProfileId();
        const response = await fetch(`/api/profiles/${profileId}/health-plans/${planId}/adjust`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getToken()}`
            },
            body: JSON.stringify({
                target_date: new Date().toISOString().split('T')[0],
                adjustment_days: 7,
                reason: 'Manual adjustment'
            })
        });

        if (response.ok) {
            showSuccess('Đã điều chỉnh kế hoạch dựa trên hoạt động gần đây');
            loadPlans();
            loadDailyProgress();
        } else {
            showError('Không thể điều chỉnh kế hoạch');
        }
    } catch (error) {
        showError('Lỗi kết nối. Vui lòng thử lại.');
    }
};

window.deletePlan = async function(planId) {
    try {
        if (!confirm('Bạn có chắc muốn xóa kế hoạch này?')) return;
        const profileId = getCurrentProfileId();
        if (!profileId) return;
        const response = await fetch(`/api/profiles/${profileId}/health-plans/${planId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (response.ok) {
            showSuccess('Đã xóa kế hoạch');
            loadPlans();
            loadDailyProgress();
            loadActivityLogs();
            loadMealLogs();
        } else {
            const err = await response.json().catch(() => ({}));
            showError(err.detail || 'Không thể xóa kế hoạch');
        }
    } catch (e) {
        showError('Lỗi kết nối. Vui lòng thử lại.');
    }
};

function renderPlanDetail(plan) {
    return `
        <div class="plan-detail">
            <div class="plan-detail-header">
                <div class="title-wrap">
                    <h3>${plan.title}</h3>
                    <span class="status-chip status-${plan.status}">${getStatusText(plan.status)}</span>
                </div>
                <div class="progress-row">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${(plan.current_progress / plan.target_value * 100).toFixed(1)}%"></div>
                    </div>
                    <span class="progress-text">${plan.current_progress}/${plan.target_value} ${plan.target_unit}</span>
                </div>
                <div class="meta-row">
                    <div class="meta"><i class="fas fa-bullseye"></i>${getGoalTypeText(plan.goal_type)}</div>
                    <div class="meta"><i class="fas fa-clock"></i>${plan.duration_days} ngày</div>
                    <div class="meta"><i class="fas fa-calendar-day"></i>${formatDate(plan.start_date)} - ${formatDate(plan.end_date)}</div>
                </div>
            </div>

            <div class="detail-grid">
                <div class="detail-card">
                    <h4><i class="fas fa-running"></i> Hoạt Động Có Thể Thực Hiện</h4>
                    <div class="tag-list">
                        ${plan.available_activities.map(activity => `<span class=\"tag\">${activity}</span>`).join('')}
                    </div>
                </div>
                ${plan.dietary_restrictions.length > 0 ? `
                <div class="detail-card">
                    <h4><i class="fas fa-utensils"></i> Hạn Chế Ăn Uống</h4>
                    <div class="tag-list">
                        ${plan.dietary_restrictions.map(restriction => `<span class=\"tag restriction\">${restriction}</span>`).join('')}
                    </div>
                </div>` : ''}
                ${plan.ai_analysis ? `
                <div class="detail-card span-2">
                    <h4><i class="fas fa-robot"></i> Phân Tích AI</h4>
                    <div class="analysis-content">
                        <div class="ai-grid">
                            <div><strong>Khả năng thành công</strong><div class="ai-score">${plan.ai_analysis.feasibility_score}/10</div></div>
                            ${plan.ai_analysis.success_tips ? `
                            <div>
                                <strong>Mẹo thành công</strong>
                                <ul class="tips-list">${plan.ai_analysis.success_tips.map(tip => `<li>${tip}</li>`).join('')}</ul>
                            </div>` : ''}
                        </div>
                    </div>
                </div>` : ''}
            </div>
        </div>
    `;
}

function renderDailyRoadmapContainer() {
    return `
        <div class="plan-daily-roadmap">
            <h4>Lộ trình theo ngày</h4>
            <div id="daily-roadmap" class="daily-roadmap">
                <div class="loading">Đang tải lộ trình...</div>
            </div>
        </div>
    `;
}

async function loadDailyRoadmap(planId) {
    try {
        const days = 30;
        const today = new Date();
        const items = [];
        for (let i = 0; i < days; i++) {
            const d = new Date(today);
            d.setDate(today.getDate() - i);
            const dateStr = d.toISOString().split('T')[0];
            // Lấy summary từng ngày
            const summary = await fetch(`/api/health-plans/${planId}/daily/${dateStr}`, {
                headers: { 'Authorization': `Bearer ${getToken()}` }
            }).then(r => r.json());
            items.push({ date: dateStr, summary });
        }
        renderDailyRoadmap(items.reverse());
    } catch (e) {
        const container = document.getElementById('daily-roadmap');
        if (container) container.innerHTML = '<div class="error">Không thể tải lộ trình ngày</div>';
    }
}

function renderDailyRoadmap(items) {
    const container = document.getElementById('daily-roadmap');
    if (!container) return;
    container.innerHTML = items.map(({ date, summary }) => {
        const completion = (summary?.completion_rate ?? 0).toFixed(0);
        const activitiesDone = summary?.activities ? summary.activities.filter(a => a.is_completed).length : 0;
        const activitiesTotal = summary?.activities ? summary.activities.length : 0;
        const mealsDone = summary?.meals ? summary.meals.filter(m => m.is_completed).length : 0;
        const mealsTotal = summary?.meals ? summary.meals.length : 0;
        return `
            <div class="daily-item">
                <div class="daily-date">${formatDate(date)}</div>
                <div class="daily-metrics">
                    <span class="metric"><i class="fas fa-check-circle"></i> ${completion}%</span>
                    <span class="metric"><i class="fas fa-running"></i> ${activitiesDone}/${activitiesTotal}</span>
                    <span class="metric"><i class="fas fa-utensils"></i> ${mealsDone}/${mealsTotal}</span>
                </div>
            </div>
        `;
    }).join('');
}

// (đã bỏ lộ trình trong card)

async function loadWeeklyTimeline() {
    try {
        const profileId = getCurrentProfileId();
        if (!profileId) return;

        // Lấy kế hoạch đang active đầu tiên
        const plans = await fetch(`/api/profiles/${profileId}/health-plans?status=active`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        }).then(r => r.json());
        if (!plans || plans.length === 0) {
            document.getElementById('weekly-timeline').innerHTML = '<div class="empty">Chưa có kế hoạch hoạt động</div>';
            return;
        }
        const plan = plans[0];

        // Lấy danh sách hoạt động theo 7 ngày gần nhất
        const today = new Date();
        const days = [...Array(7)].map((_, i) => {
            const d = new Date(today);
            d.setDate(today.getDate() - (6 - i));
            return d.toISOString().split('T')[0];
        });

        const dayItems = [];
        for (const dateStr of days) {
            const activities = await fetch(`/api/health-plans/${plan.id}/activities?date=${dateStr}`, {
                headers: { 'Authorization': `Bearer ${getToken()}` }
            }).then(r => r.json());
            dayItems.push({ date: dateStr, activities });
        }

        renderWeeklyTimeline(plan, dayItems);
    } catch (e) {
        document.getElementById('weekly-timeline').innerHTML = '<div class="error">Không thể tải lịch tuần</div>';
    }
}

function renderWeeklyTimeline(plan, dayItems) {
    const container = document.getElementById('weekly-timeline');
    if (!container) return;
    const availableActivities = (plan.available_activities || []);
    container.innerHTML = `
        <div class="week-grid">
            ${dayItems.map(({ date, activities }) => `
                <div class="week-cell">
                    <div class="week-date">${formatDate(date)}</div>
                    <div class="day-activities">
                        ${activities && activities.length ? activities.map(act => `
                            <div class="activity-row" data-activity-row>
                                <div class="activity-view">
                                    <span class="act-name">${act.activity_type}</span>
                                    <span class="act-duration">${act.duration_minutes || 30} phút</span>
                                    <button class="btn-icon edit-activity" title="Sửa" data-activity-id="${act.id}" data-plan-id="${plan.id}"><i class="fas fa-edit"></i></button>
                                </div>
                                <div class="activity-edit hidden">
                                    <select class="activity-select" data-activity-id="${act.id}" data-plan-id="${plan.id}">
                                        ${availableActivities.map(a => `<option value="${a}" ${a===act.activity_type? 'selected':''}>${a}</option>`).join('')}
                                    </select>
                                    <input type="number" class="duration-input" min="5" step="5" value="${act.duration_minutes || 30}" />
                                    <span class="minutes-label">phút</span>
                                    <button class="btn-icon save-activity" title="Lưu" data-activity-id="${act.id}" data-plan-id="${plan.id}"><i class="fas fa-save"></i></button>
                                    <button class="btn-icon cancel-activity" title="Hủy"><i class="fas fa-times"></i></button>
                                </div>
                            </div>
                        `).join('') : '<div class="empty small">Không có hoạt động</div>'}
                    </div>
                </div>
            `).join('')}
        </div>
    `;

    // Bind edit/save/cancel
    container.querySelectorAll('.edit-activity').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const row = e.currentTarget.closest('[data-activity-row]');
            row.querySelector('.activity-view').classList.add('hidden');
            row.querySelector('.activity-edit').classList.remove('hidden');
        });
    });
    container.querySelectorAll('.cancel-activity').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const row = e.currentTarget.closest('[data-activity-row]');
            row.querySelector('.activity-edit').classList.add('hidden');
            row.querySelector('.activity-view').classList.remove('hidden');
        });
    });
    container.querySelectorAll('.save-activity').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const row = e.currentTarget.closest('[data-activity-row]');
            const activityId = e.currentTarget.getAttribute('data-activity-id');
            const planId = e.currentTarget.getAttribute('data-plan-id');
            const select = row.querySelector('.activity-select');
            const duration = row.querySelector('.duration-input');
            await saveActivityUpdate(planId, activityId, select.value, parseInt(duration.value, 10));
            row.querySelector('.act-name').textContent = select.value;
            row.querySelector('.act-duration').textContent = `${parseInt(duration.value, 10)} phút`;
            row.querySelector('.activity-edit').classList.add('hidden');
            row.querySelector('.activity-view').classList.remove('hidden');
        });
    });
}

// === Monthly timeline (weeks as rows) ===
async function loadMonthlyTimeline() {
    try {
        const profileId = getCurrentProfileId();
        if (!profileId) return;

        const plans = await fetch(`/api/profiles/${profileId}/health-plans?status=active`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        }).then(r => r.json());
        if (!plans || plans.length === 0) {
            document.getElementById('weekly-timeline').innerHTML = '<div class="empty">Chưa có kế hoạch hoạt động</div>';
            return;
        }
        const plan = plans[0];

        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);

        // Bắt đầu từ thứ Hai của tuần đầu (hoặc Chủ nhật tùy locale, ở đây dùng Monday start)
        const start = new Date(firstDay);
        const dayOfWeek = (start.getDay() + 6) % 7; // Monday=0
        start.setDate(start.getDate() - dayOfWeek);

        // Kết thúc ở Chủ nhật của tuần cuối
        const end = new Date(lastDay);
        const endDayOfWeek = (end.getDay() + 6) % 7; // Monday=0
        end.setDate(end.getDate() + (6 - endDayOfWeek));

        // Tạo ma trận tuần x ngày (rows x 7)
        const weeks = [];
        let cursor = new Date(start);
        while (cursor <= end) {
            const week = [];
            for (let i = 0; i < 7; i++) {
                week.push(cursor.toISOString().split('T')[0]);
                cursor.setDate(cursor.getDate() + 1);
            }
            weeks.push(week);
        }

        // Tải activities và summary theo từng ngày (sequential để đơn giản; có thể tối ưu sau)
        const weekItems = [];
        for (const week of weeks) {
            const items = [];
            for (const dateStr of week) {
                const acts = await fetch(`/api/health-plans/${plan.id}/activities?date=${dateStr}`, {
                    headers: { 'Authorization': `Bearer ${getToken()}` }
                }).then(r => r.json());
                let summary = null;
                try {
                    summary = await fetch(`/api/health-plans/${plan.id}/daily/${dateStr}`, {
                        headers: { 'Authorization': `Bearer ${getToken()}` }
                    }).then(r => r.json());
                } catch (e) { summary = null; }
                const inPlan = (new Date(dateStr) >= new Date(plan.start_date)) && (new Date(dateStr) <= new Date(plan.end_date));
                items.push({ date: dateStr, activities: acts, summary, inPlan });
            }
            weekItems.push(items);
        }

        renderMonthlyTimeline(plan, weekItems, today);
    } catch (e) {
        document.getElementById('weekly-timeline').innerHTML = '<div class="error">Không thể tải lịch tháng</div>';
    }
}

function renderMonthlyTimeline(plan, weekItems, today) {
    const container = document.getElementById('weekly-timeline');
    if (!container) return;
    const availableActivities = (plan.available_activities || []);
    const currentMonth = today.getMonth();
    const header = `
        <div class="month-header">
            <div class="month-title">${today.toLocaleString('vi-VN', { month: 'long', year: 'numeric' })}</div>
            <div class="weekdays">
                <div>T2</div><div>T3</div><div>T4</div><div>T5</div><div>T6</div><div>T7</div><div>CN</div>
            </div>
        </div>`;

    const grid = `
        <div class="month-grid">
            ${weekItems.map(week => `
                <div class="week-row">
                    ${week.map(({ date, activities, summary, inPlan }) => {
                        const d = new Date(date);
                        const isCurrentMonth = d.getMonth() === currentMonth;
                        const completion = summary && typeof summary.completion_rate === 'number' ? Math.max(0, Math.min(100, summary.completion_rate)) : 0;
                        return `
                        <div class="day-cell ${isCurrentMonth ? '' : 'muted'} ${inPlan ? 'in-plan' : 'out-plan'}" data-date="${date}">
                            <div class="day-number">${d.getDate()}</div>
                            <span class="completion-badge ${completion>=100?'done':completion>=66?'high':completion>=33?'mid':'low'}">${completion.toFixed(0)}%</span>
                            <div class="day-activities">
                                ${activities && activities.length ? activities.map(act => `
                                    <div class="activity-row" data-activity-row data-date="${date}">
                                        <div class="activity-view">
                                            <span class="act-name">${act.activity_type}</span>
                                            <span class="act-duration">${act.duration_minutes || 30}p</span>
                                            <button class="btn-icon edit-activity" title="Sửa" data-activity-id="${act.id}" data-plan-id="${plan.id}"><i class="fas fa-edit"></i></button>
                                        </div>
                                        <div class="activity-edit hidden">
                                            <select class="activity-select" data-activity-id="${act.id}" data-plan-id="${plan.id}">
                                                ${availableActivities.map(a => `<option value="${a}" ${a===act.activity_type? 'selected':''}>${a}</option>`).join('')}
                                            </select>
                                            <input type="number" class="duration-input" min="5" step="5" value="${act.duration_minutes || 30}" />
                                            <span class="minutes-label">phút</span>
                                            <button class="btn-icon save-activity" title="Lưu" data-activity-id="${act.id}" data-plan-id="${plan.id}"><i class="fas fa-save"></i></button>
                                            <button class="btn-icon cancel-activity" title="Hủy"><i class="fas fa-times"></i></button>
                                        </div>
                                    </div>
                                `).join('') : (inPlan ? '<div class="empty small rest">Nghỉ / Tự do</div>' : '<div class="empty small">-</div>')}
                            </div>
                        </div>`;
                    }).join('')}
                </div>
            `).join('')}
        </div>`;

    container.innerHTML = header + grid;

    // Bind edit/save/cancel giống weekly
    container.querySelectorAll('.edit-activity').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const row = e.currentTarget.closest('[data-activity-row]');
            row.querySelector('.activity-view').classList.add('hidden');
            row.querySelector('.activity-edit').classList.remove('hidden');
        });
    });
    container.querySelectorAll('.cancel-activity').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const row = e.currentTarget.closest('[data-activity-row]');
            row.querySelector('.activity-edit').classList.add('hidden');
            row.querySelector('.activity-view').classList.remove('hidden');
        });
    });
    container.querySelectorAll('.save-activity').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const row = e.currentTarget.closest('[data-activity-row]');
            const activityId = e.currentTarget.getAttribute('data-activity-id');
            const planId = e.currentTarget.getAttribute('data-plan-id');
            const select = row.querySelector('.activity-select');
            const duration = row.querySelector('.duration-input');
            await saveActivityUpdate(planId, activityId, select.value, parseInt(duration.value, 10));
            row.querySelector('.act-name').textContent = select.value;
            row.querySelector('.act-duration').textContent = `${parseInt(duration.value, 10)}p`;
            row.querySelector('.activity-edit').classList.add('hidden');
            row.querySelector('.activity-view').classList.remove('hidden');

            // refresh completion badge for the day
            const dateStr = row.getAttribute('data-date');
            refreshDayCompletion(planId, dateStr, row.closest('.day-cell'));
        });
    });
}

async function refreshDayCompletion(planId, dateStr, dayCellEl) {
    try {
        const summary = await fetch(`/api/health-plans/${planId}/daily/${dateStr}`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        }).then(r => r.json());
        const completion = summary && typeof summary.completion_rate === 'number' ? Math.max(0, Math.min(100, summary.completion_rate)) : 0;
        const badge = dayCellEl.querySelector('.completion-badge');
        if (badge) {
            badge.textContent = `${completion.toFixed(0)}%`;
            badge.classList.remove('low', 'mid', 'high', 'done');
            badge.classList.add(completion>=100?'done':completion>=66?'high':completion>=33?'mid':'low');
        }
    } catch (e) {}
}

async function saveActivityUpdate(planId, activityId, activityType, duration) {
    try {
        const res = await fetch(`/api/health-plans/${planId}/activities/${activityId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
            body: JSON.stringify({ activity_type: activityType, duration_minutes: duration })
        });
        if (res.ok) {
            showSuccess('Đã cập nhật hoạt động');
        } else {
            const err = await res.json().catch(() => ({}));
            showError(err.detail || 'Không thể cập nhật');
        }
    } catch (e) {
        showError('Lỗi kết nối');
    }
}
// Utility functions
function getStatusText(status) {
    const statusMap = {
        'active': 'Đang hoạt động',
        'paused': 'Tạm dừng',
        'completed': 'Hoàn thành',
        'cancelled': 'Đã hủy'
    };
    return statusMap[status] || status;
}

function getGoalTypeText(goalType) {
    const goalMap = {
        'weight_gain': 'Tăng cân',
        'weight_loss': 'Giảm cân',
        'muscle_gain': 'Tăng cơ bắp',
        'endurance': 'Tăng sức bền',
        'recovery': 'Phục hồi',
        'maintenance': 'Duy trì'
    };
    return goalMap[goalType] || goalType;
}

function getMealTypeText(mealType) {
    const mealMap = {
        'breakfast': 'Bữa sáng',
        'lunch': 'Bữa trưa',
        'dinner': 'Bữa tối',
        'snack': 'Ăn vặt'
    };
    return mealMap[mealType] || mealType;
}

function getActivityIcon(activityType) {
    const iconMap = {
        'swimming': 'fa-swimmer',
        'running': 'fa-running',
        'gym': 'fa-dumbbell',
        'football': 'fa-futbol',
        'badminton': 'fa-table-tennis',
        'yoga': 'fa-spa',
        'walking': 'fa-walking',
        'general': 'fa-heartbeat'
    };
    return iconMap[activityType] || 'fa-heartbeat';
}

function getMealIcon(mealType) {
    const iconMap = {
        'breakfast': 'fa-coffee',
        'lunch': 'fa-hamburger',
        'dinner': 'fa-utensils',
        'snack': 'fa-cookie-bite'
    };
    return iconMap[mealType] || 'fa-utensils';
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('vi-VN');
}

// Get current profile ID from localStorage or session
function getCurrentProfileId() {
    // Đồng bộ với app/router: dùng key 'current_profile_id'
    return localStorage.getItem('current_profile_id');
}

function getToken() {
    // Đồng bộ với app/router: dùng key 'auth_token'
    return localStorage.getItem('auth_token');
}

function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    // Di chuyển modal về body để đảm bảo overlay toàn màn hình
    if (modal.parentNode !== document.body) {
        document.body.appendChild(modal);
    }
    modal.style.position = 'fixed';
    modal.style.display = 'flex';
    document.body.classList.add('modal-open');
}

function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    modal.style.display = 'none';
    // Nếu không còn modal nào hiển thị thì mở lại scroll cho body
    const anyOpen = Array.from(document.querySelectorAll('.modal')).some(m => m.style.display !== 'none');
    if (!anyOpen) document.body.classList.remove('modal-open');
}

function showModalLoading(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    let overlay = modal.querySelector('.modal-loading');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'modal-loading';
        overlay.innerHTML = '<div class="spinner"><i class="fas fa-circle-notch fa-spin"></i><span>Đang xử lý...</span></div>';
        modal.appendChild(overlay);
    }
    overlay.style.display = 'flex';
}

function hideModalLoading(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    const overlay = modal.querySelector('.modal-loading');
    if (overlay) overlay.style.display = 'none';
}

function showSuccess(message) {
    // Implementation depends on your notification system
    alert(message);
}

function showError(message) {
    // Implementation depends on your notification system
    alert(message);
}

// === NEW FUNCTIONS FOR ENHANCED FORM ===

async function loadCurrentProfile() {
    try {
        const profileId = getCurrentProfileId();
        if (!profileId) return;

        const response = await fetch(`/api/profiles/${profileId}`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });

        if (response.ok) {
            const profile = await response.json();
            
            // Fill current status fields
            const weightInput = document.getElementById('current-weight');
            const heightInput = document.getElementById('current-height');
            const ageInput = document.getElementById('current-age');
            
            if (weightInput && profile.weight != null) {
                weightInput.value = profile.weight;
            }
            if (heightInput && profile.height != null) {
                heightInput.value = profile.height;
            }
            if (ageInput && profile.age != null) {
                ageInput.value = profile.age;
            }
        }
    } catch (error) {
        console.error('Error loading profile:', error);
    }
}

async function updateProfileField(e) {
    const field = e.target.id.replace('current-', '');
    const value = parseFloat(e.target.value);
    
    if (!value || value <= 0) return;
    
    try {
        const profileId = getCurrentProfileId();
        if (!profileId) {
            return;
        }
        const response = await fetch(`/api/profiles/${profileId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getToken()}`
            },
            body: JSON.stringify({ [field]: value })
        });
        
        if (response.ok) {
            showSuccess(`Đã cập nhật ${field === 'weight' ? 'cân nặng' : field === 'height' ? 'chiều cao' : 'tuổi'}`);
        }
    } catch (error) {
        console.error('Error updating profile:', error);
    }
}

function setupBadgeInputs() {
    // Setup activities
    document.getElementById('add-activity-btn').addEventListener('click', () => {
        showAutocomplete('activity');
    });
    setupAutocomplete('activity', AVAILABLE_ACTIVITIES, selectedActivities, 'selected-activities');
    
    // Setup goals
    document.getElementById('add-goal-btn').addEventListener('click', () => showAutocomplete('goal'));
    setupAutocomplete('goal', AVAILABLE_GOALS.map(g => g.label), selectedGoals, 'selected-goals');
}

function showAutocomplete(type) {
    const container = document.getElementById(`${type}-autocomplete`);
    const input = document.getElementById(`${type}-input`);
    
    container.style.display = 'block';
    input.focus();
    input.value = '';
    updateSuggestions(type, '');
}

function setupAutocomplete(type, availableItems, selectedArray, containerId) {
    const input = document.getElementById(`${type}-input`);
    const container = document.getElementById(`${type}-autocomplete`);
    
    input.addEventListener('input', (e) => {
        updateSuggestions(type, e.target.value);
    });
    
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addBadge(type, input.value.trim());
        } else if (e.key === 'Escape') {
            container.style.display = 'none';
        }
    });
    
    // Click outside to close
    document.addEventListener('click', (e) => {
        if (!container.contains(e.target) && e.target.id !== `add-${type}-btn`) {
            container.style.display = 'none';
        }
    });
}

function updateSuggestions(type, query) {
    const suggestionsContainer = document.getElementById(`${type}-suggestions`);
    const availableItems =
        type === 'activity' ? AVAILABLE_ACTIVITIES :
        type === 'goal' ? AVAILABLE_GOALS.map(g => g.label) :
        [];
    const selectedArray =
        type === 'activity' ? selectedActivities :
        type === 'goal' ? selectedGoals : [];
    
    const filtered = availableItems.filter(item => 
        item.toLowerCase().includes(query.toLowerCase()) && 
        !selectedArray.includes(item)
    );
    
    suggestionsContainer.innerHTML = filtered.map(item => 
        `<div class="suggestion-item" onclick="addBadge('${type}', '${item}')">${item}</div>`
    ).join('');
    
    // Show "Add new" option if query doesn't exist
    if (query && !availableItems.includes(query) && !selectedArray.includes(query)) {
        suggestionsContainer.innerHTML += 
            `<div class="suggestion-item new-item" onclick="addBadge('${type}', '${query}')">
                <i class="fas fa-plus"></i> Thêm "${query}"
            </div>`;
    }
}

function addBadge(type, value) {
    if (!value) return;
    
    const selectedArray =
        type === 'activity' ? selectedActivities :
        type === 'goal' ? selectedGoals : [];
    const containerId =
        type === 'activity' ? 'selected-activities' :
        type === 'goal' ? 'selected-goals' : '';
    
    if (!selectedArray.includes(value)) {
        selectedArray.push(value);
        renderBadges(containerId, selectedArray, type);
    }
    
    // Hide autocomplete
    document.getElementById(`${type}-autocomplete`).style.display = 'none';
    document.getElementById(`${type}-input`).value = '';
    
    // Update units if goal changed
    if (type === 'goal') {
        updateUnitsBasedOnGoal();
    }
}

function renderBadges(containerId, items, type) {
    const container = document.getElementById(containerId);
    container.innerHTML = items.map(item => 
        `<span class="badge">
            ${item}
            <button type="button" class="badge-remove" onclick="removeBadge('${type}', '${item}')">
                <i class="fas fa-times"></i>
            </button>
        </span>`
    ).join('');
}

function removeBadge(type, value) {
    const selectedArray =
        type === 'activity' ? selectedActivities :
        type === 'goal' ? selectedGoals : [];
    const containerId =
        type === 'activity' ? 'selected-activities' :
        type === 'goal' ? 'selected-goals' : '';
    
    const index = selectedArray.indexOf(value);
    if (index > -1) {
        selectedArray.splice(index, 1);
        renderBadges(containerId, selectedArray, type);
        if (type === 'goal') {
            updateUnitsBasedOnGoal();
        }
    }
}

function updateUnitsBasedOnGoal() {
    const primaryGoalLabel = selectedGoals[0] || '';
    const goalType = getGoalValueByLabel(primaryGoalLabel);
    const unitSelect = document.getElementById('target-unit');
    const targetInput = document.getElementById('target-value');
    
    // Clear previous options
    unitSelect.innerHTML = '';
    
    let units = [];
    let placeholder = '';
    
    switch(goalType) {
        case 'weight_gain':
        case 'weight_loss':
        case 'weight_maintain':
            units = [['kg', 'kg (cân nặng)'], ['lbs', 'lbs (pound)']];
            placeholder = '55';
            break;
        case 'height_growth':
            units = [['cm', 'cm (chiều cao)'], ['inches', 'inches']];
            placeholder = '170';
            break;
        case 'muscle_gain':
        case 'fat_loss':
        case 'body_recomp':
            units = [['%', '% (tỷ lệ cơ/mỡ)'], ['kg', 'kg (khối lượng cơ)'], ['cm', 'cm (vòng cơ)']];
            placeholder = '15';
            break;
        case 'endurance':
        case 'strength':
            units = [['minutes', 'phút (thời gian)'], ['km', 'km (khoảng cách)'], ['reps', 'lần (số lần tập)'], ['kg', 'kg (trọng lượng)']];
            placeholder = '30';
            break;
        case 'diabetes_control':
            units = [['mg/dl', 'mg/dL (đường huyết)'], ['%', '% (HbA1c)']];
            placeholder = '100';
            break;
        case 'blood_pressure':
            units = [['mmHg', 'mmHg (huyết áp)']];
            placeholder = '120';
            break;
        default:
            units = [['kg', 'kg'], ['cm', 'cm'], ['%', '%'], ['minutes', 'phút']];
            placeholder = '1';
    }
    
    units.forEach(([value, text]) => {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = text;
        unitSelect.appendChild(option);
    });
    
    targetInput.placeholder = placeholder;
}

// Global function for age suggestions
window.suggestPlanForAge = function(ageGroup) {
    showModal('create-plan-modal');
    const durationSelect = document.getElementById('duration-days');
    
    switch(ageGroup) {
        case 'teen':
            selectedGoals = ['Phát triển chiều cao', 'Phát triển toàn diện'];
            durationSelect.value = '180';
            selectedActivities = ['Đi bộ', 'Bóng rổ', 'Bơi lội', 'Yoga'];
            selectedRestrictions = ['Thực phẩm hữu cơ', 'Ít đường'];
            break;
        case 'adult':
            selectedGoals = ['Tăng cơ bắp', 'Giảm mỡ'];
            durationSelect.value = '90';
            selectedActivities = ['Tập gym', 'Chạy bộ', 'HIIT'];
            selectedRestrictions = ['Ít muối', 'Không đồ ăn nhanh'];
            break;
        case 'middle':
            selectedGoals = ['Tim mạch', 'Huyết áp'];
            durationSelect.value = '120';
            selectedActivities = ['Đi bộ', 'Yoga', 'Đạp xe'];
            selectedRestrictions = ['DASH', 'Ít muối', 'Ít đường'];
            break;
        case 'senior':
            selectedGoals = ['Xương khớp', 'Thăng bằng'];
            durationSelect.value = '365';
            selectedActivities = ['Đi bộ', 'Thái cực', 'Stretching'];
            selectedRestrictions = ['Ít muối', 'Nhiều canxi'];
            break;
    }
    
    updateUnitsBasedOnGoal();
    renderBadges('selected-goals', selectedGoals, 'goal');
    renderBadges('selected-activities', selectedActivities, 'activity');
    renderBadges('selected-restrictions', selectedRestrictions, 'restriction');
};

// Update form submission to use new badge data
window.removeBadge = removeBadge;
window.addBadge = addBadge;
