import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { LayoutDashboard, Users as UsersIcon, Shield, Settings, Terminal, FileText, Gamepad2, Fish, Heart, Calendar, Package } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Users from './pages/Users';
import Roles from './pages/Roles';
import Config from './pages/Config';
import BotLogs from './pages/BotLogs';
import Games from './pages/Games';
import Economy from './pages/Economy';
import Community from './pages/Community';
import Events from './pages/Events';
import CogManager from './pages/CogManager';
import { ThemeProvider } from './context/ThemeContext';
import { GuildProvider } from './contexts/GuildContext';
import { ThemeToggle } from './components/ThemeToggle';
import { GuildSelector } from './components/GuildSelector';

function AppContent() {
  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="brand">
          <Terminal size={24} />
          <span>BHN_ADMIN</span>
        </div>
        
        <GuildSelector />
        
        <nav>
          <div className="nav-section">
            <span className="nav-section__label">DASHBOARD</span>
            <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <LayoutDashboard size={18} />
              <span>Overview</span>
            </NavLink>
          </div>
          
          <div className="nav-section">
            <span className="nav-section__label">MANAGEMENT</span>
            <NavLink to="/users" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <UsersIcon size={18} />
              <span>Users</span>
            </NavLink>
            <NavLink to="/roles" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Shield size={18} />
              <span>Roles</span>
            </NavLink>
          </div>
          
          <div className="nav-section">
            <span className="nav-section__label">MODULES</span>
            <NavLink to="/games" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Gamepad2 size={18} />
              <span>Games</span>
            </NavLink>
            <NavLink to="/economy" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Fish size={18} />
              <span>Economy</span>
            </NavLink>
            <NavLink to="/community" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Heart size={18} />
              <span>Community</span>
            </NavLink>
            <NavLink to="/events" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Calendar size={18} />
              <span>Events</span>
            </NavLink>
            <NavLink to="/cogs" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Package size={18} />
              <span>Cogs</span>
            </NavLink>
          </div>
          
          <div className="nav-section">
            <span className="nav-section__label">SYSTEM</span>
            <NavLink to="/config" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Settings size={18} />
              <span>Config</span>
            </NavLink>
            <NavLink to="/bot-logs" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <FileText size={18} />
              <span>Logs</span>
            </NavLink>
          </div>
        </nav>
      </aside>
      <main className="main-content">
        <ThemeToggle />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/users" element={<Users />} />
          <Route path="/roles" element={<Roles />} />
          <Route path="/games" element={<Games />} />
          <Route path="/economy" element={<Economy />} />
          <Route path="/community" element={<Community />} />
          <Route path="/events" element={<Events />} />
          <Route path="/cogs" element={<CogManager />} />
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
      <GuildProvider>
        <BrowserRouter>
          <AppContent />
        </BrowserRouter>
      </GuildProvider>
    </ThemeProvider>
  );
}

export default App;
