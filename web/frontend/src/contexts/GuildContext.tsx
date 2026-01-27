import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';

export interface Guild {
  id: string;
  name: string;
  icon: string | null;
  permissions: number;
  is_admin: boolean;
  is_bot_in_guild: boolean;
  member_count?: number;
}

interface GuildContextType {
  guilds: Guild[];
  selectedGuild: Guild | null;
  isLoading: boolean;
  error: string | null;
  selectGuild: (guildId: string) => void;
  refreshGuilds: () => Promise<void>;
}

const GuildContext = createContext<GuildContextType | undefined>(undefined);

const SELECTED_GUILD_KEY = 'bhn_selected_guild';

export function GuildProvider({ children }: { children: ReactNode }) {
  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [selectedGuild, setSelectedGuild] = useState<Guild | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchGuilds = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/auth/guilds', {
        credentials: 'include'
      });
      
      if (!response.ok) {
        if (response.status === 401) {
          setGuilds([]);
          setSelectedGuild(null);
          return;
        }
        throw new Error('Failed to fetch guilds');
      }
      
      const data: Guild[] = await response.json();
      setGuilds(data);
      
      // Restore previously selected guild or select first available
      const savedGuildId = localStorage.getItem(SELECTED_GUILD_KEY);
      const savedGuild = data.find(g => g.id === savedGuildId);
      
      if (savedGuild) {
        setSelectedGuild(savedGuild);
      } else if (data.length > 0) {
        setSelectedGuild(data[0]);
        localStorage.setItem(SELECTED_GUILD_KEY, data[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Failed to fetch guilds:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const selectGuild = useCallback((guildId: string) => {
    const guild = guilds.find(g => g.id === guildId);
    if (guild) {
      setSelectedGuild(guild);
      localStorage.setItem(SELECTED_GUILD_KEY, guildId);
    }
  }, [guilds]);

  const refreshGuilds = useCallback(async () => {
    await fetchGuilds();
  }, [fetchGuilds]);

  // Fetch guilds on mount
  useEffect(() => {
    fetchGuilds();
  }, [fetchGuilds]);

  return (
    <GuildContext.Provider value={{
      guilds,
      selectedGuild,
      isLoading,
      error,
      selectGuild,
      refreshGuilds
    }}>
      {children}
    </GuildContext.Provider>
  );
}

export function useGuild() {
  const context = useContext(GuildContext);
  if (context === undefined) {
    throw new Error('useGuild must be used within a GuildProvider');
  }
  return context;
}

// Helper hook to get current guild ID for API calls
export function useGuildId(): string | null {
  const { selectedGuild } = useGuild();
  return selectedGuild?.id ?? null;
}

// Helper to build guild-scoped API URLs
export function useGuildApi() {
  const guildId = useGuildId();
  
  return {
    guildId,
    buildUrl: (path: string) => {
      if (!guildId) return null;
      return `/api/guilds/${guildId}${path}`;
    },
    fetch: async (path: string, options?: RequestInit) => {
      if (!guildId) throw new Error('No guild selected');
      const url = `/api/guilds/${guildId}${path}`;
      return fetch(url, { ...options, credentials: 'include' });
    }
  };
}
