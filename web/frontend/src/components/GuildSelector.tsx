import { useGuild, Guild } from '../contexts/GuildContext';
import { ChevronDown, Server, RefreshCw } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';

function getGuildIconUrl(guild: Guild): string | null {
  if (!guild.icon) return null;
  return `https://cdn.discordapp.com/icons/${guild.id}/${guild.icon}.webp?size=64`;
}

export function GuildSelector() {
  const { guilds, selectedGuild, isLoading, selectGuild, refreshGuilds } = useGuild();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (isLoading) {
    return (
      <div className="guild-selector guild-selector--loading">
        <RefreshCw className="icon spinning" size={16} />
        <span>Loading servers...</span>
      </div>
    );
  }

  if (guilds.length === 0) {
    return (
      <div className="guild-selector guild-selector--empty">
        <Server className="icon" size={16} />
        <span>No servers available</span>
      </div>
    );
  }

  return (
    <div className="guild-selector" ref={dropdownRef}>
      <button 
        className="guild-selector__trigger"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        {selectedGuild?.icon ? (
          <img 
            src={getGuildIconUrl(selectedGuild)!} 
            alt="" 
            className="guild-selector__icon"
          />
        ) : (
          <Server className="guild-selector__icon guild-selector__icon--default" size={20} />
        )}
        <span className="guild-selector__name">
          {selectedGuild?.name || 'Select Server'}
        </span>
        <ChevronDown className={`guild-selector__chevron ${isOpen ? 'rotated' : ''}`} size={16} />
      </button>

      {isOpen && (
        <div className="guild-selector__dropdown" role="listbox">
          <div className="guild-selector__header">
            <span>SELECT SERVER</span>
            <button 
              className="guild-selector__refresh"
              onClick={(e) => {
                e.stopPropagation();
                refreshGuilds();
              }}
              title="Refresh server list"
            >
              <RefreshCw size={12} />
            </button>
          </div>
          
          {guilds.map((guild) => (
            <button
              key={guild.id}
              className={`guild-selector__option ${selectedGuild?.id === guild.id ? 'selected' : ''}`}
              onClick={() => {
                selectGuild(guild.id);
                setIsOpen(false);
              }}
              role="option"
              aria-selected={selectedGuild?.id === guild.id}
            >
              {guild.icon ? (
                <img 
                  src={getGuildIconUrl(guild)!} 
                  alt="" 
                  className="guild-selector__option-icon"
                />
              ) : (
                <Server className="guild-selector__option-icon guild-selector__option-icon--default" size={20} />
              )}
              <div className="guild-selector__option-info">
                <span className="guild-selector__option-name">{guild.name}</span>
                {guild.member_count && (
                  <span className="guild-selector__option-members">
                    {guild.member_count.toLocaleString()} members
                  </span>
                )}
              </div>
              {guild.is_admin && (
                <span className="guild-selector__badge">ADMIN</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
