import React, { useEffect, useState } from 'react';
import Sidebar from './components/Sidebar';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import NewRecommendationPage from './pages/NewRecommendationPage';
import RecommendationResultsPage from './pages/RecommendationResultsPage';
import StandardsCatalogPage from './pages/StandardsCatalogPage';
import HistoryPage from './pages/HistoryPage';
import AnalyticsPage from './pages/AnalyticsPage';
import { useAuth } from './context/Authcontext';
import './App.css';

function App() {
  const { user, isLoggedIn, loading: authLoading, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedRequestId, setSelectedRequestId] = useState(null);

  useEffect(() => {
    if (!authLoading && isLoggedIn && user) {
      setActiveTab('dashboard');
    }
  }, [authLoading, isLoggedIn, user]);

  if (authLoading) {
    return (
      <div className="app-auth-loading" style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', background: '#0f172a', color: '#ffffff' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '8px' }}>Indian Standards Procurement Engine</div>
          <div style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Verifying authenticated session...</div>
        </div>
      </div>
    );
  }

  if (!isLoggedIn || !user) {
    return <AuthPage />;
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
        return <StandardsCatalogPage />;

      case 'history':
        return (
          <HistoryPage
            onViewReport={handleNavigateToResult}
          />
        );

      case 'analytics':
        return <AnalyticsPage />;

      default:
        return (
          <DashboardPage
            onNavigate={(tab, reqId) => {
              if (reqId) setSelectedRequestId(reqId);
              setActiveTab(tab);
            }}
          />
        );
    }
  };

  return (
    <div className="main-app" style={{ display: 'flex', minHeight: '100vh', background: '#f8fafc' }}>
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
