import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
});

// Types
export interface EconomyStats {
  total_seeds: number;
  total_users: number;
  top_10: { user_id: number; username: string; seeds: number }[];
  gini_index: number;
  median_balance: number;
  active_users: number;
}

export interface ModuleStats {
  fishing: { total_catches: number; active_users: number };
  baucua: { total_games: number; total_won: number; total_lost: number; house_profit: number };
  noitu: { total_words: number; active_users: number };
  inventory: { unique_items: number; total_quantity: number };
}

export interface User {
  user_id: number;
  username: string;
  seeds: number;
  created_at: string;
  last_daily: string;
}

export interface UserDetail extends User {
  inventory: { item_id: string; quantity: number; item_type: string }[];
  fishing_profile: { rod_level: number; rod_durability: number; exp: number } | null;
  fish_collection: { fish_id: string; quantity: number }[];
  stats: { game_id: string; stat_key: string; value: number }[];
  achievements: { achievement_key: string; earned_at: string }[];
  buffs: { buff_type: string; duration_type: string; end_time: number; remaining_count: number }[];
}

// API Functions
export const statsApi = {
  getEconomy: () => api.get<EconomyStats>('/stats/economy').then(r => r.data),
  getModules: () => api.get<ModuleStats>('/stats/modules').then(r => r.data),
  getDistribution: () => api.get('/stats/distribution').then(r => r.data),
  getAdvanced: () => api.get('/stats/advanced').then(r => r.data),
};

export const usersApi = {
  list: (page = 1, limit = 20, search = '') => 
    api.get('/users/', { params: { page, limit, search } }).then(r => r.data),
  get: (userId: number) => api.get<{ user: UserDetail }>(`/users/${userId}`).then(r => r.data),
  updateSeeds: (userId: number, amount: number, reason = 'Admin') => 
    api.post(`/users/${userId}/seeds`, { amount, reason }).then(r => r.data),
  getExportUrl: () => '/api/export/users',
};

export const rolesApi = {
  list: (guildId?: string) => api.get('/roles/', { params: { guild_id: guildId } }).then(r => r.data),
  update: (roleId: string, data: { name?: string; color?: number }) => 
    api.patch(`/roles/${roleId}`, data).then(r => r.data),
  create: (name: string, isCategory = false) => 
    api.post('/roles/create', { name, is_category: isCategory }).then(r => r.data),
  delete: (roleId: string) => api.delete(`/roles/${roleId}`).then(r => r.data),
  batchSubmit: (updates: any[], reorder?: any) => 
    api.post('/roles/batch', { updates, reorder }).then(r => r.data),
  batchStatus: (taskId: string) => api.get(`/roles/batch/${taskId}`).then(r => r.data),
};

export const configApi = {
  get: () => api.get('/config/').then(r => r.data),
  update: (config: any) => api.post('/config/', config).then(r => r.data),
  getEvents: () => api.get('/config/events').then(r => r.data),
};

export default api;
