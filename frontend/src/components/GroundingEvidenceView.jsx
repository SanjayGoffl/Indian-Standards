import React, { useMemo, useState } from 'react';

/**
 * GroundingEvidenceView
 * Full evidence inspector for selected retrieved chunk.
 * Props:
 *  selectedSource: retrieval chunk or source object (with chunk_id)
 *  retrievalResults: array of ranked chunks
 *  sources: cited sources
 *  confidence: number
 *  retrievalMeta: {semantic_candidates, exact_candidates, merged_candidates, ...}
 *  queryUnderstanding: object | null
 *  onSelectSource: (chunk) => void
 */

function highlightMatchedTerms(text, matchedTerms) {
  if (!text || !matchedTerms || matchedTerms.length === 0) return text;
  // Escape and sort by length desc to avoid partial overlap
  const terms = [...matchedTerms]
    .filter((t) => typeof t === 'string' && t.trim().length >= 2)
    .sort((a, b) => b.length - a.length)
    .slice(0, 12);
  if (terms.length === 0) return text;
  const escaped = terms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const regex = new RegExp(`(${escaped.join('|')})`, 'gi');
  const parts = text.split(regex);
  return parts.map((part, i) => {
    const isMatch = terms.some((t) => t.toLowerCase() === part.toLowerCase());
    if (isMatch) {
      return (
        <mark
          key={i}
          style={{
            background: 'hsla(174, 100%, 41%, 0.22)',
            border: '1px solid hsla(174, 100%, 41%, 0.35)',
            color: 'var(--accent-purple)',
            padding: '0 3px',
            borderRadius: '4px',
            fontWeight: 600,
          }}
        >
          {part}
        </mark>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

function ScoreBar({ label, value, color = 'var(--accent-purple)' }) {
  const pct = Math.round(Math.max(0, Math.min(1, Number(value) || 0)) * 100);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.7rem' }}>
      <span style={{ width: '70px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', fontSize: '0.65rem' }}>{label}</span>
      <div style={{ flex: 1, height: '6px', borderRadius: '99px', background: 'var(--border-color)', overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', borderRadius: '99px', background: color, transition: 'width 0.4s ease', boxShadow: `0 0 6px ${color}55` }} />
      </div>
      <span style={{ width: '36px', textAlign: 'right', fontWeight: 700, color, fontFamily: 'var(--font-mono)' }}>{pct}%</span>
    </div>
  );
}

export default function GroundingEvidenceView({
  selectedSource,
  retrievalResults = [],
  sources = [],
  confidence,
  retrievalMeta,
  queryUnderstanding,
  onSelectSource,
}) {
  const [copied, setCopied] = useState(false);
  const [showAllMeta, setShowAllMeta] = useState(false);

  const activeChunk = useMemo(() => {
    if (!selectedSource) return null;
    // If selectedSource is already a retrieval chunk with content
    if (selectedSource.content) return selectedSource;
    // Otherwise lookup by chunk_id
    const id = selectedSource.chunk_id;
    if (!id) return selectedSource;
    return retrievalResults.find((r) => String(r.chunk_id) === String(id)) || selectedSource;
  }, [selectedSource, retrievalResults]);

  const isCited = useMemo(() => {
    if (!activeChunk) return false;
    return sources.some((s) => String(s.chunk_id) === String(activeChunk.chunk_id));
  }, [activeChunk, sources]);

  const citationRef = useMemo(() => {
    if (!activeChunk) return null;
    const src = sources.find((s) => String(s.chunk_id) === String(activeChunk.chunk_id));
    return src?.reference || null;
  }, [activeChunk, sources]);

  if (!selectedSource) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* Header */}
        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '28px', height: '28px', borderRadius: '8px', background: 'linear-gradient(135deg, var(--accent-purple), var(--accent-blue))', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </span>
            Grounding Evidence View
          </h3>
          <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>Inspect semantic matches, grounding scores & evidence</p>
        </div>

        {/* Empty state */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '32px 20px', color: 'var(--text-muted)', textAlign: 'center', border: '1px dashed var(--border-color)', borderRadius: '12px', background: 'hsla(185,18%,14%,0.2)' }}>
            <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'hsla(174, 100%, 41%, 0.10)', border: '1px solid hsla(174, 100%, 41%, 0.18)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '12px', color: 'var(--accent-purple)' }}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
                <line x1="8" y1="11" x2="14" y2="11" />
              </svg>
            </div>
            <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>No Evidence Selected</h4>
            <p style={{ fontSize: '0.75rem', lineHeight: 1.5, maxWidth: '280px' }}>Ask a question, then click any citation badge <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', minWidth: '22px', height: '16px', padding: '0 4px', borderRadius: '4px', background: 'hsla(174,100%,41%,0.15)', border: '1px solid hsla(174,100%,41%,0.25)', color: 'var(--accent-purple)', fontWeight: 700, fontFamily: 'var(--font-mono)', fontSize: '0.65rem', verticalAlign: 'middle' }}>[1]</span> in the answer or a card in the retrieval list to inspect its grounded evidence.</p>
          </div>

          {/* Retrieval overview when available */}
          {retrievalResults.length > 0 && (
            <div>
              <h4 style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                Retrieved Context
                <span className="badge badge-blue" style={{ fontSize: '0.65rem', padding: '2px 6px' }}>{retrievalResults.length} chunks</span>
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {retrievalResults.map((src, idx) => {
                  const pct = Math.round(Number(src.relevance_score || 0) * 100);
                  const isSelected = String(selectedSource?.chunk_id) === String(src.chunk_id);
                  return (
                    <button
                      key={src.chunk_id || idx}
                      onClick={() => onSelectSource && onSelectSource(src)}
                      style={{
                        padding: '10px 12px',
                        borderRadius: '10px',
                        border: `1px solid ${isSelected ? 'var(--accent-purple)' : 'var(--border-color)'}`,
                        background: isSelected ? 'hsla(174,100%,41%,0.08)' : 'hsla(185,18%,14%,0.25)',
                        cursor: 'pointer',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        fontSize: '0.78rem',
                        textAlign: 'left',
                        transition: 'all 0.18s ease',
                        width: '100%',
                      }}
                    >
                      <span style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, flex: 1 }}>
                        <span style={{ width: '22px', height: '22px', borderRadius: '6px', background: 'hsla(174,100%,41%,0.12)', border: '1px solid hsla(174,100%,41%,0.2)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-purple)', fontWeight: 700, fontSize: '0.65rem', fontFamily: 'var(--font-mono)', flexShrink: 0 }}>{idx + 1}</span>
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-primary)', fontWeight: 500 }}>{src.metadata?.filename || 'Retrieved document'}</span>
                        <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.65rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>[{src.chunk_id || 'chunk'}]</span>
                      </span>
                      <span style={{ fontWeight: 700, color: pct >= 70 ? 'var(--accent-emerald)' : pct >= 40 ? 'var(--accent-blue)' : 'var(--accent-rose)', flexShrink: 0, marginLeft: '8px' }}>{pct}%</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Retrieval stats */}
          {retrievalMeta && (
            <div className="glass-card" style={{ padding: '12px', borderRadius: '10px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.72rem' }}>
              <div><span style={{ color: 'var(--text-muted)' }}>Semantic:</span> <strong style={{ color: 'var(--text-primary)' }}>{retrievalMeta.semantic_candidates ?? 0}</strong></div>
              <div><span style={{ color: 'var(--text-muted)' }}>Exact:</span> <strong style={{ color: 'var(--text-primary)' }}>{retrievalMeta.exact_candidates ?? 0}</strong></div>
              <div><span style={{ color: 'var(--text-muted)' }}>Merged:</span> <strong style={{ color: 'var(--text-primary)' }}>{retrievalMeta.merged_candidates ?? 0}</strong></div>
              <div><span style={{ color: 'var(--text-muted)' }}>Returned:</span> <strong style={{ color: 'var(--accent-emerald)' }}>{retrievalMeta.returned_results ?? retrievalResults.length}</strong></div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Selected state
  const content = activeChunk.content || '';
  const relevancePct = Math.round(Number(activeChunk.relevance_score || 0) * 100);
  const relevanceColor = relevancePct >= 70 ? 'var(--accent-emerald)' : relevancePct >= 40 ? 'var(--accent-blue)' : 'var(--accent-rose)';
  const confidencePct = Number.isFinite(Number(confidence)) ? Math.round(Number(confidence) * 100) : null;

  const highlightedContent = highlightMatchedTerms(content, activeChunk.matched_terms);

  const handleCopy = () => {
    if (!content) return;
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div style={{ padding: '18px 20px', borderBottom: '1px solid var(--border-color)', background: 'hsla(185,24%,7%,0.6)', backdropFilter: 'blur(10px)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
          <span style={{ width: '28px', height: '28px', borderRadius: '8px', background: 'linear-gradient(135deg, var(--accent-purple), var(--accent-blue))', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: '#fff', flexShrink: 0 }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
          </span>
          <div style={{ textAlign: 'left', flex: 1, minWidth: 0 }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, lineHeight: 1.2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {activeChunk.metadata?.filename || activeChunk.source || 'Retrieved Evidence'}
            </h3>
            <p style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {activeChunk.chunk_id} {citationRef && <span style={{ color: 'var(--accent-purple)', fontWeight: 700 }}>• Cited as {citationRef}</span>}
            </p>
          </div>
          <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', padding: '4px 8px', borderRadius: '99px', fontSize: '0.7rem', fontWeight: 800, background: `${relevanceColor}18`, color: relevanceColor, border: `1px solid ${relevanceColor}35`, flexShrink: 0 }}>
            {relevancePct}% relevant
          </span>
        </div>

        {/* Grounding verification badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          {isCited ? (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '0.68rem', fontWeight: 700, color: 'var(--accent-emerald)', background: 'hsla(145,80%,42%,0.10)', border: '1px solid hsla(145,80%,42%,0.25)', padding: '4px 8px', borderRadius: '99px' }}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              Cited in answer {citationRef}
            </span>
          ) : (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '0.68rem', fontWeight: 600, color: 'var(--text-muted)', background: 'hsla(185,18%,14%,0.35)', border: '1px solid var(--border-color)', padding: '4px 8px', borderRadius: '99px' }}>
              Not directly cited • Supporting context
            </span>
          )}
          {activeChunk.matched_terms?.length > 0 && (
            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent-purple)', display: 'inline-block' }} />
              {activeChunk.matched_terms.length} evidence term(s)
            </span>
          )}
        </div>
      </div>

      {/* Scrollable content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {/* Document details */}
        <div className="glass-card" style={{ padding: '12px', borderRadius: '10px', display: 'flex', flexDirection: 'column', gap: '8px', background: 'hsla(185,18%,14%,0.28)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem' }}>
            <span style={{ color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Provenance</span>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>ID: {activeChunk.chunk_id || '—'}</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.75rem' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.68rem' }}>Document</span>
              <strong style={{ color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{activeChunk.metadata?.filename || '—'}</strong>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.68rem' }}>Chunk index</span>
              <strong style={{ color: 'var(--text-primary)' }}>{activeChunk.metadata?.chunk_index ?? '—'}</strong>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.68rem' }}>Page / locator</span>
              <strong style={{ color: 'var(--text-secondary)' }}>{activeChunk.metadata?.page ?? activeChunk.metadata?.loc ?? '—'}</strong>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.68rem' }}>Document ID</span>
              <strong style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', fontSize: '0.7rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{activeChunk.metadata?.document_id?.slice(0, 12) || '—'}</strong>
            </div>
          </div>

          {activeChunk.metadata && Object.keys(activeChunk.metadata).length > 0 && (
            <button
              onClick={() => setShowAllMeta((v) => !v)}
              style={{
                marginTop: '4px',
                background: 'transparent',
                border: 'none',
                color: 'var(--accent-blue)',
                fontSize: '0.7rem',
                fontWeight: 600,
                cursor: 'pointer',
                textAlign: 'left',
                padding: 0,
              }}
            >
              {showAllMeta ? 'Hide metadata' : `Show all metadata (${Object.keys(activeChunk.metadata).length} fields)`}
            </button>
          )}
          {showAllMeta && activeChunk.metadata && (
            <div style={{ background: 'var(--bg-input)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '8px', fontFamily: 'var(--font-mono)', fontSize: '0.68rem', lineHeight: 1.6, color: 'var(--text-secondary)', wordBreak: 'break-all' }}>
              {Object.entries(activeChunk.metadata).map(([k, v]) => (
                <div key={k} style={{ display: 'flex', gap: '8px' }}>
                  <span style={{ color: 'var(--accent-purple)', fontWeight: 600, flexShrink: 0 }}>{k}:</span>
                  <span style={{ color: 'var(--text-secondary)' }}>{String(v)}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Score breakdown */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', padding: '12px', borderRadius: '10px', background: 'hsla(185,18%,14%,0.28)', border: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2px' }}>
            <h4 style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Evidence Scores</h4>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>Grounding strength per signal</span>
          </div>
          <ScoreBar label="Relevance" value={activeChunk.relevance_score} color={relevanceColor} />
          <ScoreBar label="Semantic" value={activeChunk.semantic_score} color="var(--accent-blue)" />
          <ScoreBar label="Keyword" value={activeChunk.keyword_score} color="var(--accent-purple)" />
          <ScoreBar label="Lexical" value={activeChunk.lexical_score} color="var(--accent-cyan)" />
          <ScoreBar label="Synergy" value={activeChunk.synergy_score} color="var(--accent-emerald)" />
          <ScoreBar label="Evidence" value={activeChunk.evidence_score} color="var(--accent-emerald)" />
          {activeChunk.distance != null && (
            <div style={{ marginTop: '6px', display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              <span>Distance: {Number(activeChunk.distance).toFixed(4)}</span>
              <span>Relevance = 1 / (1 + distance)</span>
            </div>
          )}
        </div>

        {/* Matched terms */}
        {activeChunk.matched_terms && activeChunk.matched_terms.length > 0 && (
          <div>
            <h4 style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px' }}>Matched Evidence Terms</h4>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {activeChunk.matched_terms.map((term) => (
                <span key={term} style={{ fontSize: '0.7rem', padding: '4px 8px', borderRadius: '99px', background: 'hsla(174,100%,41%,0.10)', border: '1px solid hsla(174,100%,41%,0.22)', color: 'var(--accent-purple)', fontWeight: 600 }}>
                  {term}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Chunk content with highlights */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <h4 style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Retrieved Context Chunk</h4>
            <button
              onClick={handleCopy}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '5px 10px',
                borderRadius: '8px',
                border: '1px solid var(--border-color)',
                background: copied ? 'hsla(145,80%,42%,0.14)' : 'hsla(185,18%,14%,0.35)',
                color: copied ? 'var(--accent-emerald)' : 'var(--text-secondary)',
                fontSize: '0.7rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.18s ease',
              }}
            >
              {copied ? (
                <>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  Copied
                </>
              ) : (
                <>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                  </svg>
                  Copy evidence
                </>
              )}
            </button>
          </div>
          <div
            style={{
              padding: '14px',
              fontSize: '0.84rem',
              lineHeight: '1.65',
              fontFamily: 'var(--font-mono)',
              background: 'var(--bg-input)',
              border: `1px solid ${isCited ? 'hsla(174,100%,41%,0.28)' : 'var(--border-color)'}`,
              borderRadius: '10px',
              color: 'var(--text-secondary)',
              maxHeight: '280px',
              overflowY: 'auto',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              boxShadow: isCited ? '0 0 16px var(--accent-purple-glow)' : 'none',
            }}
          >
            {highlightedContent}
          </div>
          <p style={{ marginTop: '6px', fontSize: '0.68rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '2px', background: 'hsla(174,100%,41%,0.32)', border: '1px solid hsla(174,100%,41%,0.4)', display: 'inline-block' }} />
            Highlighted spans correspond to matched evidence terms that grounded the answer.
          </p>
        </div>

        {/* Confidence & retrieval */}
        {(confidencePct != null || retrievalMeta) && (
          <div className="glass-card" style={{ padding: '12px', borderRadius: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {confidencePct != null && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem' }}>
                <span style={{ color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', fontSize: '0.68rem' }}>Answer confidence</span>
                <span style={{ flex: 1, height: '6px', borderRadius: '99px', background: 'var(--border-color)', overflow: 'hidden' }}>
                  <span style={{ display: 'block', width: `${confidencePct}%`, height: '100%', background: relevanceColor, borderRadius: '99px' }} />
                </span>
                <strong style={{ color: relevanceColor }}>{confidencePct}%</strong>
              </div>
            )}
            {retrievalMeta && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                <span>semantic: <strong style={{ color: 'var(--text-primary)' }}>{retrievalMeta.semantic_candidates}</strong></span>
                <span>exact: <strong style={{ color: 'var(--text-primary)' }}>{retrievalMeta.exact_candidates}</strong></span>
                <span>merged: <strong style={{ color: 'var(--text-primary)' }}>{retrievalMeta.merged_candidates}</strong></span>
                <span>returned: <strong style={{ color: 'var(--accent-emerald)' }}>{retrievalMeta.returned_results}</strong></span>
              </div>
            )}
          </div>
        )}

        {/* All matches list */}
        {retrievalResults.length > 0 && (
          <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '14px' }}>
            <h4 style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              All Matches
              <span style={{ fontSize: '0.65rem', padding: '2px 6px', borderRadius: '99px', background: 'hsla(174,100%,41%,0.10)', border: '1px solid hsla(174,100%,41%,0.18)', color: 'var(--accent-purple)', fontWeight: 700 }}>{retrievalResults.length}</span>
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {retrievalResults.map((src, idx) => {
                const pct = Math.round(Number(src.relevance_score || 0) * 100);
                const col = pct >= 70 ? 'var(--accent-emerald)' : pct >= 40 ? 'var(--accent-blue)' : 'var(--text-muted)';
                const isActive = String(activeChunk.chunk_id) === String(src.chunk_id);
                const cited = sources.some((s) => String(s.chunk_id) === String(src.chunk_id));
                const ref = sources.find((s) => String(s.chunk_id) === String(src.chunk_id))?.reference;
                return (
                  <button
                    key={src.chunk_id || idx}
                    onClick={() => onSelectSource && onSelectSource(src)}
                    style={{
                      padding: '9px 10px',
                      borderRadius: '9px',
                      border: `1px solid ${isActive ? 'var(--accent-purple)' : 'var(--border-color)'}`,
                      background: isActive ? 'hsla(174,100%,41%,0.08)' : cited ? 'hsla(145,80%,42%,0.06)' : 'transparent',
                      cursor: 'pointer',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      fontSize: '0.72rem',
                      textAlign: 'left',
                      width: '100%',
                      transition: 'all 0.18s ease',
                    }}
                  >
                    <span style={{ display: 'flex', alignItems: 'center', gap: '7px', minWidth: 0, flex: 1 }}>
                      <span style={{ width: '20px', height: '20px', borderRadius: '6px', background: cited ? 'hsla(145,80%,42%,0.14)' : 'hsla(185,18%,14%,0.5)', border: `1px solid ${cited ? 'hsla(145,80%,42%,0.22)' : 'var(--border-color)'}`, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: cited ? 'var(--accent-emerald)' : 'var(--text-muted)', fontWeight: 700, fontSize: '0.6rem', fontFamily: 'var(--font-mono)', flexShrink: 0 }}>{ref ? ref.replace(/\[|\]/g, '') : idx + 1}</span>
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-primary)', fontWeight: isActive ? 600 : 400, maxWidth: '170px' }}>{src.metadata?.filename || 'Retrieved document'}</span>
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
                      {cited && <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent-emerald)', display: 'inline-block', boxShadow: '0 0 6px hsla(145,80%,42%,0.5)' }} />}
                      <span style={{ fontWeight: 700, color: col, fontFamily: 'var(--font-mono)' }}>{pct}%</span>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Query understanding debug (optional, collapsed) */}
        {queryUnderstanding && (
          <details style={{ marginTop: '4px', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            <summary style={{ cursor: 'pointer', color: 'var(--text-secondary)', fontWeight: 600 }}>Query understanding & routing</summary>
            <div style={{ marginTop: '8px', padding: '10px', borderRadius: '8px', background: 'var(--bg-input)', border: '1px solid var(--border-color)', fontFamily: 'var(--font-mono)', fontSize: '0.68rem', lineHeight: 1.6 }}>
              <div><span style={{ color: 'var(--accent-purple)' }}>type:</span> {queryUnderstanding.query_type}</div>
              <div><span style={{ color: 'var(--accent-purple)' }}>normalized:</span> {queryUnderstanding.normalized_query}</div>
              <div><span style={{ color: 'var(--accent-purple)' }}>keywords:</span> {(queryUnderstanding.keywords || []).join(', ') || '—'}</div>
              <div><span style={{ color: 'var(--accent-purple)' }}>exact:</span> {(queryUnderstanding.exact_terms || []).join(', ') || '—'}</div>
            </div>
          </details>
        )}
      </div>
    </div>
  );
}
