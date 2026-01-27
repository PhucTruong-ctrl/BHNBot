import { useState, useEffect } from 'react';
import { useGuild } from '../contexts/GuildContext';
import { Package, Settings2, Power, X, ChevronRight } from 'lucide-react';

interface CogCategory {
  name: string;
  icon: string;
  description: string;
}

interface CogItem {
  id: string;
  name: string;
  icon: string;
  category: string;
  description: string;
  enabled: boolean;
}

interface CogSettings {
  [key: string]: {
    type: string;
    default: number | boolean | string;
    value: number | boolean | string;
    min?: number;
    max?: number;
    step?: number;
    label: string;
  };
}

interface CogDetail extends CogItem {
  settings: CogSettings;
}

export default function CogManager() {
  const { selectedGuild } = useGuild();
  const [categories, setCategories] = useState<Record<string, CogCategory>>({});
  const [cogs, setCogs] = useState<CogItem[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedCog, setSelectedCog] = useState<CogDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [togglingCog, setTogglingCog] = useState<string | null>(null);

  const guildId = selectedGuild?.id;

  useEffect(() => {
    fetchData();
  }, [guildId]);

  async function fetchData() {
    setLoading(true);
    try {
      const [catRes, cogsRes] = await Promise.all([
        fetch('/api/cogs/categories', { credentials: 'include' }),
        fetch(`/api/cogs/?guild_id=${guildId || ''}`, { credentials: 'include' })
      ]);
      
      if (catRes.ok) {
        const catData = await catRes.json();
        setCategories(catData.categories || {});
      }
      
      if (cogsRes.ok) {
        const cogsData = await cogsRes.json();
        setCogs(cogsData.cogs || []);
      }
    } catch (err) {
      console.error('Failed to fetch cogs:', err);
    } finally {
      setLoading(false);
    }
  }

  async function openCogSettings(cogId: string) {
    try {
      const res = await fetch(`/api/cogs/${cogId}?guild_id=${guildId || ''}`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setSelectedCog(data);
      }
    } catch (err) {
      console.error('Failed to fetch cog details:', err);
    }
  }

  async function toggleCog(cogId: string, enabled: boolean) {
    setTogglingCog(cogId);
    try {
      const res = await fetch(`/api/cogs/${cogId}/toggle?guild_id=${guildId || ''}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ enabled })
      });
      
      if (res.ok) {
        setCogs(prev => prev.map(c => c.id === cogId ? { ...c, enabled } : c));
        if (selectedCog?.id === cogId) {
          setSelectedCog(prev => prev ? { ...prev, enabled } : null);
        }
      }
    } catch (err) {
      console.error('Failed to toggle cog:', err);
    } finally {
      setTogglingCog(null);
    }
  }

  async function saveSettings() {
    if (!selectedCog) return;
    setSaving(true);
    
    try {
      const settingsToSave: Record<string, unknown> = {};
      Object.entries(selectedCog.settings).forEach(([key, s]) => {
        settingsToSave[key] = s.value;
      });
      
      const res = await fetch(`/api/cogs/${selectedCog.id}?guild_id=${guildId || ''}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ settings: settingsToSave })
      });
      
      if (res.ok) {
        setSelectedCog(null);
      }
    } catch (err) {
      console.error('Failed to save settings:', err);
    } finally {
      setSaving(false);
    }
  }

  function updateSetting(key: string, value: number | boolean | string) {
    if (!selectedCog) return;
    setSelectedCog({
      ...selectedCog,
      settings: {
        ...selectedCog.settings,
        [key]: { ...selectedCog.settings[key], value }
      }
    });
  }

  function renderSettingInput(key: string, setting: CogSettings[string]) {
    if (setting.type === 'boolean') {
      return (
        <label className="toggle-switch">
          <input
            type="checkbox"
            checked={setting.value as boolean}
            onChange={(e) => updateSetting(key, e.target.checked)}
          />
          <span className="toggle-slider"></span>
        </label>
      );
    }
    
    if (setting.type === 'number') {
      return (
        <input
          type="number"
          className="input-field input-field--number"
          value={setting.value as number}
          min={setting.min}
          max={setting.max}
          step={setting.step || 1}
          onChange={(e) => updateSetting(key, parseFloat(e.target.value) || 0)}
        />
      );
    }
    
    return (
      <input
        type="text"
        className="input-field"
        value={setting.value as string}
        onChange={(e) => updateSetting(key, e.target.value)}
      />
    );
  }

  const filteredCogs = selectedCategory === 'all' 
    ? cogs 
    : cogs.filter(c => c.category === selectedCategory);

  const categoryTabs = [
    { id: 'all', name: 'All', icon: '📦' },
    ...Object.entries(categories).map(([id, cat]) => ({
      id,
      name: cat.name,
      icon: cat.icon
    }))
  ];

  if (loading) {
    return (
      <div className="page-loading">
        <Package className="spinning" size={32} />
        <span>Loading cogs...</span>
      </div>
    );
  }

  return (
    <div className="page cog-manager-page">
      <header className="page-header">
        <h1><Package size={28} /> Cog Manager</h1>
        <p>Enable/disable và cấu hình các module của bot</p>
      </header>

      {/* Category Tabs */}
      <div className="category-tabs">
        {categoryTabs.map(tab => (
          <button
            key={tab.id}
            className={`category-tab ${selectedCategory === tab.id ? 'active' : ''}`}
            onClick={() => setSelectedCategory(tab.id)}
          >
            <span className="category-tab__icon">{tab.icon}</span>
            <span>{tab.name}</span>
          </button>
        ))}
      </div>

      {/* Cogs Grid */}
      <div className="cogs-grid">
        {filteredCogs.map(cog => (
          <div 
            key={cog.id} 
            className={`cog-card ${!cog.enabled ? 'cog-card--disabled' : ''}`}
          >
            <div className="cog-card__header">
              <span className="cog-card__icon">{cog.icon}</span>
              <h3 className="cog-card__name">{cog.name}</h3>
              <button
                className={`cog-toggle ${cog.enabled ? 'active' : ''}`}
                onClick={(e) => {
                  e.stopPropagation();
                  toggleCog(cog.id, !cog.enabled);
                }}
                disabled={togglingCog === cog.id}
                title={cog.enabled ? 'Disable' : 'Enable'}
              >
                <Power size={16} />
              </button>
            </div>
            <p className="cog-card__desc">{cog.description}</p>
            <div className="cog-card__footer">
              <span className="cog-card__category">{categories[cog.category]?.name || cog.category}</span>
              <button 
                className="btn btn--sm btn--ghost"
                onClick={() => openCogSettings(cog.id)}
              >
                <Settings2 size={14} />
                <span>Settings</span>
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Settings Modal */}
      {selectedCog && (
        <div className="modal-overlay" onClick={() => setSelectedCog(null)}>
          <div className="modal cog-settings-modal" onClick={e => e.stopPropagation()}>
            <div className="modal__header">
              <span className="modal__icon">{selectedCog.icon}</span>
              <h2>{selectedCog.name}</h2>
              <button className="modal__close" onClick={() => setSelectedCog(null)}>
                <X size={20} />
              </button>
            </div>
            
            <p className="modal__desc">{selectedCog.description}</p>
            
            <div className="modal__toggle-row">
              <span>Module Status</span>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={selectedCog.enabled}
                  onChange={(e) => toggleCog(selectedCog.id, e.target.checked)}
                />
                <span className="toggle-slider"></span>
              </label>
              <span className={`status-badge ${selectedCog.enabled ? 'active' : 'inactive'}`}>
                {selectedCog.enabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
            
            <div className="settings-grid">
              {Object.entries(selectedCog.settings).map(([key, setting]) => (
                <div key={key} className="setting-row">
                  <label className="setting-label">{setting.label}</label>
                  {renderSettingInput(key, setting)}
                </div>
              ))}
            </div>
            
            <div className="modal__actions">
              <button 
                className="btn btn--ghost" 
                onClick={() => setSelectedCog(null)}
              >
                Cancel
              </button>
              <button 
                className="btn btn--primary"
                onClick={saveSettings}
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .category-tabs {
          display: flex;
          gap: 8px;
          margin-bottom: 24px;
          flex-wrap: wrap;
        }
        
        .category-tab {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 8px 16px;
          background: var(--bg-secondary);
          border: 1px solid var(--border-color);
          border-radius: 4px;
          color: var(--text-secondary);
          cursor: pointer;
          transition: all 0.15s ease;
        }
        
        .category-tab:hover {
          border-color: var(--accent-color);
          color: var(--text-primary);
        }
        
        .category-tab.active {
          background: var(--accent-color);
          border-color: var(--accent-color);
          color: #fff;
        }
        
        .category-tab__icon {
          font-size: 16px;
        }
        
        .cogs-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 16px;
        }
        
        .cog-card {
          background: var(--bg-secondary);
          border: 1px solid var(--border-color);
          border-radius: 4px;
          padding: 16px;
          transition: all 0.15s ease;
        }
        
        .cog-card:hover {
          border-color: var(--accent-color);
        }
        
        .cog-card--disabled {
          opacity: 0.6;
        }
        
        .cog-card__header {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 8px;
        }
        
        .cog-card__icon {
          font-size: 24px;
        }
        
        .cog-card__name {
          flex: 1;
          margin: 0;
          font-size: 16px;
          font-weight: 600;
        }
        
        .cog-toggle {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 32px;
          height: 32px;
          border-radius: 4px;
          border: 1px solid var(--border-color);
          background: var(--bg-primary);
          color: var(--text-secondary);
          cursor: pointer;
          transition: all 0.15s ease;
        }
        
        .cog-toggle:hover {
          border-color: var(--accent-color);
        }
        
        .cog-toggle.active {
          background: var(--success-color);
          border-color: var(--success-color);
          color: #fff;
        }
        
        .cog-card__desc {
          font-size: 13px;
          color: var(--text-secondary);
          margin: 0 0 12px 0;
          line-height: 1.4;
        }
        
        .cog-card__footer {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding-top: 12px;
          border-top: 1px solid var(--border-color);
        }
        
        .cog-card__category {
          font-size: 11px;
          text-transform: uppercase;
          color: var(--text-muted);
          letter-spacing: 0.5px;
        }
        
        .cog-settings-modal {
          width: 100%;
          max-width: 560px;
        }
        
        .modal__toggle-row {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          background: var(--bg-primary);
          border: 1px solid var(--border-color);
          border-radius: 4px;
          margin-bottom: 16px;
        }
        
        .modal__toggle-row > span:first-child {
          flex: 1;
          font-weight: 500;
        }
        
        .status-badge {
          font-size: 11px;
          padding: 4px 8px;
          border-radius: 4px;
          text-transform: uppercase;
          font-weight: 600;
        }
        
        .status-badge.active {
          background: var(--success-color);
          color: #fff;
        }
        
        .status-badge.inactive {
          background: var(--text-muted);
          color: #fff;
        }
      `}</style>
    </div>
  );
}
