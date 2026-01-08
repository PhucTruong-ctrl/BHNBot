import { useEffect, useState, useCallback } from 'react';
import { FileText, Search, RefreshCw, AlertTriangle, Info, Bug, AlertCircle, XCircle } from 'lucide-react';

interface LogEntry {
  timestamp: string;
  level: string;
  module: string;
  message: string;
}

interface LogFile {
  name: string;
  size: number;
  modified: string;
}

interface LogStats {
  files: LogFile[];
  total_size: number;
  levels_today: Record<string, number>;
  errors_24h: number;
}

interface LogsResponse {
  logs: LogEntry[];
  total: number;
  file: string;
  levels: Record<string, number>;
  modules: string[];
  limit: number;
  offset: number;
  error?: string;
}

const LEVEL_COLORS: Record<string, string> = {
  DEBUG: 'var(--accent-primary)',
  INFO: 'var(--accent-success)',
  WARNING: 'var(--accent-warning)',
  ERROR: 'var(--accent-error)',
  CRITICAL: '#dc2626'
};

const LEVEL_ICONS: Record<string, React.ReactNode> = {
  DEBUG: <Bug size={14} />,
  INFO: <Info size={14} />,
  WARNING: <AlertTriangle size={14} />,
  ERROR: <AlertCircle size={14} />,
  CRITICAL: <XCircle size={14} />
};

