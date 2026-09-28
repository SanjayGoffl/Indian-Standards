import React, { useCallback, useEffect, useState } from 'react';
import * as api from '../services/api';
import { Badge, EmptyState, ErrorState, LoadingState, StatTile } from '../components/UiStates';
import './StandardsUI.css';

/*
 * Report layout follows the review flow:
 * requirements → recommended IS → reason → related / normative standards
 * → version / status → certification → tender gaps.
 * Everything rendered comes from GET /api/procurement/requests/{id}.
 */

const BIS_PORTAL_URL = 'https://www.bis.gov.in/';

// Generic prompts shown only when nothing matched and the backend returned no
// specific missing-requirement list. Labelled in the UI as a general checklist.
const GENERIC_SPEC_CHECKLIST = [
  'Material grade or composition',
  'Dimensions, tolerances and thickness',
  'Operating temperature and environmental exposure',
  'Mechanical, electrical or physical test requirements',
  'Required certification or purchaser specification',
];

const FLOW = [
  ['requirements', 'Requirements'],
  ['recommended', 'Recommended IS'],
  ['related', 'Related standards'],
  ['certification', 'Certification'],
  ['gaps', 'Tender gaps'],
];

const fmtDate = (iso) => {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString('en-IN', { dateStyle: 'medium' });
};

const humanize = (s) => String(s || '').replace(/_/g, ' ');

