let currentPage = 'dashboard';

document.addEventListener('DOMContentLoaded', async () => {
    await checkAuth();
    initNavigation();
    loadPage('dashboard');
});

async function checkAuth() {
    try {
        const response = await fetch('/api/auth/status');
        const data = await response.json();
        
        if (data.authenticated && data.user) {
            const userAvatar = document.getElementById('userAvatar');
            const userName = document.getElementById('userName');
            
            if (userAvatar) userAvatar.textContent = data.user.username.charAt(0).toUpperCase();
            if (userName) userName.textContent = data.user.username;
        }
    } catch (error) {
        console.log('Auth check failed:', error);
    }
}

function initNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const page = item.dataset.page;
            if (page) {
                loadPage(page);
            }
        });
    });
}

async function loadPage(pageName, param = null) {
    currentPage = pageName;
    
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.page === pageName) {
            item.classList.add('active');
        }
    });
    
    const mainContent = document.getElementById('mainContent');
    mainContent.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    
    try {
        let html;
        if (pageName === 'cogConfig' && param) {
            html = await pages.cogConfig(param);
            mainContent.innerHTML = html;
            initCogConfigForm();
        } else if (pages[pageName]) {
            html = await pages[pageName]();
            mainContent.innerHTML = html;
            initPageCharts(pageName);
        } else {
            mainContent.innerHTML = `
                <div class="card">
                    <div class="card-body text-center">
                        <h2>Trang không tồn tại</h2>
                        <p class="text-muted">Trang "${pageName}" chưa được triển khai.</p>
                    </div>
                </div>
            `;
        }
    } catch (error) {
        mainContent.innerHTML = `
            <div class="card">
                <div class="card-body text-center text-danger">
                    <h2>Lỗi tải trang</h2>
                    <p>${error.message}</p>
                    <button class="btn btn-primary mt-4" onclick="loadPage('${pageName}')">
                        <i class="fas fa-redo"></i> Thử lại
                    </button>
                </div>
            </div>
        `;
    }
}

function initPageCharts(pageName) {
    setTimeout(() => {
        if (pageName === 'dashboard') {
            initDistributionChart();
        } else if (pageName === 'economy') {
            initEconomyCharts();
        } else if (pageName === 'analytics') {
            initCommandsChart();
        } else if (pageName === 'modules') {
            initModuleToggles();
        } else if (pageName === 'roles') {
            initRolesDragDrop();
        } else if (pageName === 'system') {
            initSystemWebSocket();
        }
    }, 100);
}

let systemWs = null;

function initSystemWebSocket() {
    if (systemWs) {
        systemWs.close();
    }
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    systemWs = new WebSocket(`${protocol}//${window.location.host}/api/ws/system`);
    
    const statusEl = document.getElementById('wsStatus');
    
    systemWs.onopen = () => {
        if (statusEl) {
            statusEl.textContent = 'Live';
            statusEl.className = 'badge badge-success';
        }
    };
    
    systemWs.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'system_stats') {
            updateSystemStats(msg.data);
        }
    };
    
    systemWs.onclose = () => {
        if (statusEl) {
            statusEl.textContent = 'Disconnected';
            statusEl.className = 'badge badge-danger';
        }
    };
    
    systemWs.onerror = () => {
        if (statusEl) {
            statusEl.textContent = 'Error';
            statusEl.className = 'badge badge-danger';
        }
    };
}

function updateSystemStats(data) {
    const update = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };
    
    const updateHtml = (id, html) => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = html;
    };
    
    update('cpuUsage', `${data.cpu?.usage_percent?.toFixed(1) || 0}%`);
    update('ramUsage', `${data.memory?.ram_percent?.toFixed(1) || 0}%`);
    update('ramDetail', `${(data.memory?.ram_used_gb || 0).toFixed(1)}GB / ${(data.memory?.ram_total_gb || 0).toFixed(1)}GB`);
    update('diskUsage', `${data.disk?.usage_percent?.toFixed(1) || 0}%`);
    update('diskDetail', `${(data.disk?.used_gb || 0).toFixed(1)}GB / ${(data.disk?.total_gb || 0).toFixed(1)}GB`);
    update('botStatus', data.bot?.online ? 'Online' : 'Offline');
    update('botUptime', `Uptime: ${data.bot?.uptime || 'N/A'}`);
    update('botPid', data.bot?.pid || 'N/A');
    update('botCpu', `${data.bot?.cpu_percent?.toFixed(1) || 0}%`);
    update('botMem', `${(data.bot?.memory_mb || 0).toFixed(1)} MB`);
    updateHtml('netUpload', `<i class="fas fa-arrow-up"></i> ${(data.network?.upload_speed_mbps || 0).toFixed(2)} Mbps`);
    updateHtml('netDownload', `<i class="fas fa-arrow-down"></i> ${(data.network?.download_speed_mbps || 0).toFixed(2)} Mbps`);
}

