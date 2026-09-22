import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { downloadCsv, getKnowledgeGaps } from '../services/analytics';
import './Milestone4.css';

const FILTERS = [
  { id: 'all', label: 'All Gaps' },
  { id: 'Low confidence', label: 'Low Confidence' },
  { id: 'Unanswered', label: 'Unanswered' },
];

function confidencePercent(value) {
  const n = Number(value);
  return Number.isFinite(n) ? Math.max(0, Math.min(100, n * 100)) : 0;
}

function reasonForGap(gap) {
  const reason = String(gap?.reason || '').trim();
  if (reason) return reason;
  if (Number(gap?.confidence_score) < 0.5) return 'Low confidence';
  return 'Detected gap';
}

function filterCategoryForGap(gap) {
  const reason = reasonForGap(gap).toLowerCase();

  if (reason.includes('unanswered')) {
    return 'Unanswered';
  }

  if (
    reason.includes('no information retrieved') ||
    reason.includes('no relevant chunk')
  ) {
    return 'No relevant chunks';
  }

  if (
    reason.includes('low retrieval confidence') ||
    reason.includes('low confidence')
  ) {
    return 'Low confidence';
  }

  return reasonForGap(gap);
}

export default function KnowledgeGapPage({ onIngest }) {
  const [data, setData] = useState(null);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getKnowledgeGaps());
    } catch (err) {
      setError(err?.message || 'Unable to load knowledge gap data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const gaps = data?.gaps || [];
  const statistics = data?.statistics || {};
  const top = data?.top || [];

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return gaps.filter((gap) => {
      const reason = reasonForGap(gap);
      const category = filterCategoryForGap(gap);
      if (filter !== 'all' && category.toLowerCase() !== filter.toLowerCase()) return false;
      if (q && !`${gap.query_text || ''} ${gap.query_type || ''} ${reason}`.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [gaps, filter, search]);

  const handleExport = () => {
    downloadCsv('querynest-knowledge-gaps.csv', [
      ['query', 'query_type', 'reason', 'confidence_pct', 'occurrences', 'created_at'],
      ...filtered.map((gap) => [
        gap.query_text,
        gap.query_type ?? '',
        reasonForGap(gap),
        confidencePercent(gap.confidence_score).toFixed(1),
        gap.occurrence_count ?? 1,
        gap.created_at ?? '',
      ]),
    ]);
  };

  if (loading) {
    return <div className="m4-page"><div className="glass-panel m4-state"><h3>Loading knowledge gaps…</h3><p>Fetching backend-detected gaps.</p></div></div>;
  }

  if (error) {
    return <div className="m4-page"><div className="glass-panel m4-state"><h3>Unable to load knowledge gaps.</h3><p>{error}</p><button className="btn btn-primary" onClick={load}>Retry</button></div></div>;
  }

  const total = Number(statistics.total_gaps ?? gaps.length ?? 0);
  const detected = Number(statistics.total_gaps ?? gaps.length ?? 0);
  const topRepeated = Number(
    top[0]?.occurrence_count ??
      (gaps.length > 0
        ? Math.max(...gaps.map((g) => Number(g.occurrence_count || 1)))
        : 0)
  );

  return (
    <div className="m4-page">
      <div className="m4-header-row">
        <div>
          <h1 className="m4-title">Knowledge Gap Visualization</h1>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button className="btn btn-secondary" onClick={load}>⟳ Rescan</button>
          <button className="btn btn-primary" onClick={onIngest}>📥 Ingest Documents</button>
          <button className="btn btn-secondary" onClick={handleExport}>⬇ Export CSV</button>
        </div>
      </div>

      <div className="m4-cards m4-cards-3">
        <div className="glass-card m4-card">
          <div className="m4-card-label">TOTAL GAPS</div>
          <div className="m4-card-value">{total}</div>
          <div className="m4-card-sub">Backend detected</div>
        </div>
        <div className="glass-card m4-card">
          <div className="m4-card-label">DETECTED</div>
          <div className="m4-card-value">{detected}</div>
          <div className="m4-card-sub">Active gap queries</div>
        </div>
        <div className="glass-card m4-card">
          <div className="m4-card-label">TOP REPEATED</div>
          <div className="m4-card-value">{topRepeated}</div>
          <div className="m4-card-sub">Occurrences</div>
        </div>
      </div>

      <div className="glass-panel m4-panel">
        <div className="m4-panel-head">
          <div><h3 className="m4-panel-title">Detected Knowledge Gaps</h3></div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
          {FILTERS.map((item) => (
            <button key={item.id} className={`m4-pill ${filter === item.id ? 'active' : ''}`} onClick={() => setFilter(item.id)}>
              {item.label}
            </button>
          ))}
          <input className="m4-search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search problematic query…" />
        </div>

        {filtered.length === 0 ? (
          <div className="m4-state" style={{ padding: 30 }}>
            <h3>No matching knowledge gaps</h3>
            <p>{gaps.length === 0 ? 'No backend-detected gaps are available yet.' : 'Try a different filter or search term.'}</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="m4-table">
              <thead><tr><th>Query</th><th>Type</th><th>Reason</th><th>Confidence</th><th>Occurrences</th><th>Detected</th></tr></thead>
              <tbody>
                {filtered.map((gap) => {
                  const pct = confidencePercent(gap.confidence_score);
                  return (
                    <tr key={gap.id}>
                      <td style={{ minWidth: 280, color: 'var(--text-secondary)' }}>{gap.query_text}</td>
                      <td>{gap.query_type || '—'}</td>
                      <td>{reasonForGap(gap)}</td>
                      <td><strong>{pct.toFixed(1)}%</strong></td>
                      <td>{gap.occurrence_count ?? 1}</td>
                      <td style={{ whiteSpace: 'nowrap', color: 'var(--text-muted)' }}>{gap.created_at ? new Date(gap.created_at).toLocaleString() : '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
