import React, { useState } from 'react';

export default function Sidebar({
  activeTab,
  setActiveTab,
  user,
  onLogout,
}) {
  const [profileOpen, setProfileOpen] = useState(false);

  const getInitial = () => {
    return (
      user?.full_name?.charAt(0) ||
      user?.email?.charAt(0) ||
      'U'
    ).toUpperCase();
  };

  return (
    <aside className="sidebar" style={{ width: '260px', background: '#0f172a', color: '#f8fafc', height: '100vh', display: 'flex', flexDirection: 'column', padding: '20px 16px', boxSizing: 'border-box' }}>
      
      {/* Brand Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '32px', paddingBottom: '16px', borderBottom: '1px solid #334155' }}>
        <div style={{ width: '38px', height: '38px', background: 'linear-gradient(135deg, #2563eb, #1d4ed8)', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.4rem' }}>
          🇮🇳
        </div>
        <div>
          <h2 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#ffffff', margin: 0, letterSpacing: '-0.01em' }}>
            IS Procurement AI
          </h2>
          <span style={{ fontSize: '0.68rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            BIS Standards Engine
          </span>
        </div>
      </div>

      {/* Navigation Links */}
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '6px', flex: 1 }}>
        <button
          onClick={() => setActiveTab('dashboard')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            width: '100%',
            padding: '12px 14px',
            borderRadius: '8px',
            border: 'none',
            background: activeTab === 'dashboard' ? '#2563eb' : 'transparent',
            color: activeTab === 'dashboard' ? '#ffffff' : '#cbd5e1',
            fontWeight: activeTab === 'dashboard' ? '700' : '500',
            cursor: 'pointer',
            textAlign: 'left',
            fontSize: '0.9rem'
          }}
        >
          <span>📊</span> Dashboard
        </button>

        <button
          onClick={() => setActiveTab('new-recommendation')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            width: '100%',
            padding: '12px 14px',
            borderRadius: '8px',
            border: 'none',
            background: activeTab === 'new-recommendation' ? '#2563eb' : 'transparent',
            color: activeTab === 'new-recommendation' ? '#ffffff' : '#cbd5e1',
            fontWeight: activeTab === 'new-recommendation' ? '700' : '500',
            cursor: 'pointer',
            textAlign: 'left',
            fontSize: '0.9rem'
          }}
        >
          <span>📝</span> New Specification Analysis
        </button>

        <button
          onClick={() => setActiveTab('standards')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            width: '100%',
            padding: '12px 14px',
            borderRadius: '8px',
            border: 'none',
            background: activeTab === 'standards' ? '#2563eb' : 'transparent',
            color: activeTab === 'standards' ? '#ffffff' : '#cbd5e1',
            fontWeight: activeTab === 'standards' ? '700' : '500',
            cursor: 'pointer',
            textAlign: 'left',
            fontSize: '0.9rem'
          }}
        >
          <span>📚</span> BIS Standards Catalog
        </button>

        <button
          onClick={() => setActiveTab('history')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            width: '100%',
            padding: '12px 14px',
            borderRadius: '8px',
            border: 'none',
            background: activeTab === 'history' ? '#2563eb' : 'transparent',
            color: activeTab === 'history' ? '#ffffff' : '#cbd5e1',
            fontWeight: activeTab === 'history' ? '700' : '500',
            cursor: 'pointer',
            textAlign: 'left',
            fontSize: '0.9rem'
          }}
        >
          <span>📜</span> Analysis History
        </button>

        <button
          onClick={() => setActiveTab('analytics')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            width: '100%',
            padding: '12px 14px',
            borderRadius: '8px',
            border: 'none',
            background: activeTab === 'analytics' ? '#2563eb' : 'transparent',
            color: activeTab === 'analytics' ? '#ffffff' : '#cbd5e1',
            fontWeight: activeTab === 'analytics' ? '700' : '500',
            cursor: 'pointer',
            textAlign: 'left',
            fontSize: '0.9rem'
          }}
        >
          <span>📈</span> Procurement Analytics
        </button>
      </nav>

      {/* User Profile & Sign Out */}
      {user && (
        <div style={{ borderTop: '1px solid #334155', paddingTop: '16px', marginTop: 'auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: '#3b82f6', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: '700', fontSize: '0.85rem' }}>
                {getInitial()}
              </div>
              <div style={{ overflow: 'hidden' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: '600', color: '#ffffff', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                  {user.full_name}
                </div>
                <div style={{ fontSize: '0.72rem', color: '#94a3b8', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                  {user.email}
                </div>
              </div>
            </div>
          </div>
          <button
            onClick={onLogout}
            style={{ width: '100%', background: '#1e293b', color: '#f8fafc', border: '1px solid #334155', padding: '8px', borderRadius: '6px', fontSize: '0.8rem', cursor: 'pointer', marginTop: '6px' }}
          >
            Sign Out
          </button>
        </div>
      )}
    </aside>
  );
}