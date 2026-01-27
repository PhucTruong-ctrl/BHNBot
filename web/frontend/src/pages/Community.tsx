import { useState, useEffect } from 'react';
import { useGuild } from '../contexts/GuildContext';
import { Heart, Users, Mic, Settings2, UserPlus, Gift } from 'lucide-react';

interface VoiceStats {
  total_voice_minutes_today: number;
  users_in_voice_now: number;
  top_voice_user: { id: string; name: string; minutes: number } | null;
}

interface RelationshipStats {
  total_buddies: number;
  total_marriages: number;
  gifts_sent_today: number;
}

export default function Community() {
  const { selectedGuild } = useGuild();
  const [voiceStats] = useState<VoiceStats | null>(null);
  const [relationshipStats] = useState<RelationshipStats | null>(null);
  const [loading, setLoading] = useState(true);

  const [configs, setConfigs] = useState<Record<string, unknown>>({});

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const [social, relationship, profile] = await Promise.all([
          fetch('/api/cogs/social', { credentials: 'include' }).then(r => r.ok ? r.json() : null),
          fetch('/api/cogs/relationship', { credentials: 'include' }).then(r => r.ok ? r.json() : null),
          fetch('/api/cogs/profile', { credentials: 'include' }).then(r => r.ok ? r.json() : null),
        ]);
        setConfigs({ social, relationship, profile });
      } catch (err) {
        console.error('Failed to fetch community data:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [selectedGuild?.id]);

  if (loading) {
    return (
      <div className="page-loading">
        <Heart className="spinning" size={32} />
        <span>Loading community data...</span>
      </div>
    );
  }

  return (
    <div className="page community-page">
      <header className="page-header">
        <h1><Heart size={28} /> Community</h1>
        <p>Quản lý hệ thống social, relationship và profile</p>
      </header>

      <section className="stats-overview">
        <div className="stat-cards-grid">
          <div className="stat-card stat-card--voice">
            <Mic size={24} />
            <div className="stat-card__content">
              <span className="stat-card__value">{voiceStats?.users_in_voice_now || 0}</span>
              <span className="stat-card__label">In Voice Now</span>
            </div>
          </div>
          
          <div className="stat-card stat-card--buddies">
            <UserPlus size={24} />
            <div className="stat-card__content">
              <span className="stat-card__value">{relationshipStats?.total_buddies || 0}</span>
              <span className="stat-card__label">Total Buddies</span>
            </div>
          </div>
          
          <div className="stat-card stat-card--marriages">
            <Heart size={24} />
            <div className="stat-card__content">
              <span className="stat-card__value">{relationshipStats?.total_marriages || 0}</span>
              <span className="stat-card__label">Marriages</span>
            </div>
          </div>
          
          <div className="stat-card stat-card--gifts">
            <Gift size={24} />
            <div className="stat-card__content">
              <span className="stat-card__value">{relationshipStats?.gifts_sent_today || 0}</span>
              <span className="stat-card__label">Gifts Today</span>
            </div>
          </div>
        </div>
      </section>

      <section className="config-section">
        <h2><Settings2 size={20} /> Community Configs</h2>
        
        <div className="config-grid">
          <div className="terminal-card">
            <div className="terminal-card__header">
              <Mic size={18} />
              <span>VOICE & SOCIAL</span>
            </div>
            <div className="settings-list">
              <div className="setting-item">
                <span className="setting-item__label">XP per minute in voice</span>
                <span className="setting-item__value">{(configs.social as Record<string, unknown>)?.voice_xp_per_minute as string || '2'}</span>
              </div>
              <div className="setting-item">
                <span className="setting-item__label">Daily XP cap</span>
                <span className="setting-item__value">{(configs.social as Record<string, unknown>)?.voice_xp_cap_per_day as string || '1000'}</span>
              </div>
              <div className="setting-item">
                <span className="setting-item__label">Buddy bonus</span>
                <span className="setting-item__value">{(configs.social as Record<string, unknown>)?.buddy_voice_bonus_percent as string || '20'}%</span>
              </div>
            </div>
          </div>
          
          <div className="terminal-card">
            <div className="terminal-card__header">
              <Heart size={18} />
              <span>RELATIONSHIPS</span>
            </div>
            <div className="settings-list">
              <div className="setting-item">
                <span className="setting-item__label">Max buddies</span>
                <span className="setting-item__value">{(configs.relationship as Record<string, unknown>)?.max_buddies as string || '5'}</span>
              </div>
              <div className="setting-item">
                <span className="setting-item__label">Gift cooldown</span>
                <span className="setting-item__value">{(configs.relationship as Record<string, unknown>)?.gift_cooldown_hours as string || '24'}h</span>
              </div>
              <div className="setting-item">
                <span className="setting-item__label">Marriage enabled</span>
                <span className="setting-item__value">{(configs.relationship as Record<string, unknown>)?.enable_marriage ? '✓' : '✗'}</span>
              </div>
            </div>
          </div>
          
          <div className="terminal-card">
            <div className="terminal-card__header">
              <Users size={18} />
              <span>PROFILES</span>
            </div>
            <div className="settings-list">
              <div className="setting-item">
                <span className="setting-item__label">Badge slots</span>
                <span className="setting-item__value">{(configs.profile as Record<string, unknown>)?.badge_slots as string || '5'}</span>
              </div>
              <div className="setting-item">
                <span className="setting-item__label">Bio max length</span>
                <span className="setting-item__value">{(configs.profile as Record<string, unknown>)?.bio_max_length as string || '200'}</span>
              </div>
              <div className="setting-item">
                <span className="setting-item__label">Custom backgrounds</span>
                <span className="setting-item__value">{(configs.profile as Record<string, unknown>)?.enable_custom_backgrounds ? '✓' : '✗'}</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
