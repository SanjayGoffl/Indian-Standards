import React, { useCallback, useEffect, useState } from 'react';
import * as api from '../services/api';
import { EmptyState, ErrorState, LoadingState, StatTile } from '../components/UiStates';
import RequestsTable from '../components/RequestsTable';
import './StandardsUI.css';

const RECENT_LIMIT = 8;

export default function DashboardPage({ onNavigate, user }) {
  const [summary, setSummary] = useState(null);
  const [requests, setRequests] = useState([]);
  const [catalogTotal, setCatalogTotal] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    // History is the main content, so its failure is surfaced; metrics degrade to "—".
    const [sumRes, reqRes, catRes] = await Promise.allSettled([
      api.getProcurementAnalyticsSummary(),
      api.getUserProcurementRequests(),
      api.getIndianStandards(),
    ]);
    setSummary(sumRes.status === 'fulfilled' ? sumRes.value : null);
    if (reqRes.status === 'fulfilled') setRequests(reqRes.value?.requests || []);
    else setError(reqRes.reason);
    setCatalogTotal(catRes.status === 'fulfilled' ? catRes.value?.total ?? null : null);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const standardsRecommended = requests.reduce((n, r) => n + (r.recommended_count || 0), 0);
  const firstName = (user?.full_name || '').split(' ')[0];

  return (
    <div className="su-page">
      <header className="su-header" style={{ alignItems: 'center' }}>
        <div>
          <h1 className="su-title">{firstName ? `Welcome, ${firstName}` : 'Dashboard'}</h1>
          <p className="su-subtitle">
            Turn tender specifications into applicable Indian Standards, certification needs and verification gaps.
          </p>
        </div>
        <button type="button" className="su-btn su-btn--primary" onClick={() => onNavigate('new-recommendation')}>
          + Analyze tender
        </button>
      </header>

      <div className="su-stats" style={{ marginBottom: 22 }}>
        <StatTile label="Analyses run" value={loading ? null : (summary?.total_procurement_analyses ?? requests.length)} tone="info" />
        <StatTile label="Standards recommended" value={loading ? null : standardsRecommended} hint="Across all your analyses" tone="ok" />
        <StatTile label="Mandatory certifications" value={loading ? null : summary?.mandatory_certifications_flagged} hint="Flagged in recommendations" tone="warn" />
        <StatTile label="Standards in catalogue" value={loading ? null : catalogTotal} hint="Indian Standards in the knowledge base" />
      </div>

      <section className="su-section">
        <div className="su-section-head">
          <h2 className="su-section-title">Recent analyses</h2>
          {requests.length > RECENT_LIMIT && (
            <button type="button" className="su-btn su-btn--ghost" onClick={() => onNavigate('history')}>
              View all {requests.length} →
            </button>
          )}
        </div>

        {loading ? (
          <LoadingState label="Loading your analyses…" rows={4} />
        ) : error ? (
          <ErrorState title="Could not load your analyses" error={error} onRetry={load} />
        ) : requests.length === 0 ? (
          <EmptyState
            title="No analyses yet"
            text="Paste a tender specification or upload an RFP document to get applicable Indian Standards."
            action={<button type="button" className="su-btn su-btn--primary" onClick={() => onNavigate('new-recommendation')}>Analyze your first tender</button>}
          />
        ) : (
          <RequestsTable requests={requests.slice(0, RECENT_LIMIT)} onOpen={(id) => onNavigate('results', id)} />
        )}
      </section>
    </div>
  );
}
