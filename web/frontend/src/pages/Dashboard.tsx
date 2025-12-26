import { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { statsApi, EconomyStats, ModuleStats } from '../api';

const COLORS = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#4f46e5'];

export default function Dashboard() {
  const [economy, setEconomy] = useState<EconomyStats | null>(null);
  const [modules, setModules] = useState<ModuleStats | null>(null);
  const [distribution, setDistribution] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      statsApi.getEconomy(),
      statsApi.getModules(),
      statsApi.getDistribution()
    ]).then(([eco, mod, dist]) => {
      setEconomy(eco);
      setModules(mod);
      setDistribution(dist);
      setLoading(false);
    }).catch(err => {
      console.error(err);
      setLoading(false);
    });
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <h2 style={{ marginBottom: '24px' }}>📊 Dashboard</h2>
      
      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{economy?.total_seeds?.toLocaleString() || 0}</div>
          <div className="stat-label">Tổng Hạt</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{economy?.total_users || 0}</div>
          <div className="stat-label">Tổng Users</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{economy?.gini_index?.toFixed(2) || 0}</div>
          <div className="stat-label">Gini Index</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{economy?.median_balance?.toLocaleString() || 0}</div>
          <div className="stat-label">Median Balance</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Wealth Distribution Chart */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Phân Bố Tài Sản</span>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={distribution?.chart_data || []}
                cx="50%"
                cy="50%"
                labelLine={false}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
                label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
              >
                {distribution?.chart_data?.map((_: any, index: number) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Top 10 Users */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Top 10 Người Giàu Nhất</span>
          </div>
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Username</th>
                <th>Balance</th>
              </tr>
            </thead>
            <tbody>
              {economy?.top_10?.map((user, i) => (
                <tr key={user.user_id}>
                  <td>{i + 1}</td>
                  <td>{user.username || `User#${user.user_id}`}</td>
                  <td>{user.seeds.toLocaleString()} 🌱</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Module Stats */}
      <div className="card" style={{ marginTop: '20px' }}>
        <div className="card-header">
          <span className="card-title">📈 Module Stats</span>
        </div>
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{modules?.fishing?.total_catches?.toLocaleString() || 0}</div>
            <div className="stat-label">🎣 Cá Đã Câu</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{modules?.baucua?.total_games || 0}</div>
            <div className="stat-label">🎲 Ván Bầu Cua</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: (modules?.baucua?.house_profit || 0) < 0 ? '#ef4444' : '#22c55e' }}>
              {modules?.baucua?.house_profit?.toLocaleString() || 0}
            </div>
            <div className="stat-label">💰 House Profit</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{modules?.noitu?.total_words?.toLocaleString() || 0}</div>
            <div className="stat-label">📝 Từ Nối Từ</div>
          </div>
        </div>
      </div>
    </div>
  );
}
