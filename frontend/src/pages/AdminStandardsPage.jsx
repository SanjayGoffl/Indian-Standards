import React, { useCallback, useEffect, useRef, useState } from 'react';
import * as api from '../services/api';
import { Badge, EmptyState, ErrorState, LoadingState, StatTile } from '../components/UiStates';
import './StandardsUI.css';

/*
 * Admin portal for the BIS standards ingestion pipeline.
 *
 * Every number on this page comes from existing endpoints:
 *   GET  /api/standards              -> catalogue record total
 *   GET  /api/standards/ingest-logs  -> ingestion audit runs (latest 50)
 *   POST /api/standards/sync         -> source=mock (sync) | bis_live (background)
 *   POST /api/standards/reindex-failed
 *   POST /api/standards/seed
 */

const LIVE_POLL_MS = 15000;
const LIVE_STORAGE_KEY = 'qn_live_bis_sync';

const SOURCE_LABELS = {
  bis_live_api: 'BIS live catalogue',
  mock_authorized_connector: 'Built-in sample set',
  local_json: 'Local JSON file',
  local_csv: 'Local CSV file',
};

const sourceLabel = (s) => SOURCE_LABELS[s] || s || 'Unknown source';

const fmtDate = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
};

const fmtDuration = (start, end) => {
  if (!start || !end) return '—';
  const s = Math.max(0, (new Date(end) - new Date(start)) / 1000);
  if (Number.isNaN(s)) return '—';
  if (s < 60) return `${s.toFixed(1)}s`;
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
};

const indexedCount = (log) => (log?.embeddings_created ?? 0) + (log?.embeddings_updated ?? 0);