export default function RecommendationResultsPage({ requestId, onBack }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(Boolean(requestId));
  const [error, setError] = useState(null);

  const loadReport = useCallback(async () => {
    if (!requestId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getProcurementRequestDetail(requestId);
      setReport(data);
    } catch (err) {
      console.error('Load report error:', err);
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [requestId]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  const backButton = (
    <button type="button" className="su-btn su-btn--secondary back-button" onClick={onBack}>
      ← Back to history
    </button>
  );

  if (!requestId) {
    return (
      <div className="su-page">
        <EmptyState
          title="No report selected"
          text="Open a report from your analysis history, or run a new specification analysis."
          action={backButton}
        />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="su-page">
        <LoadingState label="Loading recommendation report…" rows={6} />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="su-page">
        <ErrorState
          title={error?.status === 404 ? 'Report not found' : 'Could not load this report'}
          error={error || 'The report is unavailable.'}
          onRetry={error?.status === 404 ? undefined : loadReport}
          action={backButton}
        />
      </div>
    );
  }

  const recommended = report.recommended_standards || [];
  const potential = report.potentially_applicable_standards || [];
  const allStandards = [...recommended, ...potential];
  const requirements = report.extracted_requirements || [];
  const needsVerification = report.standards_requiring_verification || [];
  const excluded = report.excluded_standards || [];
  const relatedTop = report.related_standards || [];
  const certGuidance = report.certification_guidance || [];
  const missing = report.missing_requirements || [];
  const warnings = report.warnings || [];
  const sources = report.sources || [];
  const tenderGapCount = missing.length + warnings.length + needsVerification.length;

  // overall_status is not part of the response schema; derive a label from counts instead.
  const overall = report.overall_status || (
    recommended.length
      ? 'Applicable standard identified'
      : potential.length
        ? 'Potential standards identified — verification required'
        : 'No directly applicable standard confirmed'
  );

  return (
    <div className="su-page recommendation-report">
      {/* Print-only branding */}
      <div className="print-only-branding" style={{ display: 'none', marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '2px solid #0f172a', paddingBottom: 12 }}>
          <div>
            <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>Indian Standards Procurement Engine</div>
            <div style={{ fontSize: '0.75rem' }}>BIS standards applicability report</div>
          </div>
          <div style={{ textAlign: 'right', fontSize: '0.8rem' }}>
            <div>Ref: {report.request_id || requestId}</div>
            {fmtDate(report.created_at) && <div>{fmtDate(report.created_at)}</div>}
          </div>
        </div>
      </div>

      <header className="su-header">
        <div>
          <div className="su-eyebrow no-print">
            <button type="button" className="su-btn su-btn--ghost back-button" style={{ padding: 0 }} onClick={onBack}>
              ← Analysis history
            </button>
          </div>
          <h1 className="su-title">Standards recommendation report</h1>
          <p className="su-subtitle">
            {report.product_category || 'General procurement'}
            {fmtDate(report.created_at) && <> · {fmtDate(report.created_at)}</>}
            {' · '}<span className="su-mono">{report.request_id || requestId}</span>
          </p>
          <div style={{ marginTop: 10 }}><Badge>{overall}</Badge></div>
          <nav className="su-flow no-print" aria-label="Report sections">
            {FLOW.map(([id, label], i) => (
              <React.Fragment key={id}>
                {i > 0 && <span aria-hidden="true">→</span>}
                <a href={`#rr-${id}`}>{label}</a>
              </React.Fragment>
            ))}
          </nav>
        </div>
        <div className="su-header-actions no-print">
          <button type="button" className="su-btn su-btn--secondary print-button" onClick={() => window.print()}>
            Print / export PDF
          </button>
        </div>
      </header>

      <div className="su-summary-strip">
        <StatTile label="Requirements" value={requirements.length} tone="info" />
        <StatTile label="Recommended" value={recommended.length} tone={recommended.length ? 'ok' : 'neutral'} />
        <StatTile label="Potentially applicable" value={potential.length} tone={potential.length ? 'warn' : 'neutral'} />
        <StatTile label="Certification items" value={certGuidance.length} />
        <StatTile label="Tender gaps" value={tenderGapCount} tone={tenderGapCount ? 'danger' : 'ok'} />
      </div>

      {report.notice && (
        <div className="su-notice su-notice--warn report-banner report-card" style={{ marginBottom: 24 }}>
          <strong>Notice</strong>
          {report.notice}
        </div>
      )}

      {/* 1. Requirements */}
      <section id="rr-requirements" className="su-section report-section">
        <div className="su-section-head">
          <h2 className="su-section-title report-section-title"><span className="su-step">01</span>Procurement requirements</h2>
        </div>
        <div className="su-card report-card" style={{ marginBottom: 12 }}>
          <div className="su-rec-label">Summary</div>
          <p className="su-rec-text">{report.procurement_summary || 'No summary was returned for this request.'}</p>
        </div>
        {requirements.length ? (
          <div className="su-req-grid extracted-reqs-grid">
            {requirements.map((req, i) => (
              <div key={i} className="su-req report-card">
                <div className="su-req-cat">{req.category}</div>
                <div className="su-req-param">{req.parameter}</div>
                <div className="su-req-val">{req.value_spec}</div>
              </div>
            ))}
          </div>
        ) : (
          <p className="su-muted" style={{ fontSize: '0.84rem' }}>
            No structured technical parameters were extracted from the specification.
          </p>
        )}
      </section>

      {/* 2. Recommended IS */}
      <section id="rr-recommended" className="su-section report-section">
        <div className="su-section-head">
          <h2 className="su-section-title report-section-title"><span className="su-step">02</span>Recommended Indian Standards</h2>
          <span className="su-section-meta">{allStandards.length} standard(s)</span>
        </div>

        {allStandards.length ? (
          allStandards.map((std, idx) => <RecommendationCard key={`${std.standard_number}-${idx}`} std={std} />)
        ) : (
          <div className="su-card report-card">
            <h3 className="su-state-title" style={{ marginBottom: 6 }}>No applicable standard confirmed</h3>
            <p className="su-rec-text">
              No technically relevant Indian Standard was confirmed from the available catalogue and the extracted
              requirements. This does not mean that no standard exists.
            </p>
            {missing.length === 0 && (
              <div style={{ marginTop: 12 }}>
                <div className="su-rec-label">General checklist — add these details and re-run</div>
                <ul className="su-gap-list">
                  {GENERIC_SPEC_CHECKLIST.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>

      {/* 3. Related / normative standards (report level) */}
      <section id="rr-related" className="su-section report-section">
        <div className="su-section-head">
          <h2 className="su-section-title report-section-title"><span className="su-step">03</span>Related &amp; normative standards</h2>
          <span className="su-section-meta">Test methods, normative references and allied products</span>
        </div>
        {relatedTop.length ? (
          <RelatedTable items={relatedTop} />
        ) : (
          <p className="su-muted" style={{ fontSize: '0.84rem' }}>
            No report-level related standards were returned. Per-standard references, where available, are listed on each
            recommendation above.
          </p>
        )}
      </section>

      {/* 4. Certification */}
      <section id="rr-certification" className="su-section report-section">
        <div className="su-section-head">
          <h2 className="su-section-title report-section-title"><span className="su-step">04</span>Certification &amp; regulatory guidance</h2>
        </div>
        {certGuidance.length ? (
          certGuidance.map((c, i) => <CertificationItem key={i} cert={c} />)
        ) : (
          <div className="su-notice su-notice--warn report-card">
            <strong>Certification applicability not confirmed</strong>
            Verify the latest BIS notification or Quality Control Order with the issuing authority before tender publication.
          </div>
        )}
      </section>

      {/* 5. Tender gaps */}
      <section id="rr-gaps" className="su-section report-section">
        <div className="su-section-head">
          <h2 className="su-section-title report-section-title"><span className="su-step">05</span>Tender gaps &amp; verification</h2>
          <span className="su-section-meta">Resolve these before publishing the tender</span>
        </div>

        <div className="su-card report-card">
          <div className="su-rec-label">Missing technical information ({missing.length})</div>
          {missing.length ? (
            <ul className="su-gap-list">{missing.map((m, i) => <li key={i}>{m}</li>)}</ul>
          ) : (
            <p className="su-muted" style={{ fontSize: '0.84rem' }}>No missing information was flagged for this specification.</p>
          )}
        </div>

        {warnings.length > 0 && (
          <div className="su-card report-card">
            <div className="su-rec-label">Warnings ({warnings.length})</div>
            <ul className="su-gap-list su-gap-list--danger">{warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
          </div>
        )}

        <div className="su-card report-card">
          <div className="su-rec-label">Standards requiring official verification ({needsVerification.length})</div>
          {needsVerification.length ? (
            <ul className="su-list">
              {needsVerification.map((v, i) => (
                <li key={i}>
                  <div className="su-list-top">
                    <span className="su-code">{v.standard_number}</span>
                    <Badge>{v.verification_status || 'Verification required'}</Badge>
                  </div>
                  <div>{v.title}</div>
                  <a
                    className="su-link no-print"
                    href={v.source_url || BIS_PORTAL_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {v.source_url ? 'Open source record ↗' : 'Verify on the BIS portal ↗'}
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <p className="su-muted" style={{ fontSize: '0.84rem' }}>No standards were flagged for separate verification.</p>
          )}
        </div>

        {excluded.length > 0 && (
          <div className="su-card report-card excluded-standards-container">
            <div className="su-rec-label">Excluded candidates ({excluded.length})</div>
            <p className="su-muted" style={{ fontSize: '0.8rem', marginBottom: 10 }}>
              Retrieved by search but excluded due to product-domain or parameter mismatch.
            </p>
            <ul className="su-list">
              {excluded.map((ex, i) => (
                <li key={i}>
                  <div className="su-list-top">
                    <span className="su-code">{ex.standard_number}</span>
                    {ex.category && <Badge tone="neutral">{ex.category}</Badge>}
                  </div>
                  <div>{ex.title}</div>
                  <div className="su-muted" style={{ fontSize: '0.78rem', marginTop: 3 }}>Reason: {ex.exclusion_reason}</div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* Sources & disclaimer */}
      <section className="su-section report-section">
        {sources.length > 0 && (
          <div className="su-card report-card" style={{ marginBottom: 12 }}>
            <div className="su-rec-label">Sources</div>
            <ul className="su-evidence" style={{ marginTop: 0 }}>
              {sources.map((s, i) => <li key={i}>{s}</li>)}
            </ul>
          </div>
        )}
        <div className="su-notice su-notice--info disclaimer-box report-card">
          <strong>About this report</strong>
          {report.disclaimer || 'The match score is an internal AI retrieval indicator and does not represent official BIS approval, compliance or certification.'}
          {' '}Confirm revisions, amendments and Quality Control Orders on the official BIS portal before tender publication.
        </div>
      </section>

      <div className="print-footer" style={{ display: 'none' }}>
        Generated by the Indian Standards Procurement Engine · AI-generated analysis requires official verification.
      </div>
    </div>
  );
}

function RecommendationCard({ std }) {
  const score = typeof std.internal_match_score === 'number' ? std.internal_match_score : null;
  const matrix = std.field_comparison_matrix || [];
  const related = std.related_standards || [];
  const certs = std.certification_requirements || [];
  const amendments = std.amendments || [];
  const evidence = std.evidence || [];

  return (
    <article className="su-rec report-card">
      <div className="su-rec-head">
        <div style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <span className="su-rec-num">{std.standard_number}</span>
            <Badge>{std.applicability_status}</Badge>
          </div>
          <div className="su-rec-title">{std.title}</div>
        </div>
        {score !== null && (
          <div className="su-score" title="Internal retrieval indicator — not an official BIS compliance score">
            <div className="su-score-val">{score.toFixed(2)}</div>
            <div className="su-score-bar"><div style={{ width: `${Math.round(score * 100)}%` }} /></div>
            <div className="su-score-label">{std.match_strength ? `${std.match_strength} match · ` : ''}internal score</div>
          </div>
        )}
      </div>

      <div className="su-rec-body">
        {/* Reason */}
        <div className="su-rec-block">
          <div className="su-rec-label"><span className="su-step">A</span>Why this standard</div>
          <p className="su-rec-text su-reason">{std.reasoning || 'No reasoning was returned for this standard.'}</p>
          {std.scope && <p className="su-rec-text" style={{ marginTop: 10 }}><span className="su-muted">Scope — </span>{std.scope}</p>}
          {evidence.length > 0 && (
            <ul className="su-evidence">{evidence.map((e, i) => <li key={i}>{e}</li>)}</ul>
          )}

          {matrix.length > 0 && (
            <div className="su-table-wrap" style={{ marginTop: 14 }}>
              <table className="su-table field-matrix-table">
                <thead>
                  <tr>
                    <th className="matrix-col-param">Parameter</th>
                    <th className="matrix-col-spec">Required</th>
                    <th className="matrix-col-prov">Standard provision</th>
                    <th className="matrix-col-res">Result</th>
                  </tr>
                </thead>
                <tbody>
                  {matrix.map((m, i) => (
                    <tr key={i}>
                      <td className="matrix-col-param" style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{m.parameter}</td>
                      <td className="matrix-col-spec">{m.required_value}</td>
                      <td className="matrix-col-prov">{m.standard_provision}</td>
                      <td className="matrix-col-res"><Badge>{m.result}</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Related / normative */}
        <div className="su-rec-block">
          <div className="su-rec-label"><span className="su-step">B</span>Related &amp; normative standards ({related.length})</div>
          {related.length ? <RelatedTable items={related} /> : (
            <p className="su-muted" style={{ fontSize: '0.82rem' }}>None linked for this standard.</p>
          )}
        </div>

        {/* Version / status */}
        <div className="su-rec-block">
          <div className="su-rec-label"><span className="su-step">C</span>Version &amp; status</div>
          <dl className="su-kv">
            <div><dt>Latest revision</dt><dd className="su-mono">{std.latest_revision || 'Not confirmed'}</dd></div>
            <div><dt>Revision check</dt><dd><Badge>{std.revision_verification_status || 'Unverified'}</Badge></dd></div>
            <div>
              <dt>Official verification</dt>
              <dd>{std.verification_required === false ? <Badge tone="ok">Not required</Badge> : <Badge tone="warn">Required</Badge>}</dd>
            </div>
          </dl>
          {amendments.length > 0 && (
            <ul className="su-evidence" style={{ marginTop: 10 }}>{amendments.map((a, i) => <li key={i}>{a}</li>)}</ul>
          )}
        </div>

        {/* Certification */}
        <div className="su-rec-block">
          <div className="su-rec-label"><span className="su-step">D</span>Certification ({certs.length})</div>
          {certs.length ? certs.map((c, i) => <CertificationItem key={i} cert={c} compact />) : (
            <p className="su-muted" style={{ fontSize: '0.82rem' }}>No certification scheme linked to this standard.</p>
          )}
        </div>
      </div>
    </article>
  );
}

function RelatedTable({ items }) {
  return (
    <div className="su-table-wrap">
      <table className="su-table">
        <thead>
          <tr>
            <th className="rel-col-num">IS number</th>
            <th className="rel-col-title">Title</th>
            <th className="rel-col-type">Relationship</th>
            <th className="rel-col-stat hide-sm">Verification</th>
          </tr>
        </thead>
        <tbody>
          {items.map((r, i) => (
            <tr key={`${r.standard_number}-${i}`}>
              <td className="rel-col-num su-code" style={{ whiteSpace: 'nowrap' }}>{r.standard_number}</td>
              <td className="rel-col-title">
                {r.title}
                {r.description && <div className="su-muted" style={{ fontSize: '0.76rem', marginTop: 2 }}>{r.description}</div>}
              </td>
              <td className="rel-col-type"><Badge tone="neutral">{humanize(r.relationship_type)}</Badge></td>
              <td className="rel-col-stat hide-sm" style={{ fontSize: '0.76rem' }}>{r.verification_status || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CertificationItem({ cert, compact = false }) {
  const facts = [
    ['IS number', cert.relevant_is_number],
    ['Instrument', cert.regulatory_instrument],
    ['Evidence date', cert.evidence_date],
    ['Effective', cert.effective_date],
    ['Evidence source', cert.evidence_source],
  ].filter(([, v]) => v && v !== 'Unverified');

  return (
    <div
      className={compact ? undefined : 'su-card report-card'}
      style={compact ? { border: '1px solid var(--border-color)', borderRadius: 5, padding: '10px 12px', marginBottom: 8 } : undefined}
    >
        <div className="su-list-top">
          <strong style={{ fontSize: '0.9rem' }}>{cert.certification_type}</strong>
          <Badge>{cert.applicability}</Badge>
        </div>
        {(cert.explanation || cert.evidence_text) && (
          <p className="su-rec-text" style={{ fontSize: '0.84rem', marginTop: 4 }}>{cert.explanation || cert.evidence_text}</p>
        )}
        {facts.length > 0 && (
          <dl className="su-kv" style={{ marginTop: 10 }}>
            {facts.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}
          </dl>
        )}
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap', marginTop: 8 }}>
          {cert.verification_status && <span className="su-muted" style={{ fontSize: '0.76rem' }}>{cert.verification_status}</span>}
          {cert.source_url && (
            <a className="su-link no-print" href={cert.source_url} target="_blank" rel="noopener noreferrer">Official source ↗</a>
          )}
        </div>
        {!compact && cert.disclaimer && (
          <div className="su-muted" style={{ fontSize: '0.74rem', marginTop: 6, fontStyle: 'italic' }}>{cert.disclaimer}</div>
        )}
    </div>
  );
}
