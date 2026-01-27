import React, { useEffect, useState } from 'react';
import { 
  Cpu, 
  MemoryStick, 
  HardDrive, 
  Activity, 
  Monitor,
  Wifi
} from 'lucide-react';

// ==================== TYPES ====================

interface SystemStats {
  cpu: {
    model: string;
    usage_percent: number;
    frequency: number;
    temperature: number;
    cores: number;
    threads: number;
  };
  memory: {
    ram_total_gb: number;
    ram_used_gb: number;
    ram_percent: number;
    ram_free_gb: number;
    swap_total_gb: number;
    swap_used_gb: number;
    swap_percent: number;
  };
  disk: {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    usage_percent: number;
    read_bytes: number;
    write_bytes: number;
  };
  network: {
    upload_speed: number;
    download_speed: number;
  };
  gpu: Array<{
    name: string;
    usage: number;
    memory_used: number;
    memory_total: number;
    temperature: number;
  }>;
  bot: {
    online: boolean;
    status: string;
    pid?: number;
    cpu_percent: number;
    memory_percent: number;
    memory_mb: number;
    threads: number;
    uptime: string;
    uptime_seconds: number;
  };
  timestamp: number;
}

// ==================== HELPERS ====================

const formatBytes = (bytes: number, decimals = 2) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

const formatGb = (gb: number) => {
  if (gb < 1) return `${(gb * 1024).toFixed(0)} MB`;
  return `${gb.toFixed(1)} GB`;
};

// ==================== COMPONENTS ====================

interface StatCardProps {
    title: string;
    icon: React.ElementType;
    children: React.ReactNode;
    colorVar?: string; // e.g., var(--accent-error)
}

