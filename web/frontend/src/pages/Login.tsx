import { Terminal, LogIn } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export default function Login() {
  const { login, isLoading } = useAuth();

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <Terminal size={48} className="login-icon" />
          <h1>BHN_ADMIN</h1>
          <p className="login-subtitle">Discord Bot Control Panel</p>
        </div>
        
        <div className="login-content">
          <p className="login-description">
            Sign in with your Discord account to access the admin dashboard.
            You must have <strong>Administrator</strong> permissions in at least one server where the bot is present.
          </p>
          
          <button 
            className="login-button" 
            onClick={login}
            disabled={isLoading}
          >
            <LogIn size={20} />
            <span>{isLoading ? 'Loading...' : 'Sign in with Discord'}</span>
          </button>
        </div>
        
        <div className="login-footer">
          <span className="login-version">v2.0.0</span>
          <span className="login-divider">•</span>
          <span>Powered by BHNBot</span>
        </div>
      </div>
    </div>
  );
}
