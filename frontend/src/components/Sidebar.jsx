import React, { useEffect, useRef, useState } from 'react';

const NAV_ITEMS = [
  {
    tab: 'dashboard',
    label: 'Dashboard',
    icon: (
      <svg width="17" height="17" viewBox="0 0 17 17" fill="none">
        <rect x="1.5" y="1.5" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.4" />
        <rect x="9.5" y="1.5" width="6" height="9" rx="1" stroke="currentColor" strokeWidth="1.4" />
        <rect x="1.5" y="9.5" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.4" />
      </svg>
    ),
  },
  {
    tab: 'new-recommendation',
    label: 'Analyze Tender',
    icon: (
      <svg width="17" height="17" viewBox="0 0 17 17" fill="none">
        <path d="M3 1.5h7l4 4v10a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1v-13a1 1 0 0 1 1-1Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
        <path d="M10 1.5v4h4" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
        <path d="M4.5 9.5h6M4.5 12h6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    tab: 'standards',
    label: 'Standards',
    icon: (
      <svg width="17" height="17" viewBox="0 0 17 17" fill="none">
        <path d="M2 3a1 1 0 0 1 1-1h4.5v13H3a1 1 0 0 1-1-1V3Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
        <path d="M15 3a1 1 0 0 0-1-1H9.5v13H14a1 1 0 0 0 1-1V3Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    tab: 'history',
    label: 'History & Analytics',
    // Analytics was merged into the history page; keep its tab highlighted here.
    aliases: ['analytics', 'results'],
    icon: (
      <svg width="17" height="17" viewBox="0 0 17 17" fill="none">
        <circle cx="8.5" cy="8.5" r="6.5" stroke="currentColor" strokeWidth="1.4" />
        <path d="M8.5 5v3.7l2.6 1.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
];

export default function Sidebar({ activeTab, setActiveTab, user, onLogout }) {
  const isAdmin = (user?.role || '').toLowerCase() === 'admin';
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const onDown = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    const onKey = (e) => { if (e.key === 'Escape') setMenuOpen(false); };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [menuOpen]);

  const initial = (user?.full_name?.charAt(0) || user?.email?.charAt(0) || 'U').toUpperCase();

  const go = (tab) => {
    setActiveTab(tab);
    setMenuOpen(false);
  };

  return (
    <aside className="ledger-sidebar">
      <div className="ledger-brand">
        <div className="ledger-brand-mark">IS</div>
        <div>
          <h2 className="ledger-brand-title">Standards Engine</h2>
          <span className="ledger-brand-sub">BIS procurement advisor</span>
        </div>
      </div>

      <nav className="ledger-nav" aria-label="Main">
        {NAV_ITEMS.map((item) => {
          const active = activeTab === item.tab || item.aliases?.includes(activeTab);
          return (
            <button
              key={item.tab}
              type="button"
              onClick={() => go(item.tab)}
              className={`ledger-nav-item${active ? ' is-active' : ''}`}
              aria-current={active ? 'page' : undefined}
              title={item.label}
            >
              <span className="ledger-nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </button>
          );
        })}
      </nav>

      {user && (
        <div className="user-menu" ref={menuRef}>
          {menuOpen && (
            <div className="user-menu-panel" role="menu">
              <div className="user-menu-head">
                <strong>{user.full_name || 'Signed in'}</strong>
                <span>{user.email}</span>
                <span>Role: {user.role || 'User'}</span>
              </div>
              {isAdmin && (
                <>
                  <button
                    type="button"
                    role="menuitem"
                    className={`user-menu-item${activeTab === 'admin-standards' ? ' is-active' : ''}`}
                    onClick={() => go('admin-standards')}
                  >
                    Admin · Standards ingestion
                  </button>
                  <div className="user-menu-divider" />
                </>
              )}
              <button type="button" role="menuitem" className="user-menu-item user-menu-item--danger" onClick={onLogout}>
                Sign out
              </button>
            </div>
          )}
          <button
            type="button"
            className="user-menu-trigger"
            onClick={() => setMenuOpen((o) => !o)}
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            title="Account"
          >
            <span className="user-avatar">{initial}</span>
            <span className="user-info">
              <span className="user-name" style={{ display: 'block' }}>{user.full_name || user.email}</span>
              <span className="user-role">{isAdmin ? 'Administrator' : 'Procurement user'}</span>
            </span>
            <svg className="user-chevron" width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <path d="M3 7.5 6 4.5l3 3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      )}
    </aside>
  );
}
