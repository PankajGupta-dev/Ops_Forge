import { NavLink } from 'react-router-dom';

interface NavItem {
  to:    string;
  icon:  string;
  label: string;
}

const NAV_ITEMS: NavItem[] = [
  { to: '/dashboard',  icon: 'dashboard',      label: 'Dashboard'     },
  { to: '/deployments',icon: 'rocket_launch',  label: 'Deployments'   },
  { to: '/incidents',  icon: 'emergency_home', label: 'Incidents'     },
  { to: '/knowledge',  icon: 'menu_book',      label: 'Knowledge Base'},
];

const BOTTOM_ITEMS: NavItem[] = [
  { to: '/settings',   icon: 'settings',       label: 'Settings'      },
];

export default function Sidebar() {
  return (
    <nav className="fixed left-0 top-0 flex flex-col h-full w-sidebar-width
                    bg-surface-container-lowest border-r border-border-subtle z-20
                    overflow-y-auto overflow-x-hidden">

      {/* Logo */}
      <div className="h-16 flex items-center px-4 border-b border-border-subtle flex-shrink-0">
        <div className="w-8 h-8 rounded-full bg-primary-container border border-primary/30
                        flex items-center justify-center mr-3 flex-shrink-0
                        shadow-gold-glow-sm overflow-hidden">
          <span className="material-symbols-outlined text-primary text-[18px]">rocket_launch</span>
        </div>
        <div>
          <p className="font-headline text-headline-sm text-primary font-bold leading-none">OpsForge</p>
          <p className="font-mono text-[10px] text-on-surface-variant uppercase tracking-widest mt-0.5">
            AI Cloud Operations
          </p>
        </div>
      </div>

      {/* Main nav */}
      <div className="flex-1 py-3 flex flex-col gap-0.5">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              isActive ? 'nav-item-active animate-slide-in' : 'nav-item'
            }
          >
            <span className="material-symbols-outlined text-[20px] flex-shrink-0">{item.icon}</span>
            <span className="font-body text-body-md">{item.label}</span>
          </NavLink>
        ))}
      </div>

      {/* Bottom nav */}
      <div className="pb-4 border-t border-border-subtle pt-2 flex flex-col gap-0.5">
        {BOTTOM_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              isActive ? 'nav-item-active animate-slide-in' : 'nav-item'
            }
          >
            <span className="material-symbols-outlined text-[20px] flex-shrink-0">{item.icon}</span>
            <span className="font-body text-body-md">{item.label}</span>
          </NavLink>
        ))}

        {/* User badge */}
        <div className="flex items-center gap-3 py-2 px-4 mt-1">
          <div className="w-7 h-7 rounded-full bg-primary-container border border-primary/30
                          flex items-center justify-center flex-shrink-0">
            <span className="material-symbols-outlined text-primary text-[14px]">person</span>
          </div>
          <div className="min-w-0">
            <p className="font-body text-body-md text-on-surface truncate">ops-engineer</p>
            <p className="font-mono text-[10px] text-on-surface-variant">Production</p>
          </div>
        </div>
      </div>
    </nav>
  );
}
