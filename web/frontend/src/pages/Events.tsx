import { useState, useEffect } from 'react';
import { useGuild } from '../contexts/GuildContext';
import { Calendar, Gift, Target, Star, Settings2, Clock, Trophy } from 'lucide-react';

interface EventInfo {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
  participants: number;
}

interface QuestProgress {
  daily_completed: number;
  daily_total: number;
  weekly_completed: number;
  weekly_total: number;
  users_with_streak: number;
}

interface GiveawayInfo {
  id: string;
  prize: string;
  entries: number;
  ends_at: string;
}

export default function Events() {
  const { selectedGuild } = useGuild();
  const [currentEvent] = useState<EventInfo | null>(null);
  const [questProgress] = useState<QuestProgress | null>(null);
  const [activeGiveaways] = useState<GiveawayInfo[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [configs, setConfigs] = useState<Record<string, unknown>>({});

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const [seasonal, quest, giveaway] = await Promise.all([
          fetch('/api/cogs/seasonal', { credentials: 'include' }).then(r => r.ok ? r.json() : null),
          fetch('/api/cogs/quest', { credentials: 'include' }).then(r => r.ok ? r.json() : null),
          fetch('/api/cogs/giveaway', { credentials: 'include' }).then(r => r.ok ? r.json() : null),
        ]);
        setConfigs({ seasonal, quest, giveaway });
      } catch (err) {
        console.error('Failed to fetch events data:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [selectedGuild?.id]);

  if (loading) {
    return (
      <div className="page-loading">
        <Calendar className="spinning" size={32} />
        <span>Loading events data...</span>
      </div>
    );
  }

  return (
    <div className="page events-page">
      <header className="page-header">
        <h1><Calendar size={28} /> Events & Quests</h1>
        <p>Quản lý sự kiện theo mùa, nhiệm vụ và giveaway</p>
      </header>

      <section className="current-event">
        <h2><Star size={20} /> Current Event</h2>
        {currentEvent ? (
          <div className="event-card event-card--active">
            <div className="event-card__header">
              <span className="event-card__name">{currentEvent.name}</span>
              <span className="event-card__badge">ACTIVE</span>
            </div>
            <div className="event-card__details">
              <span><Clock size={14} /> Ends: {new Date(currentEvent.end_date).toLocaleDateString()}</span>
              <span><Trophy size={14} /> {currentEvent.participants} participants</span>
            </div>
          </div>
        ) : (
          <div className="empty-state">
            <Calendar size={24} />
            <span>No active event</span>
            <p className="text-muted">Configure seasonal events in settings below</p>
          </div>
        )}
      </section>

      <section className="quests-section">
        <h2><Target size={20} /> Quest Progress (Server-wide)</h2>
        <div className="quest-stats-grid">
          <div className="terminal-card quest-stat">
            <span className="quest-stat__label">Daily Quests Completed</span>
            <div className="quest-stat__progress">
              <div className="progress-bar">
                <div className="progress-bar__fill" style={{ width: `${((questProgress?.daily_completed || 0) / (questProgress?.daily_total || 1)) * 100}%` }}></div>
              </div>
              <span className="quest-stat__value">{questProgress?.daily_completed || 0} / {questProgress?.daily_total || 0}</span>
            </div>
          </div>
          
          <div className="terminal-card quest-stat">
            <span className="quest-stat__label">Weekly Quests Completed</span>
            <div className="quest-stat__progress">
              <div className="progress-bar">
                <div className="progress-bar__fill" style={{ width: `${((questProgress?.weekly_completed || 0) / (questProgress?.weekly_total || 1)) * 100}%` }}></div>
              </div>
              <span className="quest-stat__value">{questProgress?.weekly_completed || 0} / {questProgress?.weekly_total || 0}</span>
            </div>
          </div>
          
          <div className="terminal-card quest-stat">
            <span className="quest-stat__label">Users with Active Streak</span>
            <span className="quest-stat__value big">{questProgress?.users_with_streak || 0}</span>
          </div>
        </div>
      </section>

      <section className="giveaways-section">
        <h2><Gift size={20} /> Active Giveaways</h2>
        {activeGiveaways.length > 0 ? (
          <div className="giveaway-grid">
            {activeGiveaways.map(giveaway => (
              <div key={giveaway.id} className="giveaway-card">
                <div className="giveaway-card__prize">{giveaway.prize}</div>
                <div className="giveaway-card__info">
                  <span>{giveaway.entries} entries</span>
                  <span>Ends: {new Date(giveaway.ends_at).toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <Gift size={24} />
            <span>No active giveaways</span>
          </div>
        )}
      </section>

      <section className="config-section">
        <h2><Settings2 size={20} /> Event Configs</h2>
        <div className="config-grid">
          <div className="terminal-card">
            <div className="terminal-card__header">
              <Star size={18} />
              <span>SEASONAL EVENTS</span>
            </div>
            <div className="settings-list">
              <div className="setting-item">
                <span className="setting-item__label">Current Event ID</span>
                <span className="setting-item__value">{(configs.seasonal as Record<string, unknown>)?.current_event as string || 'None'}</span>
              </div>
              <div className="setting-item">
                <span className="setting-item__label">Bonus Multiplier</span>
                <span className="setting-item__value">{(configs.seasonal as Record<string, unknown>)?.event_bonus_multiplier as string || '2'}x</span>
              </div>
              <div className="setting-item">
                <span className="setting-item__label">Event Shop</span>
                <span className="setting-item__value">{(configs.seasonal as Record<string, unknown>)?.event_shop_enabled ? '✓' : '✗'}</span>
              </div>
            </div>
          </div>
          
          <div className="terminal-card">
            <div className="terminal-card__header">
              <Target size={18} />
              <span>QUESTS</span>
            </div>
            <div className="settings-list">
              <div className="setting-item">
                <span className="setting-item__label">Daily Quests</span>
                <span className="setting-item__value">{(configs.quest as Record<string, unknown>)?.daily_quest_count as string || '3'}</span>
              </div>
              <div className="setting-item">
                <span className="setting-item__label">Weekly Quests</span>
                <span className="setting-item__value">{(configs.quest as Record<string, unknown>)?.weekly_quest_count as string || '5'}</span>
              </div>
              <div className="setting-item">
                <span className="setting-item__label">Streak Bonus</span>
                <span className="setting-item__value">{(configs.quest as Record<string, unknown>)?.streak_bonus_percent as string || '10'}%</span>
              </div>
            </div>
          </div>
          
          <div className="terminal-card">
            <div className="terminal-card__header">
              <Gift size={18} />
              <span>GIVEAWAYS</span>
            </div>
            <div className="settings-list">
              <div className="setting-item">
                <span className="setting-item__label">Default Duration</span>
                <span className="setting-item__value">{(configs.giveaway as Record<string, unknown>)?.default_duration_hours as string || '24'}h</span>
              </div>
              <div className="setting-item">
                <span className="setting-item__label">Max Winners</span>
                <span className="setting-item__value">{(configs.giveaway as Record<string, unknown>)?.max_winners as string || '10'}</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