function initEconomyCharts() {
    const data = window._economyData;
    if (!data) return;
    
    const { detailed } = data;
    
    const dayCtx = document.getElementById('economyDayChart');
    if (dayCtx && detailed.by_day) {
        new Chart(dayCtx, {
            type: 'line',
            data: {
                labels: detailed.by_day.map(d => d.date.split('-').slice(1).join('/')),
                datasets: [
                    { label: 'Thu', data: detailed.by_day.map(d => d.earned), borderColor: 'rgba(34, 197, 94, 1)', backgroundColor: 'rgba(34, 197, 94, 0.2)', fill: true, tension: 0.4 },
                    { label: 'Chi', data: detailed.by_day.map(d => d.spent), borderColor: 'rgba(239, 68, 68, 1)', backgroundColor: 'rgba(239, 68, 68, 0.2)', fill: true, tension: 0.4 }
                ]
            },
            options: chartOptions()
        });
    }
    
    const catCtx = document.getElementById('economyCategoryChart');
    if (catCtx && detailed.by_category) {
        new Chart(catCtx, {
            type: 'doughnut',
            data: {
                labels: detailed.by_category.map(c => c.category || 'Unknown'),
                datasets: [{
                    data: detailed.by_category.map(c => c.earned),
                    backgroundColor: ['rgba(139, 92, 246, 0.8)', 'rgba(59, 130, 246, 0.8)', 'rgba(34, 197, 94, 0.8)', 'rgba(249, 115, 22, 0.8)', 'rgba(236, 72, 153, 0.8)', 'rgba(20, 184, 166, 0.8)'],
                    borderWidth: 0
                }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { color: '#a1a1aa' } } } }
        });
    }
    
    initWealthChart();
}

function initDistributionChart() {
    const ctx = document.getElementById('distributionChart');
    if (!ctx) return;
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Top 1%', 'Top 10%', 'Top 50%', 'Còn lại'],
            datasets: [{
                data: [35, 25, 25, 15],
                backgroundColor: [
                    'rgba(139, 92, 246, 0.8)',
                    'rgba(59, 130, 246, 0.8)',
                    'rgba(34, 197, 94, 0.8)',
                    'rgba(107, 114, 128, 0.8)'
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#a1a1aa',
                        padding: 20
                    }
                }
            }
        }
    });
}

function initWealthChart() {
    const ctx = document.getElementById('wealthChart');
    if (!ctx) return;
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['0-1K', '1K-10K', '10K-100K', '100K-1M', '1M+'],
            datasets: [{
                label: 'Số người dùng',
                data: [150, 320, 180, 45, 12],
                backgroundColor: 'rgba(139, 92, 246, 0.8)',
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#a1a1aa' }
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { color: '#a1a1aa' }
                }
            }
        }
    });
}

