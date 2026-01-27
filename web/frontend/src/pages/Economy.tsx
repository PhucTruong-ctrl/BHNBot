import { useState, useEffect } from 'react';
import { useGuild } from '../contexts/GuildContext';
import { Fish, Coins, Store, TrendingUp, Settings2, BarChart3 } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';

interface EconomyStats {
  total_users: number;
  total_coins: number;
  average_balance: number;
  median_balance: number;
  gini_coefficient: number;
  top_10_wealth_percent: number;
}

interface FishingStats {
  total_fish_caught: number;
  total_fish_sold: number;
  legendary_caught: number;
  active_fishers_today: number;
}

interface DistributionData {
  range: string;
  count: number;
}

export default function Economy() {
  const { selectedGuild } = useGuild();
  const [economyStats, setEconomyStats] = useState<EconomyStats | null>(null);
  const [fishingStats, setFishingStats] = useState<FishingStats | null>(null);
  const [distribution, setDistribution] = useState<DistributionData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const [economy, fishing, dist] = await Promise.all([
          fetch('/api/stats/economy', { credentials: 'include' }).then(r => r.ok ? r.json() : null),
          fetch('/api/stats/modules', { credentials: 'include' }).then(r => r.ok ? r.json() : null),
          fetch('/api/stats/distribution', { credentials: 'include' }).then(r => r.ok ? r.json() : []),
        ]);
        setEconomyStats(economy);
        setFishingStats(fishing?.fishing || null);
        setDistribution(dist);
      } catch (err) {
        console.error('Failed to fetch economy data:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [selectedGuild?.id]);

  function formatNumber(num: number): string {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toLocaleString();
  }

  if (loading) {
    return (
      <div className="page-loading">
        <Coins className="spinning" size={32} />
        <span>Loading economy data...</span>
      </div>
    );
  }

  return (
    <div className="page economy-page">
      <header className="page-header">
        <h1><Coins size={28} /> Economy & Fishing</h1>
        <p>Quản lý hệ thống kinh tế, câu cá, cửa hàng và hồ cá</p>
      </header>

      <section className="stats-overview">
        <div className="stat-cards-grid">
          <div className="stat-card stat-card--coins">
            <Coins size={24} />
            <div className="stat-card__content">
              <span className="stat-card__value">{formatNumber(economyStats?.total_coins || 0)}</span>
              <span className="stat-card__label">Total Hạt Coins</span>
            </div>
          </div>
          
          <div className="stat-card stat-card--fish">
            <Fish size={24} />
            <div className="stat-card__content">
              <span className="stat-card__value">{formatNumber(fishingStats?.total_fish_caught || 0)}</span>
              <span className="stat-card__label">Fish Caught</span>
            </div>
          </div>
          
          <div className="stat-card stat-card--users">
            <TrendingUp size={24} />
            <div className="stat-card__content">
              <span className="stat-card__value">{((economyStats?.gini_coefficient || 0) * 100).toFixed(1)}%</span>
              <span className="stat-card__label">Gini Index</span>
            </div>
          </div>
          
          <div className="stat-card stat-card--store">
            <Store size={24} />
            <div className="stat-card__content">
              <span className="stat-card__value">{formatNumber(economyStats?.median_balance || 0)}</span>
              <span className="stat-card__label">Median Balance</span>
            </div>
          </div>
        </div>
      </section>

      <section className="charts-section">
        <div className="chart-grid">
          <div className="terminal-card">
            <div className="terminal-card__header">
              <BarChart3 size={18} />
              <span>WEALTH DISTRIBUTION</span>
            </div>
            <div className="chart-container">
              {distribution.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={distribution}>
                    <XAxis dataKey="range" tick={{ fill: '#a6adc8', fontSize: 10 }} />
                    <YAxis tick={{ fill: '#a6adc8', fontSize: 10 }} />
                    <Tooltip 
                      contentStyle={{ background: '#1e1e2e', border: '1px solid #45475a' }}
                      labelStyle={{ color: '#cdd6f4' }}
                    />
                    <Bar dataKey="count" fill="#89b4fa" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="empty-chart">No data available</div>
              )}
            </div>
          </div>
          
          <div className="terminal-card">
            <div className="terminal-card__header">
              <Fish size={18} />
              <span>FISHING STATS</span>
            </div>
            <div className="fishing-stats-grid">
              <div className="fishing-stat">
                <span className="fishing-stat__label">Legendary Caught</span>
                <span className="fishing-stat__value legendary">{fishingStats?.legendary_caught || 0}</span>
              </div>
              <div className="fishing-stat">
                <span className="fishing-stat__label">Active Today</span>
                <span className="fishing-stat__value">{fishingStats?.active_fishers_today || 0}</span>
              </div>
              <div className="fishing-stat">
                <span className="fishing-stat__label">Fish Sold</span>
                <span className="fishing-stat__value">{formatNumber(fishingStats?.total_fish_sold || 0)}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="config-section">
        <h2><Settings2 size={20} /> Module Configs</h2>
        <div className="config-tabs">
          <button className="config-tab active">Fishing</button>
          <button className="config-tab">Economy</button>
          <button className="config-tab">Shop</button>
          <button className="config-tab">Aquarium</button>
        </div>
        <div className="terminal-card">
          <p className="text-muted">Select a module tab above to configure its settings. Changes are saved per-server.</p>
        </div>
      </section>
    </div>
  );
}