export default function BotLogs() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [stats, setStats] = useState<LogStats | null>(null);
  const [files, setFiles] = useState<LogFile[]>([]);
  const [modules, setModules] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);

  // Filters
  const [selectedFile, setSelectedFile] = useState('main.log');
  const [selectedLevel, setSelectedLevel] = useState('');
  const [selectedModule, setSelectedModule] = useState('');
  const [searchText, setSearchText] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');

  // Pagination
  const [limit] = useState(100);
  const [offset, setOffset] = useState(0);

  // Auto-refresh
  const [autoRefresh, setAutoRefresh] = useState(false);

  const fetchLogs = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      params.set('file', selectedFile);
      params.set('limit', limit.toString());
      params.set('offset', offset.toString());
      if (selectedLevel) params.set('level', selectedLevel);
      if (selectedModule) params.set('module', selectedModule);
      if (searchText) params.set('search', searchText);
      if (fromDate) params.set('from_date', fromDate);
      if (toDate) params.set('to_date', toDate);

      const response = await fetch(`/api/logs/?${params.toString()}`);
      const data: LogsResponse = await response.json();

      setLogs(data.logs || []);
      setTotal(data.total || 0);
      setModules(data.modules || []);
    } catch (err) {
      console.error('Failed to fetch logs:', err);
    }
  }, [selectedFile, selectedLevel, selectedModule, searchText, fromDate, toDate, limit, offset]);

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/logs/stats');
      const data: LogStats = await response.json();
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  const fetchFiles = async () => {
    try {
      const response = await fetch('/api/logs/files');
      const data = await response.json();
      setFiles(data.files || []);
    } catch (err) {
      console.error('Failed to fetch files:', err);
    }
  };

  useEffect(() => {
    Promise.allSettled([fetchFiles(), fetchStats()]).then(() => {
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchLogs]);

  const handleSearch = () => {
    setOffset(0);
    fetchLogs();
  };

  const handleReset = () => {
    setSelectedLevel('');
    setSelectedModule('');
    setSearchText('');
    setFromDate('');
    setToDate('');
    setOffset(0);
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2>Bot Logs</h2>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '14px' }}>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh
          </label>
          <button className="btn btn-primary" onClick={fetchLogs} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{total.toLocaleString()}</div>
          <div className="stat-label">Total Logs</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--accent-error)' }}>
            {stats?.errors_24h || 0}
          </div>
          <div className="stat-label">Errors (24h)</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--accent-warning)' }}>
            {stats?.levels_today?.WARNING || 0}
          </div>
          <div className="stat-label">Warnings Today</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{formatBytes(stats?.total_size || 0)}</div>
          <div className="stat-label">Total Log Size</div>
        </div>
      </div>

      {/* Filters */}
      <div className="card" style={{ marginTop: '20px' }}>
        <div className="card-header">
          <span className="card-title">
            <Search size={16} style={{ marginRight: '8px' }} />
            Filters
          </span>
        </div>
        <div style={{ padding: '16px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px', display: 'block' }}>Log File</label>
            <select
              value={selectedFile}
              onChange={(e) => { setSelectedFile(e.target.value); setOffset(0); }}
              style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-surface)', color: 'var(--text-primary)' }}
            >
              {files.map((f) => (
                <option key={f.name} value={f.name}>{f.name} ({formatBytes(f.size)})</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px', display: 'block' }}>Level</label>
            <select
              value={selectedLevel}
              onChange={(e) => { setSelectedLevel(e.target.value); setOffset(0); }}
              style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-surface)', color: 'var(--text-primary)' }}
            >
              <option value="">All Levels</option>
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px', display: 'block' }}>Module</label>
            <select
              value={selectedModule}
              onChange={(e) => { setSelectedModule(e.target.value); setOffset(0); }}
              style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-surface)', color: 'var(--text-primary)' }}
            >
              <option value="">All Modules</option>
              {modules.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px', display: 'block' }}>Search</label>
            <input
              type="text"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search message..."
              style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-surface)', color: 'var(--text-primary)' }}
            />
          </div>

          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px', display: 'block' }}>From Date</label>
            <input
              type="date"
              value={fromDate}
              onChange={(e) => { setFromDate(e.target.value); setOffset(0); }}
              style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-surface)', color: 'var(--text-primary)' }}
            />
          </div>

          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px', display: 'block' }}>To Date</label>
            <input
              type="date"
              value={toDate}
              onChange={(e) => { setToDate(e.target.value); setOffset(0); }}
              style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-surface)', color: 'var(--text-primary)' }}
            />
          </div>
        </div>
        <div style={{ padding: '0 16px 16px', display: 'flex', gap: '10px' }}>
          <button className="btn btn-primary" onClick={handleSearch}>
            <Search size={14} /> Search
          </button>
          <button className="btn" onClick={handleReset} style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-color)' }}>
            Reset
          </button>
        </div>
      </div>

      {/* Logs Table */}
      <div className="card" style={{ marginTop: '20px' }}>
        <div className="card-header">
          <span className="card-title">
            <FileText size={16} style={{ marginRight: '8px' }} />
            Log Entries ({total.toLocaleString()} total)
          </span>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%' }}>
            <thead>
              <tr>
                <th style={{ width: '160px' }}>Timestamp</th>
                <th style={{ width: '100px' }}>Level</th>
                <th style={{ width: '140px' }}>Module</th>
                <th>Message</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={4} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
                    No logs found
                  </td>
                </tr>
              ) : (
                logs.map((log, idx) => (
                  <tr key={idx}>
                    <td style={{ fontFamily: 'monospace', fontSize: '12px', whiteSpace: 'nowrap' }}>
                      {log.timestamp}
                    </td>
                    <td>
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontWeight: 600,
                        color: LEVEL_COLORS[log.level] || 'var(--text-primary)',
                        background: `${LEVEL_COLORS[log.level] || 'var(--text-primary)'}20`
                      }}>
                        {LEVEL_ICONS[log.level]}
                        {log.level}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'monospace', fontSize: '12px', color: 'var(--text-secondary)' }}>
                      {log.module}
                    </td>
                    <td style={{ fontFamily: 'monospace', fontSize: '12px', wordBreak: 'break-word' }}>
                      {log.message}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div style={{ padding: '16px', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '10px', borderTop: '1px solid var(--border-color)' }}>
            <button
              className="btn"
              onClick={() => setOffset(Math.max(0, offset - limit))}
              disabled={offset === 0}
              style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-color)' }}
            >
              Previous
            </button>
            <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
              Page {currentPage} of {totalPages}
            </span>
            <button
              className="btn"
              onClick={() => setOffset(offset + limit)}
              disabled={currentPage >= totalPages}
              style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-color)' }}
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