const StatCard: React.FC<StatCardProps> = ({ title, icon: Icon, children, colorVar = "var(--accent-primary)" }) => (
  <div className="stat-card" style={{ borderLeftColor: colorVar, display: 'flex', flexDirection: 'column', gap: '10px' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', marginBottom: '4px' }}>
      <Icon size={18} style={{ color: colorVar }} />
      <span className="stat-label" style={{ margin: 0, textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 600 }}>{title}</span>
    </div>
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      {children}
    </div>
  </div>
);

interface ProgressBarProps {
    value: number;
    color?: string;
    height?: string;
}

const ProgressBar: React.FC<ProgressBarProps> = ({ value, color = "var(--accent-primary)", height = "6px" }) => (
  <div style={{ width: '100%', backgroundColor: 'var(--bg-base)', borderRadius: '9999px', height: height, overflow: 'hidden' }}>
    <div 
      style={{ 
          width: `${Math.min(100, Math.max(0, value))}%`, 
          backgroundColor: color, 
          height: '100%',
          transition: 'width 0.3s ease-out'
      }}
    />
  </div>
);

// ==================== MAIN COMPONENT ====================

const ServerHealth: React.FC = () => {
    const [stats, setStats] = useState<SystemStats | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchStats = async () => {
            try {
                // Use relative path for proxy
                const response = await fetch('/api/system/stats');
                if (response.ok) {
                    const data = await response.json();
                    setStats(data);
                }
            } catch (error) {
                console.error("Failed to fetch system stats:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchStats();
        // Poll every 2 seconds
        const interval = setInterval(fetchStats, 2000);
        return () => clearInterval(interval);
    }, []);

    if (loading && !stats) return (
         <div className="stats-grid">
            <div className="stat-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '150px' }}>
                <span className="stat-label animate-pulse">Establishing Uplink...</span>
            </div>
        </div>
    );

    if (!stats) return null;

    return (
        <div className="stats-grid">
            
            {/* CPU STATUS */}
            <StatCard title={stats.cpu.model} icon={Cpu} colorVar="var(--accent-error)">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '8px' }}>
                    <div className="stat-value" style={{ color: 'var(--accent-error)', fontSize: '1.8rem' }}>
                        {stats.cpu.usage_percent.toFixed(1)}%
                    </div>
                    <div className="stat-label" style={{ fontFamily: 'var(--font-mono)' }}>
                         {stats.cpu.temperature > 0 ? `${stats.cpu.temperature}°C` : ''}
                    </div>
                </div>
                <ProgressBar value={stats.cpu.usage_percent} color="var(--accent-error)" />
                <div className="stat-label" style={{ display: 'flex', justifyContent: 'space-between', marginTop: '10px' }}>
                    <span>{stats.cpu.cores} Cores</span>
                    <span>{stats.cpu.frequency.toFixed(0)} MHz</span>
                </div>
            </StatCard>

            {/* MEMORY USAGE */}
            <StatCard title="RAM" icon={MemoryStick} colorVar="var(--accent-secondary)">
                 <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '8px' }}>
                    <div className="stat-value" style={{ color: 'var(--accent-secondary)', fontSize: '1.8rem' }}>
                        {stats.memory.ram_percent.toFixed(1)}%
                    </div>
                    <div className="stat-label" style={{ fontFamily: 'var(--font-mono)' }}>
                         {formatGb(stats.memory.ram_used_gb)}
                    </div>
                </div>
                <ProgressBar value={stats.memory.ram_percent} color="var(--accent-secondary)" />
                
                <div className="stat-label" style={{ marginTop: '10px' }}>
                    <span>Total: {formatGb(stats.memory.ram_total_gb)}</span>
                   {stats.memory.swap_total_gb > 0 && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', marginTop: '4px' }}>
                            <span style={{ minWidth: '40px' }}>SWAP</span>
                            <ProgressBar value={stats.memory.swap_percent} color="var(--text-dim)" height="4px" />
                        </div>
                    )}
                </div>
            </StatCard>

            {/* NETWORK & BOT */}
            <StatCard title="Network" icon={Activity} colorVar="var(--accent-success)">
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
                     <div style={{ background: 'var(--bg-base)', padding: '8px', borderRadius: 'var(--radius)' }}>
                        <div className="stat-label" style={{ fontSize: '10px', textTransform: 'uppercase' }}>Down</div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: 'var(--accent-success)', fontWeight: 'bold', fontFamily: 'var(--font-mono)' }}>
                             <Wifi size={14} style={{ transform: 'rotate(180deg)' }} />
                             {formatBytes(stats.network.download_speed)}/s
                        </div>
                     </div>
                     <div style={{ background: 'var(--bg-base)', padding: '8px', borderRadius: 'var(--radius)' }}>
                        <div className="stat-label" style={{ fontSize: '10px', textTransform: 'uppercase' }}>Up</div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: 'var(--accent-secondary)', fontWeight: 'bold', fontFamily: 'var(--font-mono)' }}>
                             <Wifi size={14} />
                             {formatBytes(stats.network.upload_speed)}/s
                        </div>
                     </div>
                </div>

                <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '10px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: stats.bot.online ? 'var(--accent-success)' : 'var(--accent-error)', boxShadow: stats.bot.online ? '0 0 8px var(--accent-success)' : 'none' }} />
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Bot Process</span>
                    </div>
                     <span className="stat-label" style={{ fontFamily: 'var(--font-mono)' }}>
                        {stats.bot.online ? stats.bot.uptime : 'OFFLINE'}
                    </span>
                </div>
            </StatCard>

             {/* DISK SPACE */}
             <StatCard title="Storage" icon={HardDrive} colorVar="var(--accent-primary)">
                 <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '8px' }}>
                    <div className="stat-value" style={{ color: 'var(--accent-primary)', fontSize: '1.8rem' }}>
                        {stats.disk.usage_percent.toFixed(0)}%
                    </div>
                    <div className="stat-label" style={{ fontFamily: 'var(--font-mono)' }}>
                         Free: {formatGb(stats.disk.free_gb)}
                    </div>
                </div>
                <ProgressBar value={stats.disk.usage_percent} color="var(--accent-primary)" />
                
                {/* GPU (Conditional) */}
                {stats.gpu.length > 0 && (
                     <div style={{ marginTop: 'auto', paddingTop: '10px', borderTop: '1px solid var(--border-color)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', marginBottom: '4px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                            <Monitor size={12} />
                            <span>{stats.gpu[0].name}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '2px' }}>
                             <span style={{ color: 'var(--accent-success)' }}>{stats.gpu[0].usage}% Load</span>
                             <span style={{ color: 'var(--accent-warning)' }}>{stats.gpu[0].temperature}°C</span>
                        </div>
                        <ProgressBar value={stats.gpu[0].usage} color="var(--accent-success)" height="4px" />
                     </div>
                )}
                 {stats.gpu.length === 0 && (
                     <div className="stat-label" style={{ marginTop: '10px' }}>
                        System Root (/)
                     </div>
                 )}
            </StatCard>

        </div>
    );
};

export default ServerHealth;
