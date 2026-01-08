const pages = {
    async dashboard() {
        try {
            const stats = await api.getStats();
            
            return `
                <div class="page-header">
                    <h1 class="page-title">Dashboard</h1>
                    <p class="page-subtitle">Tổng quan hệ thống BHNBot</p>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon purple"><i class="fas fa-users"></i></div>
                        <div class="stat-value">${formatNumber(stats.economy?.total_users || 0)}</div>
                        <div class="stat-label">Tổng người dùng</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon green"><i class="fas fa-coins"></i></div>
                        <div class="stat-value">${formatNumber(stats.economy?.total_seeds || 0)}</div>
                        <div class="stat-label">Tổng Hạt lưu thông</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon blue"><i class="fas fa-fish"></i></div>
                        <div class="stat-value">${formatNumber(stats.modules?.fishing?.total_catches || 0)}</div>
                        <div class="stat-label">Lượt câu cá</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon orange"><i class="fas fa-dice"></i></div>
                        <div class="stat-value">${formatNumber(stats.modules?.baucua?.total_games || 0)}</div>
                        <div class="stat-label">Ván Bầu Cua</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon pink"><i class="fas fa-gamepad"></i></div>
                        <div class="stat-value">${formatNumber(stats.modules?.noitu?.total_games || 0)}</div>
                        <div class="stat-label">Ván Nối Từ</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon cyan"><i class="fas fa-box"></i></div>
                        <div class="stat-value">${formatNumber(stats.modules?.inventory?.total_items || 0)}</div>
                        <div class="stat-label">Vật phẩm tồn kho</div>
                    </div>
                </div>
                
                <div class="grid-2">
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title"><i class="fas fa-chart-pie"></i> Phân phối tài sản</h3>
                        </div>
                        <div class="card-body">
                            <div class="chart-container">
                                <canvas id="distributionChart"></canvas>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title"><i class="fas fa-server"></i> Tình trạng hệ thống</h3>
                        </div>
                        <div class="card-body">
                            <div class="form-group">
                                <div class="flex flex-between mb-2">
                                    <span>CPU</span>
                                    <span>${stats.system?.cpu?.usage_percent?.toFixed(1) || 0}%</span>
                                </div>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: ${stats.system?.cpu?.usage_percent || 0}%"></div>
                                </div>
                            </div>
                            <div class="form-group">
                                <div class="flex flex-between mb-2">
                                    <span>RAM</span>
                                    <span>${stats.system?.memory?.ram_percent?.toFixed(1) || 0}%</span>
                                </div>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: ${stats.system?.memory?.ram_percent || 0}%"></div>
                                </div>
                            </div>
                            <div class="form-group">
                                <div class="flex flex-between mb-2">
                                    <span>Disk</span>
                                    <span>${stats.system?.disk?.usage_percent?.toFixed(1) || 0}%</span>
                                </div>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: ${stats.system?.disk?.usage_percent || 0}%"></div>
                                </div>
                            </div>
                            <div class="mt-4">
                                <div class="flex flex-between text-muted">
                                    <span>Bot Status</span>
                                    <span class="badge ${stats.system?.bot?.online ? 'success' : 'danger'}">
                                        ${stats.system?.bot?.online ? 'Online' : 'Offline'}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title"><i class="fas fa-trophy"></i> Top 10 giàu nhất</h3>
                    </div>
                    <div class="card-body">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>Người dùng</th>
                                    <th>Hạt</th>
                                    <th>Tỷ lệ</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${(stats.economy?.top_10 || []).map((user, i) => `
                                    <tr>
                                        <td><span class="badge ${i < 3 ? 'warning' : 'info'}">${i + 1}</span></td>
                                        <td>${user.username || 'Unknown'}</td>
                                        <td><strong>${formatNumber(user.seeds)}</strong> 🌱</td>
                                        <td>${formatPercent(user.seeds / (stats.economy?.total_seeds || 1))}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        } catch (error) {
            return `<div class="card"><div class="card-body text-center text-danger">Lỗi tải dữ liệu: ${error.message}</div></div>`;
        }
    },

    async users() {
        try {
            const users = await api.getUsers({ limit: 50 });
            
            return `
                <div class="page-header">
                    <h1 class="page-title">Quản lý người dùng</h1>
                    <p class="page-subtitle">Tìm kiếm và quản lý người dùng bot</p>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <div class="flex gap-4">
                            <input type="text" class="form-input" placeholder="Tìm kiếm theo tên hoặc ID..." 
                                   id="userSearch" style="width: 300px;">
                            <select class="form-input" id="userSort" style="width: 150px;">
                                <option value="seeds_desc">Hạt (cao→thấp)</option>
                                <option value="seeds_asc">Hạt (thấp→cao)</option>
                                <option value="name_asc">Tên (A→Z)</option>
                            </select>
                        </div>
                        <button class="btn btn-primary" onclick="exportUsers()">
                            <i class="fas fa-download"></i> Xuất Excel
                        </button>
                    </div>
                    <div class="card-body">
                        <table class="data-table" id="usersTable">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Tên</th>
                                    <th>Hạt</th>
                                    <th>Level</th>
                                    <th>Câu cá</th>
                                    <th>Hành động</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${(users.users || []).map(user => `
                                    <tr>
                                        <td><code>${user.user_id}</code></td>
                                        <td>${user.username || 'Unknown'}</td>
                                        <td><strong>${formatNumber(user.seeds)}</strong> 🌱</td>
                                        <td><span class="badge purple">Lv.${user.level || 1}</span></td>
                                        <td>${formatNumber(user.fish_caught || 0)} 🐟</td>
                                        <td>
                                            <button class="btn btn-sm btn-secondary" onclick="viewUser('${user.user_id}')">
                                                <i class="fas fa-eye"></i>
                                            </button>
                                            <button class="btn btn-sm btn-primary" onclick="editUser('${user.user_id}')">
                                                <i class="fas fa-edit"></i>
                                            </button>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        } catch (error) {
            return `<div class="card"><div class="card-body text-center text-danger">Lỗi: ${error.message}</div></div>`;
        }
    },

    async modules() {
        try {
            const data = await api.getModules();
            const modules = data.modules || [];
            
            const iconMap = {
                'fishing': { icon: 'fa-fish', color: 'blue' },
                'economy': { icon: 'fa-coins', color: 'green' },
                'gambling': { icon: 'fa-dice', color: 'orange' },
                'werewolf': { icon: 'fa-wolf-pack-battalion', color: 'purple' },
                'music': { icon: 'fa-music', color: 'pink' },
                'tree': { icon: 'fa-tree', color: 'green' },
                'aquarium': { icon: 'fa-water', color: 'cyan' },
                'relationship': { icon: 'fa-heart', color: 'pink' },
                'achievements': { icon: 'fa-trophy', color: 'orange' },
                'giveaway': { icon: 'fa-gift', color: 'purple' },
                'noitu': { icon: 'fa-comments', color: 'blue' },
                'vip': { icon: 'fa-crown', color: 'orange' },
            };

            return `
                <div class="page-header">
                    <h1 class="page-title">Quản lý Modules</h1>
                    <p class="page-subtitle">Bật/tắt và cấu hình các module của bot</p>
                </div>
                
                <div class="module-grid">
                    ${modules.map(mod => {
                        const icons = iconMap[mod.id] || { icon: 'fa-puzzle-piece', color: 'gray' };
                        return `
                        <div class="module-card" data-module-id="${mod.id}">
                            <div class="module-header">
                                <div class="flex gap-4">
                                    <div class="module-icon stat-icon ${icons.color}">
                                        <i class="fas ${icons.icon}"></i>
                                    </div>
                                    <div>
                                        <div class="module-name">${mod.name}</div>
                                        <div class="module-desc">${mod.description}</div>
                                    </div>
                                </div>
                                <label class="toggle-switch">
                                    <input type="checkbox" ${mod.enabled ? 'checked' : ''} data-module="${mod.id}" class="module-toggle">
                                    <span class="toggle-slider"></span>
                                </label>
                            </div>
                            <div class="module-stats">
                                <div class="module-stat">
                                    <div class="module-stat-value">${formatNumber(mod.usage_count || 0)}</div>
                                    <div class="module-stat-label">Lượt dùng</div>
                                </div>
                                <div class="module-stat">
                                    <div class="module-stat-value">${mod.last_used ? formatRelativeTime(mod.last_used) : '-'}</div>
                                    <div class="module-stat-label">Lần cuối</div>
                                </div>
                            </div>
                            <div class="module-actions mt-4">
                                <button class="btn btn-sm btn-secondary" onclick="openModuleConfig('${mod.id}')">
                                    <i class="fas fa-cog"></i> Cấu hình
                                </button>
                            </div>
                        </div>
                    `;}).join('')}
                </div>
            `;
        } catch (error) {
            return `<div class="card"><div class="card-body text-center text-danger">Lỗi tải modules: ${error.message}</div></div>`;
        }
    },

    async cogConfig(cogName) {
        try {
            const data = await api.getCogConfig(cogName);
            const settings = data.settings || {};
            
            return `
                <div class="page-header">
                    <div class="flex items-center gap-4">
                        <button class="btn btn-secondary" onclick="loadPage('modules')">
                            <i class="fas fa-arrow-left"></i>
                        </button>
                        <div>
                            <h1 class="page-title">Cấu hình ${data.name}</h1>
                            <p class="page-subtitle">${data.description}</p>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <h3>Cài đặt</h3>
                    </div>
                    <div class="card-body">
                        <form id="cogConfigForm" data-cog="${cogName}">
                            ${Object.entries(settings).map(([key, schema]) => `
                                <div class="form-group mb-4">
                                    <label class="form-label">${schema.label || key}</label>
                                    ${schema.type === 'boolean' ? `
                                        <label class="toggle-switch">
                                            <input type="checkbox" name="${key}" ${schema.value ? 'checked' : ''}>
                                            <span class="toggle-slider"></span>
                                        </label>
                                    ` : `
                                        <input type="number" name="${key}" 
                                            class="form-input" 
                                            value="${schema.value}" 
                                            min="${schema.min || 0}" 
                                            max="${schema.max || 999999}"
                                            step="${schema.step || 1}">
                                    `}
                                    ${schema.min !== undefined ? `<small class="text-muted">Min: ${schema.min}, Max: ${schema.max}</small>` : ''}
                                </div>
                            `).join('')}
                            
                            <div class="flex gap-4 mt-6">
                                <button type="submit" class="btn btn-primary">
                                    <i class="fas fa-save"></i> Lưu cấu hình
                                </button>
                                <button type="button" class="btn btn-secondary" onclick="loadPage('modules')">
                                    Hủy
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            `;
        } catch (error) {
            return `<div class="card"><div class="card-body text-center text-danger">Lỗi: ${error.message}</div></div>`;
        }
    },

    async economy() {
        try {
            const [stats, detailed, inventory] = await Promise.all([
                api.getEconomyStats(),
                api.get('/stats/economy/detailed'),
                api.get('/stats/inventory')
            ]);
            
            window._economyData = { stats, detailed, inventory };
            
            return `
                <div class="page-header">
                    <h1 class="page-title">Thống kê Kinh tế</h1>
                    <p class="page-subtitle">Phân tích chi tiết hệ thống kinh tế</p>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon green"><i class="fas fa-coins"></i></div>
                        <div class="stat-content">
                            <div class="stat-value">${formatNumber(stats.economy?.total_seeds || 0)}</div>
                            <div class="stat-label">Tổng Hạt lưu thông</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon blue"><i class="fas fa-chart-bar"></i></div>
                        <div class="stat-content">
                            <div class="stat-value">${formatNumber(stats.economy?.median_seeds || 0)}</div>
                            <div class="stat-label">Median (trung vị)</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon orange"><i class="fas fa-balance-scale"></i></div>
                        <div class="stat-content">
                            <div class="stat-value">${(stats.economy?.gini_coefficient || 0).toFixed(3)}</div>
                            <div class="stat-label">Hệ số Gini</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon purple"><i class="fas fa-user-tie"></i></div>
                        <div class="stat-content">
                            <div class="stat-value">${stats.advanced?.whales?.count || 0}</div>
                            <div class="stat-label">Whales (>1M)</div>
                        </div>
                    </div>
                </div>
                
                <div class="stats-grid mt-4">
                    <div class="stat-card">
                        <div class="stat-icon cyan"><i class="fas fa-box"></i></div>
                        <div class="stat-content">
                            <div class="stat-value">${formatNumber(inventory.items?.total_quantity || 0)}</div>
                            <div class="stat-label">Tổng items</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon pink"><i class="fas fa-fish"></i></div>
                        <div class="stat-content">
                            <div class="stat-value">${inventory.fish?.most_caught?.length || 0}</div>
                            <div class="stat-label">Loại cá đã bắt</div>
                        </div>
                    </div>
                </div>
                
                <div class="grid-2 mt-6">
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title"><i class="fas fa-chart-line"></i> Thu/Chi theo ngày</h3>
                        </div>
                        <div class="card-body">
                            <div class="chart-container">
                                <canvas id="economyDayChart"></canvas>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title"><i class="fas fa-chart-pie"></i> Thu nhập theo nguồn</h3>
                        </div>
                        <div class="card-body">
                            <div class="chart-container">
                                <canvas id="economyCategoryChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="grid-2 mt-6">
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title"><i class="fas fa-exchange-alt"></i> Dòng tiền theo nguồn</h3>
                        </div>
                        <div class="card-body">
                            ${(detailed.by_category || []).map(cat => `
                                <div class="flex justify-between items-center py-2 border-b border-gray-700">
                                    <span class="font-medium">${cat.category || 'Unknown'}</span>
                                    <div class="text-right">
                                        <span class="text-success">+${formatNumber(cat.earned)}</span>
                                        <span class="text-muted mx-2">/</span>
                                        <span class="text-danger">-${formatNumber(cat.spent)}</span>
                                    </div>
                                </div>
                            `).join('') || '<p class="text-muted">Không có dữ liệu</p>'}
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title"><i class="fas fa-chart-bar"></i> Phân phối tài sản</h3>
                        </div>
                        <div class="card-body">
                            <div class="chart-container">
                                <canvas id="wealthChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="grid-2 mt-6">
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title"><i class="fas fa-trophy"></i> Top Kiếm tiền (7 ngày)</h3>
                        </div>
                        <div class="card-body">
                            <table class="data-table">
                                <thead><tr><th>#</th><th>User ID</th><th>Kiếm được</th></tr></thead>
                                <tbody>
                                    ${(detailed.top_earners || []).slice(0, 5).map((u, i) => `
                                        <tr>
                                            <td>${i + 1}</td>
                                            <td><code>${u.user_id}</code></td>
                                            <td class="text-success">+${formatNumber(u.total_earned)}</td>
                                        </tr>
                                    `).join('') || '<tr><td colspan="3" class="text-center text-muted">Không có dữ liệu</td></tr>'}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title"><i class="fas fa-shopping-cart"></i> Top Chi tiêu (7 ngày)</h3>
                        </div>
                        <div class="card-body">
                            <table class="data-table">
                                <thead><tr><th>#</th><th>User ID</th><th>Chi tiêu</th></tr></thead>
                                <tbody>
                                    ${(detailed.top_spenders || []).slice(0, 5).map((u, i) => `
                                        <tr>
                                            <td>${i + 1}</td>
                                            <td><code>${u.user_id}</code></td>
                                            <td class="text-danger">-${formatNumber(u.total_spent)}</td>
                                        </tr>
                                    `).join('') || '<tr><td colspan="3" class="text-center text-muted">Không có dữ liệu</td></tr>'}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
                
                <div class="grid-2 mt-6">
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title"><i class="fas fa-box-open"></i> Top Items</h3>
                        </div>
                        <div class="card-body">
                            <table class="data-table">
                                <thead><tr><th>Item</th><th>Số lượng</th><th>Người sở hữu</th></tr></thead>
                                <tbody>
                                    ${(inventory.items?.top_items || []).slice(0, 5).map(item => `
                                        <tr>
                                            <td>${item.item_id}</td>
                                            <td>${formatNumber(item.total_quantity)}</td>
                                            <td>${item.owners}</td>
                                        </tr>
                                    `).join('') || '<tr><td colspan="3" class="text-center text-muted">Không có dữ liệu</td></tr>'}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title"><i class="fas fa-fish"></i> Top Cá bắt được</h3>
                        </div>
                        <div class="card-body">
                            <table class="data-table">
                                <thead><tr><th>Cá</th><th>Số lượng</th><th>Người bắt</th></tr></thead>
                                <tbody>
                                    ${(inventory.fish?.most_caught || []).slice(0, 5).map(fish => `
                                        <tr>
                                            <td>${fish.fish_id}</td>
                                            <td>${formatNumber(fish.total)}</td>
                                            <td>${fish.catchers}</td>
                                        </tr>
                                    `).join('') || '<tr><td colspan="3" class="text-center text-muted">Không có dữ liệu</td></tr>'}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            `;
        } catch (error) {
            return `<div class="card"><div class="card-body text-center text-danger">Lỗi: ${error.message}</div></div>`;
        }
    },

    async fishing() {
        try {
            const stats = await api.getFishingStats();
            const fishing = stats.fishing || {};
            
            return `
                <div class="page-header">
                    <h1 class="page-title">Thống kê Câu cá</h1>
                    <p class="page-subtitle">Phân tích hoạt động câu cá</p>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon blue"><i class="fas fa-fish"></i></div>
                        <div class="stat-value">${formatNumber(fishing.total_catches || 0)}</div>
                        <div class="stat-label">Tổng lượt câu</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon green"><i class="fas fa-users"></i></div>
                        <div class="stat-value">${formatNumber(fishing.active_fishers || 0)}</div>
                        <div class="stat-label">Người câu hoạt động</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon orange"><i class="fas fa-star"></i></div>
                        <div class="stat-value">${formatNumber(fishing.legendary_catches || 0)}</div>
                        <div class="stat-label">Cá huyền thoại</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon purple"><i class="fas fa-chart-line"></i></div>
                        <div class="stat-value">${formatNumber(fishing.avg_per_day || 0)}</div>
                        <div class="stat-label">TB mỗi ngày</div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title"><i class="fas fa-trophy"></i> Top câu thủ</h3>
                    </div>
                    <div class="card-body">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>Người chơi</th>
                                    <th>Tổng câu</th>
                                    <th>Huyền thoại</th>
                                    <th>XP</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${(fishing.top_fishers || []).map((fisher, i) => `
                                    <tr>
                                        <td><span class="badge ${i < 3 ? 'warning' : 'info'}">${i + 1}</span></td>
                                        <td>${fisher.username || 'Unknown'}</td>
                                        <td>${formatNumber(fisher.total_catches)}</td>
                                        <td>${formatNumber(fisher.legendary || 0)}</td>
                                        <td>${formatNumber(fisher.xp || 0)}</td>
                                    </tr>
                                `).join('') || '<tr><td colspan="5" class="text-center">Không có dữ liệu</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        } catch (error) {
            return `<div class="card"><div class="card-body text-center text-danger">Lỗi: ${error.message}</div></div>`;
        }
    },

    async config() {
        try {
            const config = await api.getConfig();
            
            return `
                <div class="page-header">
                    <h1 class="page-title">Cấu hình</h1>
                    <p class="page-subtitle">Điều chỉnh cài đặt bot</p>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title"><i class="fas fa-sliders-h"></i> Cài đặt chung</h3>
                        <button class="btn btn-primary" onclick="saveConfig()">
                            <i class="fas fa-save"></i> Lưu thay đổi
                        </button>
                    </div>
                    <div class="card-body">
                        <div class="grid-2">
                            <div class="form-group">
                                <label class="form-label">Daily Reward (Hạt)</label>
                                <input type="number" class="form-input" id="cfg_daily_reward" 
                                       value="${config.game?.daily_reward || 100}">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Fishing Cooldown (giây)</label>
                                <input type="number" class="form-input" id="cfg_fish_cooldown" 
                                       value="${config.game?.fish_cooldown || 30}">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Max Bet (Hạt)</label>
                                <input type="number" class="form-input" id="cfg_max_bet" 
                                       value="${config.game?.max_bet || 10000}">
                            </div>
                            <div class="form-group">
                                <label class="form-label">XP Multiplier</label>
                                <input type="number" class="form-input" id="cfg_xp_multi" 
                                       value="${config.game?.xp_multiplier || 1}" step="0.1">
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title"><i class="fas fa-exclamation-triangle"></i> Sự kiện</h3>
                    </div>
                    <div class="card-body">
                        <p class="text-muted">Cấu hình sự kiện thảm họa và bán cá được quản lý riêng.</p>
                        <div class="mt-4 flex gap-4">
                            <button class="btn btn-secondary" onclick="loadPage('events')">
                                <i class="fas fa-calendar-alt"></i> Quản lý sự kiện
                            </button>
                        </div>
                    </div>
                </div>
            `;
        } catch (error) {
            return `<div class="card"><div class="card-body text-center text-danger">Lỗi: ${error.message}</div></div>`;
        }
    },

    async system() {
        try {
            const stats = await api.get('/system/stats');
            
            return `
                <div class="page-header">
                    <h1 class="page-title">Hệ thống</h1>
                    <p class="page-subtitle">Giám sát tài nguyên server <span class="badge" id="wsStatus">Connecting...</span></p>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon blue"><i class="fas fa-microchip"></i></div>
                        <div class="stat-content">
                            <div class="stat-value" id="cpuUsage">${stats.cpu?.usage_percent?.toFixed(1) || 0}%</div>
                            <div class="stat-label">CPU Usage</div>
                        </div>
                        <div class="text-muted mt-2" style="font-size: 12px;">${stats.cpu?.model || 'Unknown'}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon green"><i class="fas fa-memory"></i></div>
                        <div class="stat-content">
                            <div class="stat-value" id="ramUsage">${stats.memory?.ram_percent?.toFixed(1) || 0}%</div>
                            <div class="stat-label">RAM Usage</div>
                        </div>
                        <div class="text-muted mt-2" style="font-size: 12px;" id="ramDetail">
                            ${(stats.memory?.ram_used_gb || 0).toFixed(1)}GB / ${(stats.memory?.ram_total_gb || 0).toFixed(1)}GB
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon orange"><i class="fas fa-hdd"></i></div>
                        <div class="stat-content">
                            <div class="stat-value" id="diskUsage">${stats.disk?.usage_percent?.toFixed(1) || 0}%</div>
                            <div class="stat-label">Disk Usage</div>
                        </div>
                        <div class="text-muted mt-2" style="font-size: 12px;" id="diskDetail">
                            ${(stats.disk?.used_gb || 0).toFixed(1)}GB / ${(stats.disk?.total_gb || 0).toFixed(1)}GB
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon purple"><i class="fas fa-robot"></i></div>
                        <div class="stat-content">
                            <div class="stat-value" id="botStatus">${stats.bot?.online ? 'Online' : 'Offline'}</div>
                            <div class="stat-label">Bot Status</div>
                        </div>
                        <div class="text-muted mt-2" style="font-size: 12px;" id="botUptime">
                            Uptime: ${stats.bot?.uptime || 'N/A'}
                        </div>
                    </div>
                </div>
                
                <div class="grid-2">
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title"><i class="fas fa-network-wired"></i> Network</h3>
                        </div>
                        <div class="card-body">
                            <div class="flex flex-between mb-4">
                                <span>Upload</span>
                                <span class="text-success" id="netUpload"><i class="fas fa-arrow-up"></i> ${(stats.network?.upload_speed_mbps || 0).toFixed(2)} Mbps</span>
                            </div>
                            <div class="flex flex-between">
                                <span>Download</span>
                                <span class="text-info" id="netDownload"><i class="fas fa-arrow-down"></i> ${(stats.network?.download_speed_mbps || 0).toFixed(2)} Mbps</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title"><i class="fas fa-cogs"></i> Process Info</h3>
                        </div>
                        <div class="card-body">
                            <div class="flex flex-between mb-4">
                                <span>PID</span>
                                <code id="botPid">${stats.bot?.pid || 'N/A'}</code>
                            </div>
                            <div class="flex flex-between mb-4">
                                <span>CPU (Bot)</span>
                                <span id="botCpu">${stats.bot?.cpu_percent?.toFixed(1) || 0}%</span>
                            </div>
                            <div class="flex flex-between">
                                <span>Memory (Bot)</span>
                                <span id="botMem">${stats.bot?.memory_mb?.toFixed(1) || 0} MB</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } catch (error) {
            return `<div class="card"><div class="card-body text-center text-danger">Lỗi: ${error.message}</div></div>`;
        }
    },

    async logs() {
        try {
            const data = await api.getAuditLogs();
            const logs = data.logs || [];
            const actions = data.actions || [];
            
            const actionLabels = {
                'user_update': 'Cập nhật user',
                'config_change': 'Đổi cấu hình', 
                'module_toggle': 'Bật/tắt module',
                'role_update': 'Cập nhật role',
                'login': 'Đăng nhập'
            };
            
            return `
                <div class="page-header">
                    <h1 class="page-title">Audit Logs</h1>
                    <p class="page-subtitle">Lịch sử hoạt động quản trị</p>
                </div>
                
                <div class="stats-grid mb-6">
                    <div class="stat-card">
                        <div class="stat-icon blue"><i class="fas fa-list"></i></div>
                        <div class="stat-content">
                            <div class="stat-value">${logs.length}</div>
                            <div class="stat-label">Tổng logs</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon green"><i class="fas fa-calendar-day"></i></div>
                        <div class="stat-content">
                            <div class="stat-value">${logs.filter(l => isToday(l.created_at)).length}</div>
                            <div class="stat-label">Hôm nay</div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <div class="flex gap-4">
                            <select class="form-input" id="logActionFilter" style="width: 150px;" onchange="filterLogs()">
                                <option value="">Tất cả loại</option>
                                ${actions.map(a => `<option value="${a}">${actionLabels[a] || a}</option>`).join('')}
                            </select>
                        </div>
                    </div>
                    <div class="card-body">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Thời gian</th>
                                    <th>Admin</th>
                                    <th>Hành động</th>
                                    <th>Mục tiêu</th>
                                    <th>Chi tiết</th>
                                </tr>
                            </thead>
                            <tbody id="logsTableBody">
                                ${logs.length === 0 ? `
                                    <tr><td colspan="5" class="text-center text-muted">Chưa có log nào</td></tr>
                                ` : logs.map(log => `
                                    <tr data-action="${log.action}">
                                        <td>${formatDateTime(log.created_at)}</td>
                                        <td>${log.admin_name}</td>
                                        <td><span class="badge">${actionLabels[log.action] || log.action}</span></td>
                                        <td>${log.target_type ? `${log.target_type}: ${log.target_id || '-'}` : '-'}</td>
                                        <td><code>${log.details ? JSON.stringify(log.details) : '-'}</code></td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        } catch (error) {
            return `<div class="card"><div class="card-body text-center text-danger">Lỗi: ${error.message}</div></div>`;
        }
    },

    async analytics() {
        try {
            const [cmdStats, activityStats] = await Promise.all([
                api.getCommandStats(7),
                api.getActivityStats(7)
            ]);
            
            window._analyticsData = { cmdStats, activityStats };
            
            return `
                <div class="page-header">
                    <h1 class="page-title">Phân tích</h1>
                    <p class="page-subtitle">Thống kê sử dụng lệnh và hoạt động</p>
                </div>
                
                <div class="stats-grid mb-6">
                    <div class="stat-card">
                        <div class="stat-icon blue"><i class="fas fa-terminal"></i></div>
                        <div class="stat-content">
                            <div class="stat-value">${formatNumber(cmdStats.total_commands || 0)}</div>
                            <div class="stat-label">Lệnh (7 ngày)</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon green"><i class="fas fa-check-circle"></i></div>
                        <div class="stat-content">
                            <div class="stat-value">${cmdStats.success_rate || 0}%</div>
                            <div class="stat-label">Tỷ lệ thành công</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon purple"><i class="fas fa-user-plus"></i></div>
                        <div class="stat-content">
                            <div class="stat-value">${activityStats.summary?.total_joins || 0}</div>
                            <div class="stat-label">Thành viên mới</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon ${(activityStats.summary?.net_change || 0) >= 0 ? 'green' : 'red'}">
                            <i class="fas fa-${(activityStats.summary?.net_change || 0) >= 0 ? 'arrow-up' : 'arrow-down'}"></i>
                        </div>
                        <div class="stat-content">
                            <div class="stat-value">${activityStats.summary?.net_change || 0}</div>
                            <div class="stat-label">Thay đổi ròng</div>
                        </div>
                    </div>
                </div>
                
                <div class="grid-2 mb-6">
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title"><i class="fas fa-chart-line"></i> Lệnh theo ngày</h3>
                        </div>
                        <div class="card-body">
                            <div class="chart-container">
                                <canvas id="commandsByDayChart"></canvas>
                            </div>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title"><i class="fas fa-clock"></i> Lệnh theo giờ</h3>
                        </div>
                        <div class="card-body">
                            <div class="chart-container">
                                <canvas id="commandsByHourChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="grid-2 mb-6">
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title"><i class="fas fa-chart-bar"></i> Top 10 Lệnh</h3>
                        </div>
                        <div class="card-body">
                            <div class="chart-container">
                                <canvas id="topCommandsChart"></canvas>
                            </div>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title"><i class="fas fa-puzzle-piece"></i> Theo Module</h3>
                        </div>
                        <div class="card-body">
                            <div class="chart-container">
                                <canvas id="commandsByCogChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title"><i class="fas fa-users"></i> Thành viên vào/ra</h3>
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="memberActivityChart"></canvas>
                        </div>
                    </div>
                </div>
                
                <div class="grid-2 mt-6">
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title"><i class="fas fa-trophy"></i> Top Users</h3>
                        </div>
                        <div class="card-body">
                            <table class="data-table">
                                <thead><tr><th>User ID</th><th>Số lệnh</th></tr></thead>
                                <tbody>
                                    ${(cmdStats.top_users || []).slice(0, 5).map(u => `
                                        <tr>
                                            <td><code>${u.user_id}</code></td>
                                            <td>${formatNumber(u.count)}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title"><i class="fas fa-exclamation-triangle"></i> Lỗi phổ biến</h3>
                        </div>
                        <div class="card-body">
                            <table class="data-table">
                                <thead><tr><th>Loại lỗi</th><th>Số lần</th></tr></thead>
                                <tbody>
                                    ${(cmdStats.errors || []).length === 0 ? 
                                        '<tr><td colspan="2" class="text-center text-muted">Không có lỗi</td></tr>' :
                                        (cmdStats.errors || []).slice(0, 5).map(e => `
                                            <tr>
                                                <td><code>${e.error_type}</code></td>
                                                <td>${formatNumber(e.count)}</td>
                                            </tr>
                                        `).join('')
                                    }
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            `;
        } catch (error) {
            return `<div class="card"><div class="card-body text-center text-danger">Lỗi: ${error.message}</div></div>`;
        }
    },

    async gambling() {
        try {
            const stats = await api.get('/stats/modules');
            const baucua = stats.baucua || {};
            
            return `
                <div class="page-header">
                    <h1 class="page-title">Thống kê Cờ bạc</h1>
                    <p class="page-subtitle">Bầu Cua, Xì Dách, Slot Machine</p>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon orange"><i class="fas fa-dice"></i></div>
                        <div class="stat-value">${formatNumber(baucua.total_games || 0)}</div>
                        <div class="stat-label">Ván Bầu Cua</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon green"><i class="fas fa-coins"></i></div>
                        <div class="stat-value">${formatNumber(baucua.total_wagered || 0)}</div>
                        <div class="stat-label">Tổng đặt cược</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon blue"><i class="fas fa-percentage"></i></div>
                        <div class="stat-value">${(baucua.house_edge || 0).toFixed(1)}%</div>
                        <div class="stat-label">House Edge</div>
                    </div>
                </div>
            `;
        } catch (error) {
            return `<div class="card"><div class="card-body text-center text-danger">Lỗi: ${error.message}</div></div>`;
        }
    },

    async music() {
        return `
            <div class="page-header">
                <h1 class="page-title">Thống kê Âm nhạc</h1>
                <p class="page-subtitle">Hoạt động phát nhạc</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon pink"><i class="fas fa-music"></i></div>
                    <div class="stat-value">-</div>
                    <div class="stat-label">Bài đã phát</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon blue"><i class="fas fa-clock"></i></div>
                    <div class="stat-value">-</div>
                    <div class="stat-label">Giờ phát</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon green"><i class="fas fa-list"></i></div>
                    <div class="stat-value">-</div>
                    <div class="stat-label">Playlists</div>
                </div>
            </div>
            
                <div class="card">
                <div class="card-body text-center text-muted">
                    <i class="fas fa-info-circle"></i> Thống kê âm nhạc sẽ được cập nhật khi có dữ liệu.
                </div>
            </div>
        `;
    },

    async botLogs() {
        try {
            const [stats, logsData] = await Promise.all([
                api.getBotLogStats(),
                api.getBotLogs({ limit: 200 })
            ]);
            
            window._botLogsData = logsData;
            
            const levelColors = {
                'DEBUG': 'gray',
                'INFO': 'blue', 
                'WARNING': 'orange',
                'ERROR': 'red',
                'CRITICAL': 'purple'
            };
            
            return `
                <div class="page-header">
                    <h1 class="page-title">Bot Logs</h1>
                    <p class="page-subtitle">Xem logs hoạt động của bot</p>
                </div>
                
                <div class="stats-grid mb-6">
                    <div class="stat-card">
                        <div class="stat-icon blue"><i class="fas fa-info-circle"></i></div>
                        <div class="stat-content">
                            <div class="stat-value">${stats.levels_today?.INFO || 0}</div>
                            <div class="stat-label">INFO hôm nay</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon orange"><i class="fas fa-exclamation-triangle"></i></div>
                        <div class="stat-content">
                            <div class="stat-value">${stats.levels_today?.WARNING || 0}</div>
                            <div class="stat-label">WARNING hôm nay</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon red"><i class="fas fa-times-circle"></i></div>
                        <div class="stat-content">
                            <div class="stat-value">${stats.errors_24h || 0}</div>
                            <div class="stat-label">Lỗi 24h</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon green"><i class="fas fa-file-alt"></i></div>
                        <div class="stat-content">
                            <div class="stat-value">${stats.files?.length || 0}</div>
                            <div class="stat-label">Log files</div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <div class="flex gap-4 flex-wrap">
                            <select class="form-input" id="logFileSelect" style="width: 150px;" onchange="filterBotLogs()">
                                <option value="main.log">main.log</option>
                                ${(stats.files || []).filter(f => f.name !== 'main.log').map(f => 
                                    `<option value="${f.name}">${f.name}</option>`
                                ).join('')}
                            </select>
                            <select class="form-input" id="logLevelFilter" style="width: 120px;" onchange="filterBotLogs()">
                                <option value="">Tất cả level</option>
                                <option value="DEBUG">DEBUG</option>
                                <option value="INFO">INFO</option>
                                <option value="WARNING">WARNING</option>
                                <option value="ERROR">ERROR</option>
                                <option value="CRITICAL">CRITICAL</option>
                            </select>
                            <select class="form-input" id="logModuleFilter" style="width: 150px;" onchange="filterBotLogs()">
                                <option value="">Tất cả module</option>
                                ${(logsData.modules || []).map(m => 
                                    `<option value="${m}">${m}</option>`
                                ).join('')}
                            </select>
                            <input type="text" class="form-input" id="logSearchInput" placeholder="Tìm kiếm..." style="width: 200px;" onkeyup="debounceFilterBotLogs()">
                            <input type="date" class="form-input" id="logFromDate" style="width: 140px;" onchange="filterBotLogs()">
                            <input type="date" class="form-input" id="logToDate" style="width: 140px;" onchange="filterBotLogs()">
                            <button class="btn btn-secondary" onclick="refreshBotLogs()">
                                <i class="fas fa-sync"></i>
                            </button>
                        </div>
                    </div>
                    <div class="card-body" style="max-height: 600px; overflow-y: auto;">
                        <div id="botLogsContainer">
                            ${renderBotLogs(logsData.logs || [])}
                        </div>
                        <div class="text-center mt-4 text-muted" id="logsPagination">
                            Hiển thị ${logsData.logs?.length || 0} / ${logsData.total || 0} logs
                        </div>
                    </div>
                </div>
            `;
        } catch (error) {
            return `<div class="card"><div class="card-body text-center text-danger">Lỗi: ${error.message}</div></div>`;
        }
    },

    async roles() {
        try {
            const data = await api.getRoles();
            const categories = data.categories || [];
            const total = data.total || 0;
            
            return `
                <div class="page-header">
                    <h1 class="page-title">Quản lý Roles</h1>
                    <p class="page-subtitle">Phân loại và quản lý roles theo danh mục</p>
                </div>
                
                <div class="stats-grid mb-6">
                    <div class="stat-card">
                        <div class="stat-icon purple"><i class="fas fa-user-tag"></i></div>
                        <div class="stat-content">
                            <div class="stat-value">${total}</div>
                            <div class="stat-label">Tổng roles</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon blue"><i class="fas fa-folder"></i></div>
                        <div class="stat-content">
                            <div class="stat-value">${categories.filter(c => c.is_real_category).length}</div>
                            <div class="stat-label">Danh mục</div>
                        </div>
                    </div>
                </div>
                
                <div class="roles-container">
                    ${categories.map(cat => `
                        <div class="card mb-4 role-category" data-category="${cat.id}">
                            <div class="card-header" style="border-left: 4px solid #${cat.color?.toString(16).padStart(6, '0') || '99aab5'}">
                                <div class="flex justify-between items-center">
                                    <div>
                                        <h3 class="font-semibold">${cat.name}</h3>
                                        <span class="text-sm text-muted">${cat.roles?.length || 0} roles</span>
                                    </div>
                                    ${cat.is_real_category ? `
                                        <button class="btn btn-sm btn-secondary" onclick="editCategory('${cat.id}')">
                                            <i class="fas fa-edit"></i>
                                        </button>
                                    ` : ''}
                                </div>
                            </div>
                            <div class="card-body role-list" data-category="${cat.id}">
                                ${(cat.roles || []).map(role => `
                                    <div class="role-item" data-role-id="${role.id}" draggable="true">
                                        <div class="role-color" style="background-color: #${role.color?.toString(16).padStart(6, '0') || '99aab5'}"></div>
                                        <span class="role-name">${role.name}</span>
                                        <span class="role-members text-muted">${role.member_count || 0} thành viên</span>
                                        <div class="role-actions">
                                            <button class="btn btn-xs btn-secondary" onclick="editRole('${role.id}')">
                                                <i class="fas fa-edit"></i>
                                            </button>
                                        </div>
                                    </div>
                                `).join('')}
                                ${(cat.roles || []).length === 0 ? '<div class="text-muted text-center py-4">Không có role</div>' : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
                
                <div class="card mt-4">
                    <div class="card-body">
                        <p class="text-muted text-sm">
                            <i class="fas fa-info-circle"></i> 
                            Kéo thả roles giữa các danh mục để sắp xếp. Thay đổi sẽ được lưu tự động.
                        </p>
                    </div>
                </div>
            `;
        } catch (error) {
            return `<div class="card"><div class="card-body text-center text-danger">Lỗi: ${error.message}</div></div>`;
        }
    }
};
