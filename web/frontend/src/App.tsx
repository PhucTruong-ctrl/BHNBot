import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Users from './pages/Users';
import Roles from './pages/Roles';
import Config from './pages/Config';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <aside className="sidebar">
          <h1>🏠 BHN Admin</h1>
          <nav>
            <ul className="nav-links">
              <li><NavLink to="/">📊 Dashboard</NavLink></li>
              <li><NavLink to="/users">👥 Users</NavLink></li>
              <li><NavLink to="/roles">🎭 Roles</NavLink></li>
              <li><NavLink to="/config">⚙️ Config</NavLink></li>
            </ul>
          </nav>
        </aside>
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/users" element={<Users />} />
            <Route path="/roles" element={<Roles />} />
            <Route path="/config" element={<Config />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
