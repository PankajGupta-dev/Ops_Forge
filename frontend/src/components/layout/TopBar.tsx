import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function TopBar() {
  const [search, setSearch] = useState('');
  const navigate = useNavigate();

  return (
    <header className="fixed top-0 right-0 left-sidebar-width h-topbar-height
                       flex items-center justify-between px-margin-page z-10
                       border-b border-border-subtle bg-surface-container-lowest">

      {/* Search */}
      <div className="flex items-center w-64 bg-surface-container border border-border-subtle
                      rounded-md px-3 py-1.5 focus-within:border-primary transition-colors duration-150">
        <span className="material-symbols-outlined text-on-surface-variant text-[16px] mr-2 select-none">
          search
        </span>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="bg-transparent border-none outline-none font-mono text-mono-data
                     w-full placeholder:text-on-surface-variant text-on-surface p-0 focus:ring-0"
          placeholder="Search resources..."
          type="text"
        />
      </div>

      {/* Right cluster */}
      <div className="flex items-center gap-3">

        {/* Env badge */}
        <div className="flex items-center gap-2 border-r border-border-subtle pr-4">
          <span className="w-2 h-2 rounded-full bg-success animate-pulse-dot" />
          <span className="font-mono text-mono-data text-on-surface-variant uppercase tracking-wider">
            Production
          </span>
        </div>

        {/* Notifications */}
        <button
          className="text-on-surface-variant hover:text-primary hover:bg-surface-container
                     rounded-md p-2 transition-all duration-150 active:scale-95"
          aria-label="Notifications"
        >
          <span className="material-symbols-outlined text-[20px]">notifications</span>
        </button>

        {/* Help */}
        <button
          className="text-on-surface-variant hover:text-primary hover:bg-surface-container
                     rounded-md p-2 transition-all duration-150 active:scale-95"
          aria-label="Help"
        >
          <span className="material-symbols-outlined text-[20px]">help_outline</span>
        </button>

        {/* User avatar */}
        <button
          onClick={() => navigate('/settings')}
          className="w-8 h-8 rounded-full bg-primary-container border border-primary/30
                     flex items-center justify-center ml-1 hover:shadow-gold-glow-sm
                     transition-all duration-150 active:scale-95"
          aria-label="Account settings"
        >
          <span className="material-symbols-outlined text-primary text-[16px]">person</span>
        </button>
      </div>
    </header>
  );
}
