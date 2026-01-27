import { useState, useEffect } from 'react';
import { useGuild } from '../contexts/GuildContext';
import { Gamepad2, Users, Clock, Trophy, Settings2, Play, Square } from 'lucide-react';

interface CogConfig {
  id: string;
  name: string;
  description: string;
  settings: Record<string, {
    type: string;
    default: number | boolean | string;
    value: number | boolean | string;
    min?: number;
    max?: number;
    step?: number;
    label: string;
  }>;
}

interface ActiveGame {
  id: string;
  type: string;
  players: number;
  phase: string;
  started_at: string;
}

export default function Games() {
  const { selectedGuild } = useGuild();
  const [werewolfConfig, setWerewolfConfig] = useState<CogConfig | null>(null);
  const [xiDachConfig, setXiDachConfig] = useState<CogConfig | null>(null);
  const [gamblingConfig, setGamblingConfig] = useState<CogConfig | null>(null);
  const [activeGames] = useState<ActiveGame[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => {
    async function fetchConfigs() {
      setLoading(true);
      try {
        const [werewolf, xiDach, gambling] = await Promise.all([
          fetch('/api/cogs/werewolf', { credentials: 'include' }).then(r => r.ok ? r.json() : null),
          fetch('/api/cogs/xi_dach', { credentials: 'include' }).then(r => r.ok ? r.json() : null),
          fetch('/api/cogs/gambling', { credentials: 'include' }).then(r => r.ok ? r.json() : null),
        ]);
        setWerewolfConfig(werewolf);
        setXiDachConfig(xiDach);
        setGamblingConfig(gambling);
      } catch (err) {
        console.error('Failed to fetch game configs:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchConfigs();
  }, [selectedGuild?.id]);

  async function saveConfig(cogName: string, settings: Record<string, unknown>) {
    setSaving(cogName);
    try {
      const response = await fetch(`/api/cogs/${cogName}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ settings })
      });
      if (!response.ok) throw new Error('Failed to save');
    } catch (err) {
      console.error('Failed to save config:', err);
    } finally {
      setSaving(null);
    }
  }

  function updateSetting(config: CogConfig, key: string, value: unknown) {
    const newSettings = { ...config.settings };
    newSettings[key] = { ...newSettings[key], value: value as number | boolean | string };
    
    if (config.id === 'werewolf') {
      setWerewolfConfig({ ...config, settings: newSettings });
    } else if (config.id === 'xi_dach') {
      setXiDachConfig({ ...config, settings: newSettings });
    } else if (config.id === 'gambling') {
      setGamblingConfig({ ...config, settings: newSettings });
    }
  }

  function renderSettingInput(config: CogConfig, key: string, setting: CogConfig['settings'][string]) {
    if (setting.type === 'boolean') {
      return (
        <label className="toggle-switch">
          <input
            type="checkbox"
            checked={setting.value as boolean}
            onChange={(e) => updateSetting(config, key, e.target.checked)}
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
          onChange={(e) => updateSetting(config, key, parseFloat(e.target.value))}
        />
      );
    }
    
    return (
      <input
        type="text"
        className="input-field"
        value={setting.value as string}
        onChange={(e) => updateSetting(config, key, e.target.value)}
      />
    );
  }

  function renderConfigCard(config: CogConfig | null, icon: React.ReactNode) {
    if (!config) return null;
    
    const settingsToSave: Record<string, unknown> = {};
    Object.entries(config.settings).forEach(([key, s]) => {
      settingsToSave[key] = s.value;
    });
    
    return (
      <div className="terminal-card">
        <div className="terminal-card__header">
          {icon}
          <span>{config.name.toUpperCase()}</span>
          <button 
            className="btn btn--primary btn--sm"
            onClick={() => saveConfig(config.id, settingsToSave)}
            disabled={saving === config.id}
          >
            {saving === config.id ? 'Saving...' : 'Save'}
          </button>
        </div>
        <p className="terminal-card__desc">{config.description}</p>
        <div className="settings-grid">
          {Object.entries(config.settings).map(([key, setting]) => (
            <div key={key} className="setting-row">
              <label className="setting-label">{setting.label}</label>
              {renderSettingInput(config, key, setting)}
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="page-loading">
        <Gamepad2 className="spinning" size={32} />
        <span>Loading game configs...</span>
      </div>
    );
  }

  return (
    <div className="page games-page">
      <header className="page-header">
        <h1><Gamepad2 size={28} /> Games Management</h1>
        <p>Configure Ma Sói, Xì Dách, Bầu Cua và các minigame khác</p>
      </header>

      <section className="active-games">
        <h2><Play size={20} /> Active Games</h2>
        {activeGames.length === 0 ? (
          <div className="empty-state">
            <Square size={24} />
            <span>No active games</span>
          </div>
        ) : (
          <div className="games-grid">
            {activeGames.map(game => (
              <div key={game.id} className="game-card">
                <div className="game-card__type">{game.type}</div>
                <div className="game-card__info">
                  <span><Users size={14} /> {game.players} players</span>
                  <span><Clock size={14} /> {game.phase}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="config-section">
        <h2><Settings2 size={20} /> Game Settings</h2>
        <div className="config-grid">
          {renderConfigCard(werewolfConfig, <Trophy size={20} />)}
          {renderConfigCard(xiDachConfig, <Gamepad2 size={20} />)}
          {renderConfigCard(gamblingConfig, <Gamepad2 size={20} />)}
        </div>
      </section>
    </div>
  );
}
