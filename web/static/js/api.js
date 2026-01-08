const API_BASE = '/api';

const api = {
    async request(method, endpoint, data = null) {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
            },
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        try {
            const response = await fetch(`${API_BASE}${endpoint}`, options);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },
    
    get(endpoint) {
        return this.request('GET', endpoint);
    },
    
    post(endpoint, data) {
        return this.request('POST', endpoint, data);
    },
    
    patch(endpoint, data) {
        return this.request('PATCH', endpoint, data);
    },
    
    delete(endpoint) {
        return this.request('DELETE', endpoint);
    },

    async getStats() {
        const [economy, modules, system, distribution] = await Promise.all([
            this.get('/stats/economy'),
            this.get('/stats/modules'),
            this.get('/system/stats'),
            this.get('/stats/distribution')
        ]);
        return { economy, modules, system, distribution };
    },

    async getEconomyStats() {
        const [economy, advanced, cashflow, distribution] = await Promise.all([
            this.get('/stats/economy'),
            this.get('/stats/advanced'),
            this.get('/stats/cashflow'),
            this.get('/stats/distribution')
        ]);
        return { economy, advanced, cashflow, distribution };
    },

    async getUsers(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/users${query ? '?' + query : ''}`);
    },

    async getUser(userId) {
        return this.get(`/users/${userId}`);
    },

    async updateUser(userId, data) {
        return this.patch(`/users/${userId}`, data);
    },

    async adjustSeeds(userId, amount, reason) {
        return this.post(`/users/${userId}/seeds`, { amount, reason });
    },

    async getConfig() {
        return this.get('/config');
    },

    async updateConfig(config) {
        return this.post('/config', config);
    },

    async getModules() {
        return this.get('/modules');
    },

    async toggleModule(moduleId, enabled) {
        return this.post(`/modules/${moduleId}/toggle`, { enabled });
    },

    async getAuditLogs(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/audit/${query ? '?' + query : ''}`);
    },

    async getCommandStats() {
        return this.get('/stats/commands');
    },

    async getFishingStats() {
        return this.get('/stats/modules');
    },

    async getMusicStats() {
        return this.get('/stats/music');
    },

    async getRoles() {
        return this.get('/roles');
    },

    async updateRole(roleId, data) {
        return this.patch(`/roles/${roleId}`, data);
    },

    async createRole(data) {
        return this.post('/roles/create', data);
    },

    async deleteRole(roleId) {
        return this.delete(`/roles/${roleId}`);
    },

    async batchUpdateRoles(updates, reorder) {
        return this.post('/roles/batch', { updates, reorder });
    },

    async getBatchStatus(taskId) {
        return this.get(`/roles/batch/${taskId}`);
    },

    async getActivityStats(days = 7) {
        return this.get(`/stats/activity?days=${days}`);
    },

    async getCommandStats(days = 7) {
        return this.get(`/stats/commands?days=${days}`);
    },

    async getCogList() {
        return this.get('/cogs');
    },

    async getCogConfig(cogName) {
        return this.get(`/cogs/${cogName}`);
    },

    async updateCogConfig(cogName, settings) {
        return this.post(`/cogs/${cogName}`, { settings });
    },

    async getBotLogs(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/logs/${query ? '?' + query : ''}`);
    },

    async getBotLogFiles() {
        return this.get('/logs/files/');
    },

    async getBotLogStats() {
        return this.get('/logs/stats/');
    },

    async tailBotLogs(file = 'main.log', lines = 100) {
        return this.get(`/logs/tail/?file=${file}&lines=${lines}`);
    }
};

function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    if (num >= 1e9) return (num / 1e9).toFixed(1) + 'B';
    if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M';
    if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K';
    return num.toLocaleString('vi-VN');
}

function formatPercent(value, decimals = 1) {
    return (value * 100).toFixed(decimals) + '%';
}

function formatDuration(ms) {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) return `${days}d ${hours % 24}h`;
    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
}

function formatTimeAgo(date) {
    const now = new Date();
    const past = new Date(date);
    const diff = now - past;
    
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) return `${days} ngày trước`;
    if (hours > 0) return `${hours} giờ trước`;
    if (minutes > 0) return `${minutes} phút trước`;
    return 'Vừa xong';
}
