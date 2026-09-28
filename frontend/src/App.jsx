import React, { useEffect, useState } from 'react';
import Sidebar from './components/Sidebar';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import NewRecommendationPage from './pages/NewRecommendationPage';
import RecommendationResultsPage from './pages/RecommendationResultsPage';
import StandardsCatalogPage from './pages/StandardsCatalogPage';
import HistoryPage from './pages/HistoryPage';
import LandingPage from './pages/LandingPage';
import AdminStandardsPage from './pages/AdminStandardsPage';
import { useAuth } from './context/Authcontext';
import './App.css';

function App() {
  const { user, isLoggedIn, loading: authLoading, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedRequestId, setSelectedRequestId] = useState(null);
  // Logged-out flow: landing page first, then the sign-in / sign-up form.
  const [authView, setAuthView] = useState(null); // null = landing, 'login' | 'signup'

  useEffect(() => {
    if (!authLoading && isLoggedIn && user) {
      setActiveTab('dashboard');
    }
  }, [authLoading, isLoggedIn, user]);

  if (authLoading) {
    return (
      <div className="app-auth-loading" style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-surface-opaque)', color: 'var(--text-primary)' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: '600', marginBottom: '8px' }}>Indian Standards Procurement Engine</div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Verifying authenticated session…</div>
        </div>
      </div>
    );
  }

  if (!isLoggedIn || !user) {
    if (!authView) {
      return <LandingPage onSignIn={() => setAuthView('login')} onSignUp={() => setAuthView('signup')} />;
    }
    return <AuthPage key={authView} initialTab={authView} onBack={() => setAuthView(null)} />;
  }

  const handleNavigateToResult = (reqId) => {
    setSelectedRequestId(reqId);
    setActiveTab('results');
  };

  const renderActivePage = () => {
    switch (activeTab) {
      case 'dashboard':
        return (
          <DashboardPage
            user={user}
            onNavigate={(tab, reqId) => {
              if (reqId) setSelectedRequestId(reqId);
              setActiveTab(tab);
            }}
          />
        );

      case 'new-recommendation':
        return (
          <NewRecommendationPage
            onAnalysisComplete={(res) => {
              const reqId = typeof res === 'string' ? res : res.request_id;
              if (reqId) {
                setSelectedRequestId(reqId);
                setActiveTab('results');
              } else {
                setActiveTab('history');
              }
            }}
          />
        );

      case 'results':
        return (
          <RecommendationResultsPage
            requestId={selectedRequestId}
            onBack={() => setActiveTab('history')}
          />
        );

      case 'standards':
        return <StandardsCatalogPage user={user} onNavigate={setActiveTab} />;

      case 'admin-standards':
        return <AdminStandardsPage user={user} onNavigate={setActiveTab} />;

      case 'history':
      case 'analytics':
        return (
          <HistoryPage
            onViewReport={handleNavigateToResult}
          />
        );

      default:
        return (
          <DashboardPage
            user={user}
            onNavigate={(tab, reqId) => {
              if (reqId) setSelectedRequestId(reqId);
              setActiveTab(tab);
            }}
          />
        );
    }
  };

  return (
    <div className="main-app">
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        user={user}
        onLogout={logout}
      />

      <main className="main-content" style={{ flex: 1, overflowY: 'auto' }}>
        {renderActivePage()}
      </main>
    </div>
  );
}

export default App;
