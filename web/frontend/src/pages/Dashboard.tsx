import { useEffect, useState } from 'react';
import { 
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid 
} from 'recharts';
import { FileSpreadsheet } from 'lucide-react';
import ServerHealth from '../components/ServerHealth';
import { statsApi, EconomyStats, ModuleStats } from '../api';

const COLORS = ['#ef4444', '#f97316', '#eab308', '#22c5e', '#4f46e5', '#8b5cf6'];

export default function Dashboard() {

  const [economy, setEconomy] = useState<EconomyStats | null>(null);
  const [modules, setModules] = useState<ModuleStats | null>(null);
  const [distribution, setDistribution] = useState<any>(null);
  const [advanced, setAdvanced] = useState<any>(null);
  const [cashflow, setCashflow] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    Promise.allSettled([
      statsApi.getEconomy(),
      statsApi.getModules(),
      statsApi.getDistribution(),
      statsApi.getAdvanced(),
      statsApi.getCashflow(30)
    ]).then(([ecoResult, modResult, distResult, advResult, flowResult]) => {
      if (ecoResult.status === 'fulfilled') setEconomy(ecoResult.value);
      if (modResult.status === 'fulfilled') setModules(modResult.value);
      if (distResult.status === 'fulfilled') setDistribution(distResult.value);
      if (advResult.status === 'fulfilled') setAdvanced(advResult.value);
      if (flowResult.status === 'fulfilled') setCashflow(flowResult.value);
      
      if (advResult.status === 'rejected') console.error("Advanced stats failed:", advResult.reason);
      
      setLoading(false);
    }).catch(err => {
      console.error("Critical dashboard error:", err);
      setLoading(false);
    });
  }, []);

  const handleExport = async () => {
    setExporting(true);
    try {
        // Direct download via window.open is simplest for blob response, 
        // but using fetch allows us to handle errors better if needed.
        // Since it's a file download, a simple link or window.location is often easiest 
        // IF we don't need auth headers (which we arguably do if using cookies/tokens, but here we likely rely on open API or same-origin)
        
        // Using fetch to get blob
        const response = await fetch('/api/stats/export');
        if (!response.ok) throw new Error('Export failed');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `bhn_stats_${new Date().toISOString().split('T')[0]}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        
    } catch (e) {
        console.error(e);
        alert('Failed to export Excel');
    } finally {
        setExporting(false);
    }
  };

  if (loading) return <div>Loading...</div>;

  // Custom label for Pie Chart
  const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: any) => {
    if (percent < 0.05) return null;
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);
    return (
      <text x={x} y={y} fill="white" textAnchor={x > cx ? 'start' : 'end'} dominantBaseline="central">
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <div>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px'}}>
          <h2>System Overview</h2>
          <button 
            className="btn btn-primary" 
            onClick={handleExport}
            disabled={exporting}
            style={{backgroundColor: 'var(--accent-success)'}}
          >
            <FileSpreadsheet size={16} /> 
            {exporting ? 'Downloading...' : 'Export Excel'}
          </button>
      </div>
      
      {/* SERVER HEALTH MONITOR DASHBOARD */}
      <ServerHealth />

      {/* Economy Overview */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{economy?.total_seeds?.toLocaleString() || 0}</div>
          <div className="stat-label">Total Supply</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{color: 'var(--accent-success)'}}>
            {advanced?.active_circulation?.toLocaleString() || 0}
          </div>
          <div className="stat-label">Active Supply (7 Days)</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{economy?.gini_index?.toFixed(2) || 0}</div>
          <div className="stat-label">Gini Index (Inequality)</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{economy?.median_balance?.toLocaleString() || 0}</div>
          <div className="stat-label">Median Balance</div>
        </div>
      </div>

      {/* Cashflow Analysis (Real-time from Transaction Logs) */}
      <h3 style={{margin: '30px 0 15px', color: 'var(--text-secondary)'}}>Cash Flow Analysis (30 Days)</h3>
      
      {/* Summary Cards */}
      <div className="stats-grid" style={{marginBottom: '20px'}}>
        <div className="stat-card">
           <div className="stat-value" style={{color: 'var(--accent-success)'}}>
             +{cashflow?.summary?.total_in?.toLocaleString() || 0}
           </div>
           <div className="stat-label">Total Inflow</div>
        </div>
        <div className="stat-card">
           <div className="stat-value" style={{color: 'var(--accent-error)'}}>
             {cashflow?.summary?.total_out?.toLocaleString() || 0}
           </div>
           <div className="stat-label">Total Outflow</div>
        </div>
        <div className="stat-card">
           <div className="stat-value" style={{color: (cashflow?.summary?.net_flow || 0) >= 0 ? 'var(--accent-success)' : 'var(--accent-error)'}}>
             {(cashflow?.summary?.net_flow || 0) > 0 ? '+' : ''}{cashflow?.summary?.net_flow?.toLocaleString() || 0}
           </div>
           <div className="stat-label">Net Profit/Loss</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px' }}>
        
        {/* Money Inflow Breakdown */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Money Inflow (Sources)</span>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={Object.entries(cashflow?.categories || {})
                    .map(([key, data]: any) => ({ name: key, value: data.total_in }))
                    .filter((item: any) => item.value > 0)
                }
                cx="50%" cy="50%"
                innerRadius={60} outerRadius={80}
                fill="#82ca9d" paddingAngle={5}
                dataKey="value"
              >
                {Object.keys(cashflow?.categories || {})
                    .filter((key) => (cashflow?.categories[key]?.total_in || 0) > 0)
                    .map((_: any, index: number) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(val: number) => val.toLocaleString()} />
              <Legend verticalAlign="bottom" height={36}/>
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Money Outflow Breakdown */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Money Outflow (Sinks)</span>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={Object.entries(cashflow?.categories || {})
                    .map(([key, data]: any) => ({ name: key, value: Math.abs(data.total_out) }))
                    .filter((item: any) => item.value > 0)
                }
                cx="50%" cy="50%"
                innerRadius={60} outerRadius={80}
                fill="#ef4444" paddingAngle={5}
                dataKey="value"
              >
                {Object.keys(cashflow?.categories || {})
                     .filter((key) => (cashflow?.categories[key]?.total_out || 0) < 0)
                     .map((_: any, index: number) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(val: number) => val.toLocaleString()} />
              <Legend verticalAlign="bottom" height={36}/>
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Whale Alert */}
      <div className="card" style={{marginTop: '20px', borderColor: 'var(--accent-warning)'}}>
        <div className="card-header">
          <span className="card-title" style={{color: 'var(--accent-warning)'}}>Whale Alert (&gt;5% Supply)</span>
        </div>
        {advanced?.whales?.length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>Username</th>
                <th>Balance</th>
                <th>% of Supply</th>
              </tr>
            </thead>
            <tbody>
              {advanced.whales.map((whale: any) => (
                <tr key={whale.user_id}>
                  <td>{whale.username}</td>
                  <td style={{fontWeight: 'bold', color: 'var(--accent-warning)'}}>{whale.seeds.toLocaleString()}</td>
                  <td>{((whale.seeds / (economy?.total_seeds || 1)) * 100).toFixed(2)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p style={{padding: '20px', textAlign: 'center', color: 'var(--text-secondary)'}}>No whales detected</p>
        )}
      </div>

      {/* Original Distribution & Top 10 */}
      <h3 style={{margin: '30px 0 15px', color: 'var(--text-secondary)'}}>General Stats</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px' }}>
        
        {/* Wealth Distribution */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Wealth Distribution</span>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={distribution?.chart_data || []}
                cx="50%" cy="50%"
                labelLine={false}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
                label={renderCustomizedLabel}
              >
                {distribution?.chart_data?.map((_: any, index: number) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value: number) => value.toLocaleString()} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Top 10 Users Chart */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Top 10 Richest</span>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={economy?.top_10 || []} layout="vertical" margin={{ left: 40 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
              <XAxis type="number" hide />
              <YAxis 
                type="category" 
                dataKey="username" 
                width={100} 
                tick={{fill: 'var(--text-secondary)', fontSize: 12}} 
              />
              <Tooltip 
                cursor={{fill: 'rgba(255,255,255,0.05)'}}
                contentStyle={{background: 'var(--bg-surface)', border: '1px solid var(--border-color)'}}
              />
              <Bar dataKey="seeds" fill="var(--accent-primary)" radius={[0, 4, 4, 0]}>
                {economy?.top_10?.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={index < 3 ? 'var(--accent-warning)' : 'var(--accent-primary)'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Module Stats */}
      <div className="card" style={{ marginTop: '20px' }}>
        <div className="card-header">
          <span className="card-title">Game Modules</span>
        </div>
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{modules?.fishing?.total_catches?.toLocaleString() || 0}</div>
            <div className="stat-label">Total Catches</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{modules?.baucua?.total_games || 0}</div>
            <div className="stat-label">Bau Cua Games</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: (modules?.baucua?.house_profit || 0) < 0 ? 'var(--accent-error)' : 'var(--accent-success)' }}>
              {modules?.baucua?.house_profit?.toLocaleString() || 0}
            </div>
            <div className="stat-label">House Profit</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{modules?.noitu?.total_words?.toLocaleString() || 0}</div>
            <div className="stat-label">Noi Tu Words</div>
          </div>
        </div>
      </div>
    </div>
  );
}
