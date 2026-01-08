import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { LayoutDashboard, Users as UsersIcon, Shield, Settings, Terminal, FileText } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Users from './pages/Users';
import Roles from './pages/Roles';
import Config from './pages/Config';
import BotLogs from './pages/BotLogs';
import { ThemeProvider } from './context/ThemeContext';
import { ThemeToggle } from './components/ThemeToggle';

function AppContent() {
  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="brand">
          <Terminal size={24} />
          <span>BHN_ADMIN</span>
        </div>
        <nav>
          <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <LayoutDashboard size={20} />
            <span>Overview</span>
          </NavLink>
          <NavLink to="/users" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <UsersIcon size={20} />
            <span>Users</span>
          </NavLink>
          <NavLink to="/roles" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <Shield size={20} />
            <span>Roles</span>
          </NavLink>
          <NavLink to="/config" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <Settings size={20} />
            <span>System</span>
          </NavLink>
          <NavLink to="/bot-logs" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <FileText size={20} />
            <span>Logs</span>
          </NavLink>
        </nav>
      </aside>
      <main className="main-content">
        <ThemeToggle />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/users" element={<Users />} />
          <Route path="/roles" element={<Roles />} />
          <Route path="/config" element={<Config />} />
          <Route path="/bot-logs" element={<BotLogs />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
