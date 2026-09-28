import React, { useCallback, useEffect, useMemo, useState } from 'react';
import * as api from '../services/api';
import { EmptyState, ErrorState, LoadingState, StatTile } from '../components/UiStates';
import RequestsTable from '../components/RequestsTable';
import './StandardsUI.css';

/*
 * History & Analytics — the user's analysis history plus usage analytics
 * from GET /api/analytics/summary. `monthly_usage` from that endpoint is
 * derived from the total (not real per-month history), so it is not shown.
 */
export default function HistoryPage({ onViewReport }) {
  const [requests, setRequests] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  const [pendingDelete, setPendingDelete] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [deleteError, setDeleteError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const [reqRes, sumRes] = await Promise.allSettled([
      api.getUserProcurementRequests(),
      api.getProcurementAnalyticsSummary(),
    ]);
    if (reqRes.status === 'fulfilled') setRequests(reqRes.value?.requests || []);
    else setError(reqRes.reason);
    setSummary(sumRes.status === 'fulfilled' ? sumRes.value : null);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const confirmDelete = async () => {
    const req = pendingDelete;
    setPendingDelete(null);
    setDeletingId(req.id);
    setDeleteError(null);
    try {
      await api.deleteProcurementRequest(req.id);
      setRequests((prev) => prev.filter((r) => r.id !== req.id));
      api.getProcurementAnalyticsSummary().then(setSummary).catch(() => {});
    } catch (err) {
      setDeleteError(err);
    } finally {
      setDeletingId(null);
    }
  };

  const filtered = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    if (!term) return requests;
    return requests.filter((r) =>
      [r.product_category, r.summary, r.procurement_purpose].some((v) => (v || '').toLowerCase().includes(term)),
    );
  }, [requests, searchTerm]);

  const categories = summary?.top_product_categories || [];
  const topStandards = summary?.commonly_recommended_standards || [];
  const maxCat = Math.max(1, ...categories.map((c) => c.count || 0));

  return (
    <div className="su-page">
      <header className="su-header">
        <div>
          <h1 className="su-title">History &amp; Analytics</h1>
          <p className="su-subtitle">Your past specification analyses and what they recommended.</p>
        </div>
      </header>

      {loading ? (
        <LoadingState label="Loading history and analytics…" rows={5} />
      ) : error ? (
        <ErrorState title="Could not load your analysis history" error={error} onRetry={load} />
      ) : requests.length === 0 ? (
        <EmptyState title="No analyses yet" text="Reports you generate from Analyze Tender will appear here with usage analytics." />
      ) : (
        <>
          <div className="su-stats" style={{ marginBottom: 16 }}>
            <StatTile label="Analyses" value={summary?.total_procurement_analyses ?? requests.length} tone="info" />
            <StatTile label="Standards recommended" value={requests.reduce((n, r) => n + (r.recommended_count || 0), 0)} tone="ok" />
            <StatTile label="Mandatory certifications" value={summary?.mandatory_certifications_flagged} tone="warn" />
            <StatTile label="Distinct categories" value={new Set(requests.map((r) => r.product_category).filter(Boolean)).size} />
          </div>

          {summary && (categories.length > 0 || topStandards.length > 0) && (
            <div className="su-split" style={{ marginBottom: 24 }}>
              <div className="su-card">
                <div className="su-rec-label">Top product categories</div>
                {categories.length ? (
                  <ul className="su-bars">
                    {categories.map((c) => (
                      <li key={c.category}>
                        <div className="su-bars-row">
                          <span>{c.category}</span>
                          <span className="su-mono">{c.count}</span>
                        </div>
                        <div className="su-score-bar"><div style={{ width: `${(c.count / maxCat) * 100}%` }} /></div>
                      </li>
                    ))}
                  </ul>
                ) : <p className="su-muted" style={{ fontSize: '0.84rem' }}>No category data yet.</p>}
              </div>
              <div className="su-card">
                <div className="su-rec-label">Most recommended standards</div>
                {topStandards.length ? (
                  <table className="su-table" style={{ fontSize: '0.82rem' }}>
                    <tbody>
                      {topStandards.map((s) => (
                        <tr key={s.standard_number}>
                          <td className="su-code" style={{ whiteSpace: 'nowrap', paddingLeft: 0 }}>{s.standard_number}</td>
                          <td>{s.title}</td>
                          <td className="su-num">{s.count}×</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : <p className="su-muted" style={{ fontSize: '0.84rem' }}>No recommendations yet.</p>}
              </div>
            </div>
          )}

          <section className="su-section">
            <div className="su-toolbar">
              <input
                type="search"
                className="su-input su-input--search"
                placeholder="Filter by category, purpose or keyword"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                aria-label="Filter history"
              />
              <span className="su-section-meta">
                {filtered.length} of {requests.length} analyses
              </span>
            </div>

            {pendingDelete && (
              <div className="su-confirm" style={{ marginBottom: 12 }}>
                Delete the analysis “{(pendingDelete.summary || pendingDelete.product_category || pendingDelete.id).slice(0, 80)}”? This cannot be undone.
                <div className="su-control-row">
                  <button type="button" className="su-btn su-btn--danger" onClick={confirmDelete}>Delete</button>
                  <button type="button" className="su-btn su-btn--secondary" onClick={() => setPendingDelete(null)}>Cancel</button>
                </div>
              </div>
            )}
            {deleteError && (
              <div className="su-notice su-notice--danger" style={{ marginBottom: 12 }}>
                <strong>Delete failed</strong>{deleteError.message}
              </div>
            )}

            {filtered.length === 0 ? (
              <EmptyState
                title="No analyses match this filter"
                action={<button type="button" className="su-btn su-btn--secondary" onClick={() => setSearchTerm('')}>Clear filter</button>}
              />
            ) : (
              <RequestsTable
                requests={filtered}
                onOpen={onViewReport}
                onDelete={setPendingDelete}
                deletingId={deletingId}
              />
            )}
          </section>
        </>
      )}
    </div>
  );
}