function readLiveRun() {
  try {
    const raw = sessionStorage.getItem(LIVE_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function writeLiveRun(value) {
  try {
    if (value) sessionStorage.setItem(LIVE_STORAGE_KEY, JSON.stringify(value));
    else sessionStorage.removeItem(LIVE_STORAGE_KEY);
  } catch {
    // Storage unavailable: polling still works for this page visit.
  }
}

export default function AdminStandardsPage({ user, onNavigate = () => {} }) {
  const isAdmin = (user?.role || '').toLowerCase() === 'admin';

  const [logs, setLogs] = useState([]);
  const [logsLoading, setLogsLoading] = useState(true);
  const [logsError, setLogsError] = useState(null);

  const [catalogTotal, setCatalogTotal] = useState(null);
  const [catalogError, setCatalogError] = useState(null);

  const [busy, setBusy] = useState(null); // 'mock' | 'live' | 'reindex' | 'seed'
  const [actionResult, setActionResult] = useState(null);
  const [actionError, setActionError] = useState(null);

  const [maxNumber, setMaxNumber] = useState(20000);
  const [confirmLive, setConfirmLive] = useState(false);
  const [liveRun, setLiveRun] = useState(() => readLiveRun());

  const [expandedRun, setExpandedRun] = useState(null);
  const pollRef = useRef(null);

  const loadLogs = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLogsLoading(true);
    try {
      const data = await api.getStandardsIngestLogs();
      const list = Array.isArray(data?.logs) ? data.logs : [];
      setLogs(list);
      setLogsError(null);
      return list;
    } catch (err) {
      setLogsError(err);
      return null;
    } finally {
      if (!silent) setLogsLoading(false);
    }
  }, []);

  const loadCatalogTotal = useCallback(async () => {
    try {
      const data = await api.getIndianStandards();
      setCatalogTotal(typeof data?.total === 'number' ? data.total : (data?.standards || []).length);
      setCatalogError(null);
    } catch (err) {
      setCatalogError(err);
    }
  }, []);

  const refreshAll = useCallback(() => {
    loadLogs();
    loadCatalogTotal();
  }, [loadLogs, loadCatalogTotal]);

  useEffect(() => {
    if (isAdmin) refreshAll();
  }, [isAdmin, refreshAll]);

  // Background live sweep: the backend only writes an audit log when the
  // run finishes, so a new BIS-live ingestion_id means the sweep completed.
  useEffect(() => {
    if (!liveRun || !isAdmin) return undefined;

    const check = async () => {
      const list = await loadLogs({ silent: true });
      if (!list) return;
      const finished = list.find(
        (l) => l.source_name === 'bis_live_api' && !liveRun.knownIds.includes(l.ingestion_id),
      );
      if (finished) {
        setLiveRun(null);
        writeLiveRun(null);
        setActionResult({ kind: 'live-finished', data: finished, at: new Date().toISOString() });
        loadCatalogTotal();
      }
    };

    check();
    pollRef.current = setInterval(check, LIVE_POLL_MS);
    return () => clearInterval(pollRef.current);
  }, [liveRun, isAdmin, loadLogs, loadCatalogTotal]);

  const runAction = async (kind, fn) => {
    setBusy(kind);
    setActionError(null);
    setActionResult(null);
    try {
      const data = await fn();
      setActionResult({ kind, data, at: new Date().toISOString() });
      return data;
    } catch (err) {
      setActionError({ kind, err });
      return null;
    } finally {
      setBusy(null);
    }
  };

  const handleMockSync = async () => {
    const data = await runAction('mock', () => api.syncStandards('mock'));
    if (data) refreshAll();
  };

  const handleReindex = async () => {
    const data = await runAction('reindex', () => api.reindexFailedStandards());
    if (data) refreshAll();
  };

  const handleSeed = async () => {
    const data = await runAction('seed', () => api.seedStandards());
    if (data) refreshAll();
  };

  const handleLiveSync = async () => {
    setConfirmLive(false);
    const n = Math.min(30000, Math.max(1, Number(maxNumber) || 20000));
    // Snapshot existing run IDs so only a run started after this click counts as "finished".
    const fresh = await loadLogs({ silent: true });
    const knownIds = (fresh || logs).map((l) => l.ingestion_id);
    const data = await runAction('live', () => api.syncStandards('bis_live', n));
    if (data) {
      const run = { startedAt: new Date().toISOString(), maxNumber: n, knownIds };
      setLiveRun(run);
      writeLiveRun(run);
    }
  };

  const stopWatchingLive = () => {
    setLiveRun(null);
    writeLiveRun(null);
  };

  if (!isAdmin) {
    return (
      <div className="su-page">
        <ErrorState
          title="Admin access required"
          error="Standards ingestion and sync controls are available to Admin accounts only."
          action={
            <button type="button" className="su-btn su-btn--secondary" onClick={() => onNavigate('standards')}>
              Open the standards catalog
            </button>
          }
        />
      </div>
    );
  }

  const latest = logs[0] || null;
  const anyBusy = Boolean(busy);

  return (
    <div className="su-page">
      <header className="su-header">
        <div>
          <div className="su-eyebrow">Admin · Knowledge base</div>
          <h1 className="su-title">Standards ingestion &amp; sync</h1>
          <p className="su-subtitle">
            Pull BIS standards into the catalogue, track what each ingestion run discovered, stored and
            indexed, and retry vector indexing for records that failed.
          </p>
        </div>
        <div className="su-header-actions">
          <button type="button" className="su-btn su-btn--secondary" onClick={refreshAll} disabled={logsLoading}>
            {logsLoading ? <span className="su-spinner" /> : null}
            Refresh
          </button>
          <button type="button" className="su-btn su-btn--secondary" onClick={() => onNavigate('standards')}>
            View catalog
          </button>
        </div>
      </header>

      {/* ---------- Catalogue counts ---------- */}
      <section className="su-section">
        <div className="su-section-head">
          <h2 className="su-section-title">Catalogue status</h2>
          <span className="su-section-meta">
            {latest
              ? <>Latest run <span className="su-mono">{latest.ingestion_id}</span> · {sourceLabel(latest.source_name)} · {fmtDate(latest.end_time || latest.start_time)}</>
              : 'No ingestion runs recorded yet'}
          </span>
        </div>

        {logsLoading && !logs.length ? (
          <LoadingState label="Loading ingestion audit log…" rows={2} />
        ) : logsError && !logs.length ? (
          <ErrorState title="Could not load ingestion logs" error={logsError} onRetry={() => loadLogs()} />
        ) : (
          <div className="su-stats">
            <StatTile
              label="Catalogue records"
              value={catalogError ? '—' : catalogTotal}
              hint={catalogError ? 'Catalogue count unavailable' : 'Standards stored in the database'}
              tone="info"
            />
            <StatTile label="Discovered" value={latest?.total_records} hint="Records returned by the source in the latest run" />
            <StatTile label="Ingested (new)" value={latest?.new_records} hint="New standards added" tone="ok" />
            <StatTile label="Updated" value={latest?.updated_records} hint={latest ? `${(latest.unchanged_records ?? 0).toLocaleString('en-IN')} unchanged (hash match)` : undefined} tone="info" />
            <StatTile label="Indexed" value={latest ? indexedCount(latest) : null} hint={latest ? `${latest.embeddings_created ?? 0} created · ${latest.embeddings_updated ?? 0} updated embeddings` : undefined} tone="ok" />
            <StatTile label="Failed" value={latest?.failed_records} hint="Records rejected by validation" tone={latest?.failed_records ? 'danger' : 'neutral'} />
          </div>
        )}
        {latest && (latest.new_records + latest.updated_records) > indexedCount(latest) && (
          <div className="su-notice su-notice--warn" style={{ marginTop: 12 }}>
            <strong>Some records were stored but not indexed</strong>
            {(latest.new_records + latest.updated_records - indexedCount(latest)).toLocaleString('en-IN')} new or updated
            record(s) in the latest run have no vector embedding yet. Use “Re-index failed &amp; pending” below.
          </div>
        )}
      </section>

      {/* ---------- Controls ---------- */}
      <section className="su-section">
        <div className="su-section-head">
          <h2 className="su-section-title">Sync &amp; re-index controls</h2>
          <span className="su-section-meta">Admin role enforced by the backend</span>
        </div>

        <div className="su-controls">
          <div className="su-card su-control">
            <h4>Live BIS catalogue sweep</h4>
            <p>
              Sweeps the BIS public “Know Your Standards” search for IS numbers 1…N. Runs in the background and
              can take several minutes; this page watches the audit log for completion.
            </p>
            {liveRun ? (
              <div>
                <div className="su-running"><span className="su-spinner" /> Sweep running (IS 1…{liveRun.maxNumber})</div>
                <div className="su-muted" style={{ fontSize: '0.75rem', marginTop: 6 }}>
                  Started {fmtDate(liveRun.startedAt)} · checking every {LIVE_POLL_MS / 1000}s
                </div>
                <button type="button" className="su-btn su-btn--ghost" onClick={stopWatchingLive}>
                  Stop watching
                </button>
              </div>
            ) : confirmLive ? (
              <div className="su-confirm">
                Start a live sweep of IS numbers 1…{Number(maxNumber).toLocaleString('en-IN')}? The backend will query BIS for each number.
                <div className="su-control-row">
                  <button type="button" className="su-btn su-btn--primary" onClick={handleLiveSync} disabled={anyBusy}>
                    Start sweep
                  </button>
                  <button type="button" className="su-btn su-btn--secondary" onClick={() => setConfirmLive(false)}>
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="su-control-row">
                <label htmlFor="max-number">Up to IS</label>
                <input
                  id="max-number"
                  className="su-input"
                  type="number"
                  min={1}
                  max={30000}
                  value={maxNumber}
                  onChange={(e) => setMaxNumber(e.target.value)}
                />
                <button type="button" className="su-btn su-btn--primary" onClick={() => setConfirmLive(true)} disabled={anyBusy}>
                  {busy === 'live' && <span className="su-spinner" />}
                  Run live sync
                </button>
              </div>
            )}
          </div>

          <div className="su-card su-control">
            <h4>Sync built-in sample set</h4>
            <p>
              Re-runs the ingestion pipeline on the bundled sample catalogue. Runs immediately; unchanged records are
              skipped by content-hash change detection.
            </p>
            <div className="su-control-row">
              <button type="button" className="su-btn su-btn--secondary" onClick={handleMockSync} disabled={anyBusy}>
                {busy === 'mock' && <span className="su-spinner" />}
                Sync sample set
              </button>
              <button type="button" className="su-btn su-btn--ghost" onClick={handleSeed} disabled={anyBusy}>
                {busy === 'seed' && <span className="su-spinner" />}
                Seed defaults
              </button>
            </div>
          </div>

          <div className="su-card su-control">
            <h4>Re-index failed &amp; pending</h4>
            <p>
              Retries vector embedding for every standard flagged for re-index or not yet marked as indexed in the
              vector store.
            </p>
            <div className="su-control-row">
              <button type="button" className="su-btn su-btn--secondary" onClick={handleReindex} disabled={anyBusy}>
                {busy === 'reindex' && <span className="su-spinner" />}
                Re-index failed &amp; pending
              </button>
            </div>
          </div>
        </div>

        {actionError && (
          <div style={{ marginTop: 14 }}>
            <ErrorState title="The operation did not complete" error={actionError.err} />
          </div>
        )}
        {actionResult && <ActionResult result={actionResult} />}
      </section>

      {/* ---------- Run history ---------- */}
      <section className="su-section">
        <div className="su-section-head">
          <h2 className="su-section-title">Ingestion run history</h2>
          <span className="su-section-meta">{logs.length ? `${logs.length} most recent run(s)` : ''}</span>
        </div>

        {logsLoading && !logs.length ? (
          <LoadingState label="Loading run history…" />
        ) : logsError && !logs.length ? null : logs.length === 0 ? (
          <EmptyState
            title="No ingestion runs yet"
            text="Run a sync above to populate the catalogue. Each run is recorded here with its discovered, ingested, updated, failed and indexed counts."
          />
        ) : (
          <div className="su-table-wrap">
            <table className="su-table">
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Source</th>
                  <th>Started</th>
                  <th className="hide-sm">Duration</th>
                  <th className="su-num">Discovered</th>
                  <th className="su-num">New</th>
                  <th className="su-num">Updated</th>
                  <th className="su-num hide-sm">Unchanged</th>
                  <th className="su-num">Failed</th>
                  <th className="su-num">Indexed</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => {
                  const open = expandedRun === log.ingestion_id;
                  const hasErrors = Boolean(log.error_summary);
                  return (
                    <React.Fragment key={log.ingestion_id || log.id}>
                      <tr
                        className={hasErrors ? 'su-row-clickable' : undefined}
                        onClick={hasErrors ? () => setExpandedRun(open ? null : log.ingestion_id) : undefined}
                        title={hasErrors ? 'Show error summary' : undefined}
                      >
                        <td className="su-mono">{log.ingestion_id}</td>
                        <td>{sourceLabel(log.source_name)}</td>
                        <td style={{ whiteSpace: 'nowrap' }}>{fmtDate(log.start_time)}</td>
                        <td className="hide-sm su-mono">{fmtDuration(log.start_time, log.end_time)}</td>
                        <td className="su-num">{log.total_records ?? '—'}</td>
                        <td className="su-num">{log.new_records ?? '—'}</td>
                        <td className="su-num">{log.updated_records ?? '—'}</td>
                        <td className="su-num hide-sm">{log.unchanged_records ?? '—'}</td>
                        <td className="su-num">{log.failed_records ?? '—'}</td>
                        <td className="su-num">{indexedCount(log)}</td>
                        <td>
                          <Badge>{(log.status || 'unknown').replace(/_/g, ' ')}</Badge>
                          {hasErrors && <span className="su-muted" style={{ fontSize: '0.7rem', marginLeft: 6 }}>{open ? '▲' : '▼'}</span>}
                        </td>
                      </tr>
                      {open && (
                        <tr>
                          <td colSpan={11}>
                            <div className="su-pre">{log.error_summary}</div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function ActionResult({ result }) {
  const { kind, data, at } = result;

  if (kind === 'live') {
    return (
      <div className="su-notice su-notice--info" style={{ marginTop: 14 }}>
        <strong>Live sync started</strong>
        {data?.message || 'The sweep is running in the background.'}
      </div>
    );
  }

  if (kind === 'reindex') {
    const d = data?.details || {};
    return (
      <div className={`su-notice ${d.failed_count ? 'su-notice--danger' : 'su-notice--ok'}`} style={{ marginTop: 14 }}>
        <strong>{data?.message || 'Re-index finished'} · {fmtDate(at)}</strong>
        {d.message
          ? d.message
          : <>Re-indexed <b>{d.reindexed_count ?? 0}</b> of {d.total_attempted ?? '—'} · failed <b>{d.failed_count ?? 0}</b></>}
        {d.error && <div className="su-pre" style={{ marginTop: 8 }}>{d.error}</div>}
      </div>
    );
  }

  // mock sync returns `summary`; seed returns `details`; finished live run is an audit log entry.
  const s = kind === 'live-finished' ? data : (data?.summary || data?.details || {});
  const title = kind === 'live-finished'
    ? `Live BIS sweep finished (${s.ingestion_id})`
    : `${data?.message || 'Sync finished'} · ${fmtDate(at)}`;
  const failed = s.failed_records ?? 0;

  return (
    <div className={`su-notice ${failed ? 'su-notice--warn' : 'su-notice--ok'}`} style={{ marginTop: 14 }}>
      <strong>{title}</strong>
      {'total_records' in s ? (
        <>
          Discovered {s.total_records} · new {s.new_records ?? 0} · updated {s.updated_records ?? 0} · unchanged{' '}
          {s.unchanged_records ?? 0} · failed {failed} · indexed {indexedCount(s)}
          {typeof s.total_in_db === 'number' && <> · {s.total_in_db} in catalogue</>}
        </>
      ) : (
        <span className="su-muted">The backend did not return run counts; see the run history below.</span>
      )}
    </div>
  );
}
