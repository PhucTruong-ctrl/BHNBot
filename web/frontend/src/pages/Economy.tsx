import { useState, useEffect } from 'react';
import { useGuild } from '../contexts/GuildContext';
import { Fish, Coins, Store, TrendingUp, Settings2, BarChart3, Loader2, Save, RotateCcw } from 'lucide-react';
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

interface CogConfig {
  name: string;
  display_name: string;
  description: string;
  category: string;
  settings: Record<string, ConfigField>;
}

interface ConfigField {
  type: string;
  default: unknown;
  description: string;
  min?: number;
  max?: number;
  options?: string[];
}

type TabType = 'fishing' | 'economy' | 'shop' | 'aquarium';

export default function Economy() {
  const { selectedGuild } = useGuild();
  const [economyStats, setEconomyStats] = useState<EconomyStats | null>(null);
  const [fishingStats, setFishingStats] = useState<FishingStats | null>(null);
  const [distribution, setDistribution] = useState<DistributionData[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabType>('fishing');
  const [tabConfig, setTabConfig] = useState<CogConfig | null>(null);
  const [tabLoading, setTabLoading] = useState(false);
  const [configValues, setConfigValues] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false);

  const TAB_COG_MAP: Record<TabType, string> = {
    fishing: 'fishing',
    economy: 'economy',
    shop: 'unified_shop',
    aquarium: 'aquarium',
  };

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

  // Fetch config when tab changes
  useEffect(() => {
    async function fetchTabConfig() {
      setTabLoading(true);
      try {
        const cogName = TAB_COG_MAP[activeTab];
        const res = await fetch(`/api/cogs/${cogName}`, { credentials: 'include' });
        if (res.ok) {
          const config = await res.json();
          setTabConfig(config);
          // Initialize config values with defaults
          const defaults: Record<string, unknown> = {};
          if (config.settings) {
            Object.entries(config.settings).forEach(([key, field]) => {
              defaults[key] = (field as ConfigField).default;
            });
          }
          setConfigValues(defaults);
        } else {
          setTabConfig(null);
        }
      } catch (err) {
        console.error('Failed to fetch tab config:', err);
        setTabConfig(null);
      } finally {
        setTabLoading(false);
      }
    }
    fetchTabConfig();
  }, [activeTab]);

  async function handleSaveConfig() {
    if (!tabConfig) return;
    setSaving(true);
    try {
      const res = await fetch(`/api/cogs/${TAB_COG_MAP[activeTab]}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ guild_id: selectedGuild?.id, settings: configValues }),
      });
      if (res.ok) {
        alert('Config saved!');
      } else {
        alert('Failed to save config');
      }
    } catch (err) {
      console.error('Save error:', err);
      alert('Error saving config');
    } finally {
      setSaving(false);
    }
  }

  function handleResetConfig() {
    if (!tabConfig?.settings) return;
    const defaults: Record<string, unknown> = {};
    Object.entries(tabConfig.settings).forEach(([key, field]) => {
      defaults[key] = field.default;
    });
    setConfigValues(defaults);
  }

  function updateConfigValue(key: string, value: unknown) {
    setConfigValues(prev => ({ ...prev, [key]: value }));
  }

  function renderConfigField(key: string, field: ConfigField) {
    const value = configValues[key];
    
    switch (field.type) {
      case 'boolean':
        return (
          <label className="config-toggle">
            <input
              type="checkbox"
              checked={Boolean(value)}
              onChange={(e) => updateConfigValue(key, e.target.checked)}
            />
            <span className="toggle-slider"></span>
          </label>
        );
      case 'integer':
      case 'number':
        return (
          <input
            type="number"
            className="config-input"
            value={Number(value) || 0}
            min={field.min}
            max={field.max}
            onChange={(e) => updateConfigValue(key, parseInt(e.target.value) || 0)}
          />
        );
      case 'float':
        return (
          <input
            type="number"
            className="config-input"
            value={Number(value) || 0}
            min={field.min}
            max={field.max}
            step="0.1"
            onChange={(e) => updateConfigValue(key, parseFloat(e.target.value) || 0)}
          />
        );
      case 'select':
        return (
          <select
            className="config-select"
            value={String(value)}
            onChange={(e) => updateConfigValue(key, e.target.value)}
          >
            {field.options?.map(opt => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        );
      default:
        return (
          <input
            type="text"
            className="config-input"
            value={String(value || '')}
            onChange={(e) => updateConfigValue(key, e.target.value)}
          />
        );
    }
  }

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
          <button 
            className={`config-tab ${activeTab === 'fishing' ? 'active' : ''}`}
            onClick={() => setActiveTab('fishing')}
          >
            <Fish size={16} /> Fishing
          </button>
          <button 
            className={`config-tab ${activeTab === 'economy' ? 'active' : ''}`}
            onClick={() => setActiveTab('economy')}
          >
            <Coins size={16} /> Economy
          </button>
          <button 
            className={`config-tab ${activeTab === 'shop' ? 'active' : ''}`}
            onClick={() => setActiveTab('shop')}
          >
            <Store size={16} /> Shop
          </button>
          <button 
            className={`config-tab ${activeTab === 'aquarium' ? 'active' : ''}`}
            onClick={() => setActiveTab('aquarium')}
          >
            <Fish size={16} /> Aquarium
          </button>
        </div>
        
        <div className="terminal-card config-panel">
          {tabLoading ? (
            <div className="config-loading">
              <Loader2 className="spinning" size={24} />
              <span>Loading {activeTab} config...</span>
            </div>
          ) : tabConfig ? (
            <>
              <div className="config-header">
                <div className="config-info">
                  <h3>{tabConfig.display_name}</h3>
                  <p>{tabConfig.description}</p>
                </div>
                <div className="config-actions">
                  <button className="btn btn--secondary" onClick={handleResetConfig}>
                    <RotateCcw size={14} /> Reset
                  </button>
                  <button className="btn btn--primary" onClick={handleSaveConfig} disabled={saving}>
                    {saving ? <Loader2 className="spinning" size={14} /> : <Save size={14} />}
                    {saving ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </div>
              
              <div className="config-fields">
                {tabConfig.settings && Object.entries(tabConfig.settings).map(([key, field]) => (
                  <div key={key} className="config-field">
                    <div className="config-field__info">
                      <label className="config-field__label">{key.replace(/_/g, ' ')}</label>
                      <span className="config-field__desc">{field.description}</span>
                    </div>
                    <div className="config-field__input">
                      {renderConfigField(key, field)}
                    </div>
                  </div>
                ))}
                {(!tabConfig.settings || Object.keys(tabConfig.settings).length === 0) && (
                  <p className="text-muted">No configurable settings for this module.</p>
                )}
              </div>
            </>
          ) : (
            <p className="text-muted">Failed to load config. Make sure you're logged in.</p>
          )}
        </div>
      </section>
    </div>
  );
}
