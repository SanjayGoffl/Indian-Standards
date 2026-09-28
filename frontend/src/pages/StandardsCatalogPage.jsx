import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import * as api from '../services/api';
import { Badge, EmptyState, ErrorState, LoadingState, VerificationNotice } from '../components/UiStates';
import './StandardsUI.css';

const PAGE_SIZE = 50;
const SEARCH_DEBOUNCE_MS = 300;

const uniqueSorted = (items, key) =>
  [...new Set(items.map((i) => i[key]).filter(Boolean))].sort((a, b) => a.localeCompare(b));

export default function StandardsCatalogPage({ user, onNavigate = () => {} }) {
  const isAdmin = (user?.role || '').toLowerCase() === 'admin';

  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [sector, setSector] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const [standards, setStandards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [visible, setVisible] = useState(PAGE_SIZE);

  // Facet options are derived from the unfiltered catalogue so they
  // always reflect what is actually stored, not a hardcoded list.
  const [facets, setFacets] = useState({ categories: [], sectors: [], total: null });

  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);

  const requestSeq = useRef(0);

  useEffect(() => {
    const t = setTimeout(() => setSearch(searchInput.trim()), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [searchInput]);

  const fetchStandards = useCallback(async () => {
    const seq = ++requestSeq.current;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getIndianStandards(search, category, sector);
      if (seq !== requestSeq.current) return;
      const list = data?.standards || [];
      setStandards(list);
      setVisible(PAGE_SIZE);
      if (!search && !category && !sector) {
        setFacets({
          categories: uniqueSorted(list, 'category'),
          sectors: uniqueSorted(list, 'sector'),
          total: typeof data?.total === 'number' ? data.total : list.length,
        });
      }
    } catch (err) {
      if (seq === requestSeq.current) setError(err);
    } finally {
      if (seq === requestSeq.current) setLoading(false);
    }
  }, [search, category, sector]);

  useEffect(() => {
    fetchStandards();
  }, [fetchStandards]);

  const statuses = useMemo(() => uniqueSorted(standards, 'status'), [standards]);

  const filtered = useMemo(
    () => (statusFilter ? standards.filter((s) => s.status === statusFilter) : standards),
    [standards, statusFilter],
  );

  const openDetail = async (std) => {
    setSelected(std.standard_number);
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    try {
      const data = await api.getIndianStandardDetail(std.standard_number);
      setDetail(data);
    } catch (err) {
      setDetailError(err);
    } finally {
      setDetailLoading(false);
    }
  };

  const closeDetail = () => {
    setSelected(null);
    setDetail(null);
    setDetailError(null);
  };

  useEffect(() => {
    if (!selected) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') closeDetail(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [selected]);

  const clearFilters = () => {
    setSearchInput('');
    setSearch('');
    setCategory('');
    setSector('');
    setStatusFilter('');
  };

  const activeFilters = [
    search && { key: 'search', label: `“${search}”`, clear: () => { setSearchInput(''); setSearch(''); } },
    category && { key: 'category', label: category, clear: () => setCategory('') },
    sector && { key: 'sector', label: sector, clear: () => setSector('') },
    statusFilter && { key: 'status', label: `Status: ${statusFilter}`, clear: () => setStatusFilter('') },
  ].filter(Boolean);

  const catalogueEmpty = !loading && !error && facets.total === 0 && activeFilters.length === 0;

  return (
    <div className="su-page">
      <header className="su-header">
        <div>
          <h1 className="su-title">Standards</h1>
          <p className="su-subtitle">
            {facets.total !== null
              ? `${facets.total.toLocaleString('en-IN')} Indian Standards in the knowledge base. Select a row for full details.`
              : 'Indian Standards in the knowledge base. Select a row for full details.'}
          </p>
        </div>
      </header>

      <div className="su-toolbar" role="search">
        <input
          type="search"
          className="su-input su-input--search"
          placeholder="IS number, title or scope — e.g. IS 694, cable, cement"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          aria-label="Search standards"
        />
        <select className="su-select" value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Category">
          <option value="">All categories</option>
          {facets.categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select className="su-select" value={sector} onChange={(e) => setSector(e.target.value)} aria-label="Sector">
          <option value="">All sectors</option>
          {facets.sectors.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        {statuses.length > 1 && (
          <select className="su-select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label="Status">
            <option value="">Any status</option>
            {statuses.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        )}
      </div>

      <div className="su-chip-row">
        <span>
          {loading
            ? 'Searching…'
            : `${filtered.length.toLocaleString('en-IN')} result${filtered.length === 1 ? '' : 's'}`}
          {facets.total !== null && !loading && activeFilters.length > 0 && ` of ${facets.total.toLocaleString('en-IN')}`}
        </span>
        {activeFilters.map((f) => (
          <button key={f.key} type="button" className="su-chip" onClick={f.clear} title="Remove filter">
            {f.label}<span>×</span>
          </button>
        ))}
        {activeFilters.length > 1 && (
          <button type="button" className="su-btn su-btn--ghost" onClick={clearFilters}>Clear all</button>
        )}
      </div>

      <div>
          {loading && !standards.length ? (
            <LoadingState label="Loading Indian Standards catalog…" rows={5} />
          ) : error ? (
            <ErrorState title="Could not load the standards catalog" error={error} onRetry={fetchStandards} />
          ) : catalogueEmpty ? (
            <EmptyState
              title="The catalogue is empty"
              text="No standards have been ingested yet."
              action={isAdmin
                ? <button type="button" className="su-btn su-btn--primary" onClick={() => onNavigate('admin-standards')}>Run a sync</button>
                : <span className="su-muted" style={{ fontSize: '0.82rem' }}>Ask an administrator to run a standards sync.</span>}
            />
          ) : filtered.length === 0 ? (
            <EmptyState
              title="No standards match these filters"
              text="Try a shorter IS number (e.g. “694” instead of “IS 694:2010”), a broader keyword, or remove a filter."
              action={<button type="button" className="su-btn su-btn--secondary" onClick={clearFilters}>Clear filters</button>}
            />
          ) : (
            <>
              <div className="su-table-wrap" style={{ opacity: loading ? 0.6 : 1 }}>
                <table className="su-table">
                  <thead>
                    <tr>
                      <th>IS number</th>
                      <th>Title &amp; scope</th>
                      <th className="hide-sm">Category</th>
                      <th className="hide-sm">Revision</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.slice(0, visible).map((std) => (
                      <tr
                        key={std.id || std.standard_number}
                        className={`su-row-clickable${selected === std.standard_number ? ' su-row-selected' : ''}`}
                        onClick={() => openDetail(std)}
                        onKeyDown={(e) => { if (e.key === 'Enter') openDetail(std); }}
                        tabIndex={0}
                      >
                        <td className="su-code" style={{ whiteSpace: 'nowrap' }}>{std.standard_number}</td>
                        <td>
                          <div style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{std.title}</div>
                          {std.scope && <div className="su-truncate-2 su-muted" style={{ fontSize: '0.78rem', marginTop: 3 }}>{std.scope}</div>}
                        </td>
                        <td className="hide-sm">{std.category || '—'}</td>
                        <td className="hide-sm su-mono" style={{ fontSize: '0.78rem' }}>{std.revision || '—'}</td>
                        <td>{std.status ? <Badge>{std.status}</Badge> : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {filtered.length > visible && (
                <div className="su-more">
                  <button type="button" className="su-btn su-btn--secondary" onClick={() => setVisible((v) => v + PAGE_SIZE)}>
                    Show {Math.min(PAGE_SIZE, filtered.length - visible)} more ({(filtered.length - visible).toLocaleString('en-IN')} remaining)
                  </button>
                </div>
              )}
            </>
          )}
      </div>

      {selected && (
        <>
          <div className="su-drawer-backdrop" onClick={closeDetail} aria-hidden="true" />
          <aside className="su-detail" role="dialog" aria-modal="true" aria-label={`Details for ${selected}`}>
            <div className="su-detail-head">
              <div>
                <div className="su-code" style={{ fontSize: '1.15rem' }}>{selected}</div>
              </div>
              <button type="button" className="su-close" onClick={closeDetail} aria-label="Close details">✕</button>
            </div>

            {detailLoading ? (
              <LoadingState label="Loading standard details…" />
            ) : detailError ? (
              <ErrorState
                title="Could not load this standard"
                error={detailError}
                onRetry={() => openDetail({ standard_number: selected })}
              />
            ) : detail ? (
              <StandardDetail detail={detail} />
            ) : null}
          </aside>
        </>
      )}
    </div>
  );
}

const RELATION_GROUPS = [
  ['normative_reference', 'Normative references'],
  ['test_method', 'Test methods'],
];

function groupRelationships(related) {
  const groups = RELATION_GROUPS.map(([type, label]) => ({
    label,
    items: related.filter((r) => r.relationship_type === type),
  }));
  const known = new Set(RELATION_GROUPS.map(([type]) => type));
  groups.push({ label: 'Other related standards', items: related.filter((r) => !known.has(r.relationship_type)) });
  return groups.filter((g) => g.items.length);
}

function StandardDetail({ detail }) {
  const certs = detail.certifications || [];
  const related = detail.related_standards || [];
  const groups = groupRelationships(related);

  return (
    <>
      <h3>{detail.title}</h3>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
        {detail.status && <Badge>{detail.status}</Badge>}
        {detail.category && <Badge tone="info">{detail.category}</Badge>}
        {detail.sector && <Badge tone="neutral">{detail.sector}</Badge>}
      </div>

      <div className="su-detail-section">
        <h5>Scope</h5>
        <p>{detail.scope || 'No scope text is stored for this standard.'}</p>
      </div>

      <div className="su-detail-section">
        <h5>Revision &amp; amendments</h5>
        <dl className="su-kv" style={{ marginBottom: 8 }}>
          <div><dt>Revision</dt><dd className="su-mono">{detail.revision || 'Not recorded'}</dd></div>
          <div><dt>Published</dt><dd className="su-mono">{detail.publication_date || 'Not recorded'}</dd></div>
        </dl>
        <p>{detail.amendment_details || 'No amendment details are stored for this standard.'}</p>
      </div>

      <div className="su-detail-section">
        <h5>Certification ({certs.length})</h5>
        {certs.length ? (
          <ul className="su-list">
            {certs.map((c, i) => (
              <li key={`${c.certification_type}-${i}`}>
                <div className="su-list-top">
                  <strong style={{ color: 'var(--text-primary)' }}>{c.certification_type}</strong>
                  {c.applicability && <Badge>{c.applicability}</Badge>}
                </div>
                {c.verification_status && <div className="su-muted" style={{ fontSize: '0.78rem' }}>{c.verification_status}</div>}
                {c.source_url && (
                  <a className="su-link" href={c.source_url} target="_blank" rel="noopener noreferrer">Source ↗</a>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="su-muted">No certification scheme is linked to this standard in the catalogue.</p>
        )}
      </div>

      <div className="su-detail-section">
        <h5>Relationships ({related.length})</h5>
        {groups.length ? groups.map((g) => (
          <div key={g.label} style={{ marginBottom: 10 }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, margin: '4px 0 6px' }}>{g.label}</div>
            <ul className="su-list">
              {g.items.map((r, i) => (
                <li key={`${r.standard_number}-${i}`}>
                  <div className="su-list-top">
                    <span className="su-code">{r.standard_number}</span>
                    {g.label === 'Other related standards' && r.relationship_type && (
                      <Badge tone="neutral">{r.relationship_type.replace(/_/g, ' ')}</Badge>
                    )}
                  </div>
                  <div>{r.title}</div>
                  {r.description && <div className="su-muted" style={{ fontSize: '0.78rem', marginTop: 3 }}>{r.description}</div>}
                </li>
              ))}
            </ul>
          </div>
        )) : (
          <p className="su-muted">No normative references, test methods or related standards are linked in the catalogue.</p>
        )}
      </div>

      {detail.evidence_text && detail.evidence_text !== detail.scope && (
        <div className="su-detail-section">
          <h5>Source evidence</h5>
          <p style={{ fontStyle: 'italic' }}>{detail.evidence_text}</p>
        </div>
      )}

      <div className="su-detail-section">
        <VerificationNotice>
          Confirm the current revision and status on the official BIS portal before citing this standard in a tender.
          {detail.source_url && (
            <div style={{ marginTop: 6 }}>
              <a className="su-link" href={detail.source_url} target="_blank" rel="noopener noreferrer">Open source record ↗</a>
            </div>
          )}
        </VerificationNotice>
      </div>
    </>
  );
}