function initCommandsChart() {
    const data = window._analyticsData;
    if (!data) return;
    
    const { cmdStats, activityStats } = data;
    
    const dayCtx = document.getElementById('commandsByDayChart');
    if (dayCtx && cmdStats.by_day) {
        new Chart(dayCtx, {
            type: 'line',
            data: {
                labels: cmdStats.by_day.map(d => d.date.split('-').slice(1).join('/')),
                datasets: [{
                    label: 'Lệnh',
                    data: cmdStats.by_day.map(d => d.count),
                    borderColor: 'rgba(139, 92, 246, 1)',
                    backgroundColor: 'rgba(139, 92, 246, 0.2)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: chartOptions()
        });
    }
    
    const hourCtx = document.getElementById('commandsByHourChart');
    if (hourCtx && cmdStats.by_hour) {
        const hourData = Array(24).fill(0);
        cmdStats.by_hour.forEach(h => { hourData[h.hour] = h.count; });
        
        new Chart(hourCtx, {
            type: 'bar',
            data: {
                labels: Array.from({length: 24}, (_, i) => `${i}h`),
                datasets: [{
                    label: 'Lệnh',
                    data: hourData,
                    backgroundColor: 'rgba(59, 130, 246, 0.8)',
                    borderRadius: 4
                }]
            },
            options: chartOptions()
        });
    }
    
    const topCtx = document.getElementById('topCommandsChart');
    if (topCtx && cmdStats.by_command) {
        new Chart(topCtx, {
            type: 'bar',
            data: {
                labels: cmdStats.by_command.slice(0, 10).map(c => c.command_name),
                datasets: [{
                    label: 'Lượt dùng',
                    data: cmdStats.by_command.slice(0, 10).map(c => c.count),
                    backgroundColor: 'rgba(139, 92, 246, 0.8)',
                    borderRadius: 6
                }]
            },
            options: { ...chartOptions(), indexAxis: 'y' }
        });
    }
    
    const cogCtx = document.getElementById('commandsByCogChart');
    if (cogCtx && cmdStats.by_cog) {
        new Chart(cogCtx, {
            type: 'doughnut',
            data: {
                labels: cmdStats.by_cog.map(c => c.cog_name),
                datasets: [{
                    data: cmdStats.by_cog.map(c => c.count),
                    backgroundColor: [
                        'rgba(139, 92, 246, 0.8)', 'rgba(59, 130, 246, 0.8)',
                        'rgba(34, 197, 94, 0.8)', 'rgba(249, 115, 22, 0.8)',
                        'rgba(236, 72, 153, 0.8)', 'rgba(99, 102, 241, 0.8)',
                        'rgba(20, 184, 166, 0.8)', 'rgba(245, 158, 11, 0.8)'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'right', labels: { color: '#a1a1aa' } } }
            }
        });
    }
    
    const memberCtx = document.getElementById('memberActivityChart');
    if (memberCtx && activityStats.by_day) {
        new Chart(memberCtx, {
            type: 'bar',
            data: {
                labels: activityStats.by_day.map(d => d.date.split('-').slice(1).join('/')),
                datasets: [
                    { label: 'Vào', data: activityStats.by_day.map(d => d.joins), backgroundColor: 'rgba(34, 197, 94, 0.8)', borderRadius: 4 },
                    { label: 'Ra', data: activityStats.by_day.map(d => d.leaves), backgroundColor: 'rgba(239, 68, 68, 0.8)', borderRadius: 4 }
                ]
            },
            options: chartOptions()
        });
    }
}

function chartOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            x: { grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#a1a1aa' } },
            y: { grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#a1a1aa' } }
        }
    };
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'times-circle' : 'exclamation-circle'}"></i>
        <span>${message}</span>
    `;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function initModuleToggles() {
    document.querySelectorAll('.module-toggle').forEach(toggle => {
        toggle.addEventListener('change', async (e) => {
            const moduleId = e.target.dataset.module;
            const enabled = e.target.checked;
            const card = e.target.closest('.module-card');
            
            try {
                card.style.opacity = '0.6';
                const response = await fetch(`/api/modules/${moduleId}/toggle`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ enabled })
                });
                
                if (!response.ok) throw new Error('Toggle failed');
                
                showToast(`Module ${moduleId} đã ${enabled ? 'bật' : 'tắt'}`, 'success');
            } catch (error) {
                e.target.checked = !enabled;
                showToast(`Lỗi: ${error.message}`, 'error');
            } finally {
                card.style.opacity = '1';
            }
        });
    });
}

function initRolesDragDrop() {
    const roleItems = document.querySelectorAll('.role-item');
    const roleLists = document.querySelectorAll('.role-list');
    
    roleItems.forEach(item => {
        item.addEventListener('dragstart', (e) => {
            item.classList.add('dragging');
            e.dataTransfer.setData('text/plain', item.dataset.roleId);
        });
        
        item.addEventListener('dragend', () => {
            item.classList.remove('dragging');
            document.querySelectorAll('.role-list').forEach(l => l.classList.remove('drag-over'));
        });
    });
    
    roleLists.forEach(list => {
        list.addEventListener('dragover', (e) => {
            e.preventDefault();
            list.classList.add('drag-over');
        });
        
        list.addEventListener('dragleave', () => {
            list.classList.remove('drag-over');
        });
        
        list.addEventListener('drop', async (e) => {
            e.preventDefault();
            list.classList.remove('drag-over');
            
            const roleId = e.dataTransfer.getData('text/plain');
            const targetCategory = list.dataset.category;
            const draggingItem = document.querySelector(`.role-item[data-role-id="${roleId}"]`);
            
            if (draggingItem && targetCategory) {
                list.appendChild(draggingItem);
                showToast('Đã di chuyển role', 'success');
            }
        });
    });
}

function openModuleConfig(moduleId) {
    loadPage('cogConfig', moduleId);
}

function initCogConfigForm() {
    const form = document.getElementById('cogConfigForm');
    if (!form) return;
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const cogName = form.dataset.cog;
        const formData = new FormData(form);
        const settings = {};
        
        form.querySelectorAll('input').forEach(input => {
            if (input.type === 'checkbox') {
                settings[input.name] = input.checked;
            } else if (input.type === 'number') {
                settings[input.name] = parseFloat(input.value);
            } else {
                settings[input.name] = input.value;
            }
        });
        
        try {
            await api.updateCogConfig(cogName, settings);
            showToast('Đã lưu cấu hình', 'success');
        } catch (error) {
            showToast(`Lỗi: ${error.message}`, 'error');
        }
    });
}

function renderBotLogs(logs) {
    if (!logs || logs.length === 0) {
        return '<div class="text-center text-muted py-4">Không có logs</div>';
    }
    
    const levelColors = {
        'DEBUG': '#6b7280',
        'INFO': '#3b82f6', 
        'WARNING': '#f59e0b',
        'ERROR': '#ef4444',
        'CRITICAL': '#8b5cf6'
    };
    
    return logs.map(log => `
        <div class="log-entry" style="border-left: 3px solid ${levelColors[log.level] || '#6b7280'}; padding: 8px 12px; margin-bottom: 4px; background: var(--bg-tertiary); border-radius: 4px; font-family: monospace; font-size: 13px;">
            <div class="flex gap-4">
                <span class="text-muted" style="min-width: 140px;">${log.timestamp}</span>
                <span style="color: ${levelColors[log.level]}; min-width: 70px; font-weight: 600;">${log.level}</span>
                <span class="text-muted" style="min-width: 120px;">[${log.module}]</span>
                <span style="flex: 1; word-break: break-word;">${escapeHtml(log.message)}</span>
            </div>
        </div>
    `).join('');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

let filterDebounceTimer = null;
function debounceFilterBotLogs() {
    clearTimeout(filterDebounceTimer);
    filterDebounceTimer = setTimeout(filterBotLogs, 300);
}

async function filterBotLogs() {
    const file = document.getElementById('logFileSelect')?.value || 'main.log';
    const level = document.getElementById('logLevelFilter')?.value || '';
    const module = document.getElementById('logModuleFilter')?.value || '';
    const search = document.getElementById('logSearchInput')?.value || '';
    const fromDate = document.getElementById('logFromDate')?.value || '';
    const toDate = document.getElementById('logToDate')?.value || '';
    
    const container = document.getElementById('botLogsContainer');
    container.innerHTML = '<div class="text-center py-4"><i class="fas fa-spinner fa-spin"></i> Đang tải...</div>';
    
    try {
        const params = { file, limit: 200 };
        if (level) params.level = level;
        if (module) params.module = module;
        if (search) params.search = search;
        if (fromDate) params.from_date = fromDate;
        if (toDate) params.to_date = toDate;
        
        const data = await api.getBotLogs(params);
        container.innerHTML = renderBotLogs(data.logs || []);
        document.getElementById('logsPagination').textContent = `Hiển thị ${data.logs?.length || 0} / ${data.total || 0} logs`;
    } catch (error) {
        container.innerHTML = `<div class="text-center text-danger py-4">Lỗi: ${error.message}</div>`;
    }
}

async function refreshBotLogs() {
    await filterBotLogs();
    showToast('Đã làm mới logs', 'success');
}

async function viewUser(userId) {
    try {
        const user = await api.getUser(userId);
        showUserModal(user);
    } catch (error) {
        showToast('Không thể tải thông tin người dùng', 'error');
    }
}

function showUserModal(user) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal" style="background: var(--bg-card); border-radius: var(--radius-lg); padding: 24px; max-width: 500px; width: 90%;">
            <div class="flex flex-between mb-4">
                <h2>${user.username || 'Unknown'}</h2>
                <button class="btn btn-sm btn-secondary" onclick="this.closest('.modal-overlay').remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="grid-2 gap-4">
                <div>
                    <div class="text-muted">ID</div>
                    <code>${user.user_id}</code>
                </div>
                <div>
                    <div class="text-muted">Hạt</div>
                    <strong>${formatNumber(user.seeds)}</strong> 🌱
                </div>
                <div>
                    <div class="text-muted">Level</div>
                    <span class="badge purple">Lv.${user.level || 1}</span>
                </div>
                <div>
                    <div class="text-muted">Cá đã câu</div>
                    ${formatNumber(user.fish_caught || 0)} 🐟
                </div>
            </div>
        </div>
    `;
    modal.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;z-index:1000;';
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
    document.body.appendChild(modal);
}

function editUser(userId) {
    showToast('Tính năng đang phát triển', 'warning');
}

async function saveConfig() {
    try {
        const config = {
            game: {
                daily_reward: parseInt(document.getElementById('cfg_daily_reward').value),
                fish_cooldown: parseInt(document.getElementById('cfg_fish_cooldown').value),
                max_bet: parseInt(document.getElementById('cfg_max_bet').value),
                xp_multiplier: parseFloat(document.getElementById('cfg_xp_multi').value)
            }
        };
        await api.updateConfig(config);
        showToast('Đã lưu cấu hình thành công!', 'success');
    } catch (error) {
        showToast('Lỗi lưu cấu hình: ' + error.message, 'error');
    }
}

function exportUsers() {
    window.open('/api/stats/export', '_blank');
}

function logout() {
    fetch('/api/auth/logout', { method: 'POST' })
        .then(() => {
            window.location.href = '/login';
        })
        .catch(() => {
            window.location.href = '/login';
        });
}

setInterval(() => {
    if (currentPage === 'system') {
        loadPage('system');
    }
}, 30000);
