import { useEffect, useState } from 'react';
import { configApi } from '../api';

export default function Config() {
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Form state
  const [wormCost, setWormCost] = useState('');
  const [bucketLimit, setBucketLimit] = useState('');
  const [npcChance, setNpcChance] = useState('');

  const fetchConfig = async () => {
    setLoading(true);
    try {
      const data = await configApi.get();
      setConfig(data);
      setWormCost(data.game_settings?.worm_cost?.toString() || '');
      setBucketLimit(data.game_settings?.fish_bucket_limit?.toString() || '');
      setNpcChance(data.game_settings?.npc_encounter_chance?.toString() || '');
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const updates: any = {};
      if (wormCost) updates.worm_cost = parseInt(wormCost);
      if (bucketLimit) updates.fish_bucket_limit = parseInt(bucketLimit);
      if (npcChance) updates.npc_encounter_chance = parseFloat(npcChance);
      
      const result = await configApi.update(updates);
      alert(`Saved! ${result.note || ''}`);
      fetchConfig();
    } catch (err) {
      alert('Failed to save config');
    }
    setSaving(false);
  };

  if (loading) return <div>Loading config...</div>;

  return (
    <div>
      <h2 style={{ marginBottom: '24px' }}>System Configuration</h2>
      
      <div className="card">
        <div className="card-header">
          <span className="card-title">Fishing Settings</span>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>
              Worm Cost
            </label>
            <input
              type="number"
              value={wormCost}
              onChange={(e) => setWormCost(e.target.value)}
              placeholder="3"
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>
              Fish Bucket Limit
            </label>
            <input
              type="number"
              value={bucketLimit}
              onChange={(e) => setBucketLimit(e.target.value)}
              placeholder="15"
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>
              NPC Encounter Chance
            </label>
            <input
              type="number"
              step="0.01"
              value={npcChance}
              onChange={(e) => setNpcChance(e.target.value)}
              placeholder="0.06"
            />
          </div>
        </div>
        
        <button 
          className="btn btn-primary" 
          onClick={handleSave}
          disabled={saving}
          style={{ marginTop: '20px' }}
        >
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
        
        <p style={{ marginTop: '12px', color: 'var(--text-dim)', fontSize: '0.85rem' }}>
          Note: Changes trigger automatic hot-reload.
        </p>
      </div>

      {/* Current Config Display */}
      <div className="card" style={{ marginTop: '20px' }}>
        <div className="card-header">
          <span className="card-title">Current Configuration (Read-only)</span>
        </div>
        <pre style={{ 
          background: 'var(--bg-base)', 
          padding: '16px', 
          borderRadius: '4px',
          overflow: 'auto',
          fontSize: '0.85rem',
          color: 'var(--text-primary)',
          border: '1px solid var(--border-color)'
        }}>
          {JSON.stringify(config, null, 2)}
        </pre>
      </div>
    </div>
  );
}
