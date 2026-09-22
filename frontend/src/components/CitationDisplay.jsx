import React from 'react';

/**
 * CitationDisplay
 * - Renders answer with inline citation badges parsed from [1], [2] etc.
 * - Shows grounding cards for each cited source with evidence preview.
 * Props:
 *  answer: string
 *  sources: [{source, reference, chunk_id, relevance_score, metadata}]
 *  retrievalResults: [{chunk_id, content, metadata, relevance_score, ...}]
 *  confidence: number 0-1
 *  onSelectCitation: (sourceObj, retrievalChunk) => void
 *  activeChunkId: string | null
 */
export default function CitationDisplay({
  answer,
  sources = [],
  retrievalResults = [],
  confidence,
  onSelectCitation,
  activeChunkId,
}) {
  const hasCitations = sources && sources.length > 0;

  // Map chunk_id -> retrieval chunk for grounding content
  const chunkMap = React.useMemo(() => {
    const m = new Map();
    for (const r of retrievalResults || []) {
      if (r.chunk_id) m.set(String(r.chunk_id), r);
    }
    return m;
  }, [retrievalResults]);

  // Also map reference number -> source
  // reference is like "[1]"
  const refToSource = React.useMemo(() => {
    const m = new Map();
    sources.forEach((s) => {
      const num = parseInt(String(s.reference).replace(/[^0-9]/g, ''), 10);
      if (!isNaN(num)) m.set(num, s);
    });
    return m;
  }, [sources]);

  // Parse answer into parts with inline citations
  const renderAnswerWithCitations = () => {
    if (!answer) return null;
    // Match [1], [2], also 【1】 normalized already but handle both
    const regex = /(\[(\d+)\]|【(\d+)】)/g;
    const parts = [];
    let lastIndex = 0;
    let match;
    let key = 0;
    while ((match = regex.exec(answer)) !== null) {
      const full = match[0];
      const num = parseInt(match[2] || match[3], 10);
      const idx = match.index;
      if (idx > lastIndex) {
        parts.push(
          <span key={`t-${key++}`}>{answer.slice(lastIndex, idx)}</span>
        );
      }
      const src = refToSource.get(num);
      const chunk = src ? chunkMap.get(String(src.chunk_id)) : null;
      const isActive = src && String(src.chunk_id) === String(activeChunkId);
      const relevance = src?.relevance_score ?? chunk?.relevance_score;

      // color by relevance
      const getCiteStyle = () => {
        if (relevance == null) return {};
        const pct = Number(relevance);
        if (pct >= 0.7) return { borderColor: 'var(--accent-emerald)', color: 'var(--accent-emerald)' };
        if (pct >= 0.4) return { borderColor: 'var(--accent-blue)', color: 'var(--accent-blue)' };
        return { borderColor: 'var(--accent-rose)', color: 'var(--accent-rose)' };
      };

      const citeStyle = getCiteStyle();

      parts.push(
        <button
          key={`c-${key++}-${num}`}
          onClick={() => {
            if (src && onSelectCitation) {
              onSelectCitation(src, chunk || src);
            }
          }}
          title={src ? `${src.source} • ${Math.round(Number(relevance || 0) * 100)}% relevance • Click to view evidence` : `Citation ${full}`}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            minWidth: '22px',
            height: '20px',
            padding: '0 6px',
            margin: '0 3px',
            borderRadius: '6px',
            fontSize: '0.7rem',
            fontWeight: 700,
            fontFamily: 'var(--font-mono)',
            background: isActive ? 'hsla(174, 100%, 41%, 0.18)' : 'hsla(174, 100%, 41%, 0.10)',
            border: `1px solid ${isActive ? 'var(--accent-purple)' : citeStyle.borderColor || 'hsla(174,100%,41%,0.35)'}`,
            color: isActive ? 'var(--accent-purple)' : citeStyle.color || 'var(--accent-purple)',
            cursor: src ? 'pointer' : 'default',
            verticalAlign: 'middle',
            lineHeight: 1,
            transform: isActive ? 'scale(1.08)' : 'scale(1)',
            boxShadow: isActive ? '0 0 10px var(--accent-purple-glow)' : 'none',
            transition: 'all 0.18s ease',
          }}
          onMouseEnter={(e) => {
            if (!isActive) {
              e.currentTarget.style.background = 'hsla(174, 100%, 41%, 0.22)';
              e.currentTarget.style.transform = 'translateY(-1px) scale(1.05)';
            }
          }}
          onMouseLeave={(e) => {
            if (!isActive) {
              e.currentTarget.style.background = 'hsla(174, 100%, 41%, 0.10)';
              e.currentTarget.style.transform = 'scale(1)';
            }
          }}
        >
          {full}
        </button>
      );
      lastIndex = idx + full.length;
    }
    if (lastIndex < answer.length) {
      parts.push(<span key={`t-${key++}`}>{answer.slice(lastIndex)}</span>);
    }
    // Preserve line breaks
    return (
      <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.7', fontSize: '0.95rem' }}>
        {parts}
      </div>
    );
  };

  const confidencePct = Number.isFinite(Number(confidence)) ? Math.round(Number(confidence) * 100) : null;

  const confidenceColor = () => {
    if (confidencePct == null) return 'var(--text-muted)';
    if (confidencePct >= 75) return 'var(--accent-emerald)';
    if (confidencePct >= 45) return 'var(--accent-blue)';
    return 'var(--accent-rose)';
  };

  const confidenceLabel = () => {
    if (confidencePct == null) return 'Unknown';
    if (confidencePct >= 75) return 'High';
    if (confidencePct >= 45) return 'Medium';
    return 'Low';
  };

  return (
    <div style={{ width: '100%' }}>
      {/* Answer with inline citations */}
      <div style={{ paddingRight: '20px' }}>{renderAnswerWithCitations()}</div>

      {/* Confidence + Citation Summary Bar */}
      {!hasCitations && confidencePct != null ? (
        <div
          style={{
            marginTop: '14px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '10px 12px',
            borderRadius: '10px',
            background: 'hsla(185, 18%, 14%, 0.35)',
            border: '1px solid var(--border-color)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
            <span style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
              Confidence
            </span>
            <div style={{ flex: 1, height: '6px', borderRadius: '99px', background: 'var(--border-color)', overflow: 'hidden', maxWidth: '160px' }}>
              <div
                style={{
                  width: `${confidencePct}%`,
                  height: '100%',
                  borderRadius: '99px',
                  background: confidenceColor(),
                  transition: 'width 0.5s ease',
                  boxShadow: `0 0 8px ${confidenceColor()}55`,
                }}
              />
            </div>
            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: confidenceColor() }}>{confidencePct}%</span>
            <span className="badge" style={{ fontSize: '0.6rem', background: `${confidenceColor()}18`, color: confidenceColor(), border: `1px solid ${confidenceColor()}35`, padding: '2px 6px' }}>
              {confidenceLabel()}
            </span>
          </div>
        </div>
      ) : null}

      {/* Sources Attribution / Citation Display */}
      {hasCitations && (
        <div style={{ marginTop: '16px', paddingTop: '14px', borderTop: '1px solid var(--border-color)' }}>
          {/* Header row */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px', flexWrap: 'wrap', gap: '8px' }}>
            <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
              Citations · Grounding Evidence ({sources.length})
            </span>
            {confidencePct != null && (
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Answer confidence:
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ width: '60px', height: '5px', borderRadius: '99px', background: 'var(--border-color)', display: 'inline-block', overflow: 'hidden', verticalAlign: 'middle' }}>
                    <span style={{ display: 'block', width: `${confidencePct}%`, height: '100%', background: confidenceColor(), borderRadius: '99px' }} />
                  </span>
                  <strong style={{ color: confidenceColor() }}>{confidencePct}%</strong>
                  <span style={{ fontSize: '0.65rem', padding: '2px 6px', borderRadius: '99px', background: `${confidenceColor()}18`, border: `1px solid ${confidenceColor()}30`, color: confidenceColor(), fontWeight: 700 }}>{confidenceLabel()}</span>
                </span>
              </span>
            )}
          </div>

          {/* Citation Cards Grid */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {sources.map((src, idx) => {
              const chunk = chunkMap.get(String(src.chunk_id));
              const content = chunk?.content || '';
              const preview = content ? (content.length > 180 ? content.slice(0, 180) + '…' : content) : 'No preview available';
              const relevancePct = Math.round(Number(src.relevance_score ?? chunk?.relevance_score ?? 0) * 100);
              const isActive = String(src.chunk_id) === String(activeChunkId);
              const relevanceColor = relevancePct >= 70 ? 'var(--accent-emerald)' : relevancePct >= 40 ? 'var(--accent-blue)' : 'var(--accent-rose)';
              const matchedTerms = chunk?.matched_terms || [];
              return (
                <button
                  key={src.chunk_id || src.reference || idx}
                  onClick={() => onSelectCitation && onSelectCitation(src, chunk || src)}
                  style={{
                    textAlign: 'left',
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: '10px',
                    border: `1px solid ${isActive ? 'var(--accent-purple)' : 'var(--border-color)'}`,
                    background: isActive ? 'hsla(174, 100%, 41%, 0.08)' : 'hsla(185, 18%, 14%, 0.30)',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                    transition: 'all 0.2s ease',
                    boxShadow: isActive ? '0 4px 16px var(--accent-purple-glow)' : 'none',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.borderColor = 'var(--border-color-hover)';
                      e.currentTarget.style.background = 'hsla(185, 18%, 20%, 0.45)';
                      e.currentTarget.style.transform = 'translateY(-1px)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.borderColor = 'var(--border-color)';
                      e.currentTarget.style.background = 'hsla(185, 18%, 14%, 0.30)';
                      e.currentTarget.style.transform = 'translateY(0)';
                    }
                  }}
                >
                  {/* Top row: citation badge + file + relevance */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', width: '100%' }}>
                    <span
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        minWidth: '32px',
                        height: '22px',
                        padding: '0 7px',
                        borderRadius: '6px',
                        fontSize: '0.7rem',
                        fontWeight: 800,
                        fontFamily: 'var(--font-mono)',
                        background: 'linear-gradient(135deg, var(--accent-purple), var(--accent-blue))',
                        color: 'hsl(185, 60%, 4%)',
                        boxShadow: '0 2px 8px var(--accent-purple-glow)',
                        letterSpacing: '0.02em',
                      }}
                    >
                      {src.reference || `[${idx + 1}]`}
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)', flex: 1, minWidth: 0 }}>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--accent-purple)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                      </svg>
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{src.source || src.metadata?.filename || chunk?.metadata?.filename || 'Retrieved document'}</span>
                    </span>
                    <span
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        color: relevanceColor,
                        background: `${relevanceColor}14`,
                        border: `1px solid ${relevanceColor}30`,
                        padding: '3px 7px',
                        borderRadius: '99px',
                        flexShrink: 0,
                      }}
                    >
                      <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: relevanceColor, display: 'inline-block' }} />
                      {relevancePct}% match
                    </span>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', maxWidth: '110px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {src.chunk_id || chunk?.chunk_id || ''}
                    </span>
                  </div>

                  {/* Evidence preview */}
                  <div
                    style={{
                      fontSize: '0.78rem',
                      lineHeight: '1.5',
                      color: 'var(--text-secondary)',
                      background: 'var(--bg-input)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      padding: '8px 10px',
                      fontFamily: 'var(--font-mono)',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                    }}
                  >
                    “{preview}”
                  </div>

                  {/* Bottom: matched terms + metadata */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                    {matchedTerms.length > 0 && (
                      <>
                        <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>Evidence:</span>
                        {matchedTerms.slice(0, 4).map((t) => (
                          <span key={t} style={{ fontSize: '0.65rem', padding: '2px 6px', borderRadius: '99px', background: 'hsla(174, 100%, 41%, 0.10)', border: '1px solid hsla(174, 100%, 41%, 0.22)', color: 'var(--accent-purple)', fontWeight: 600 }}>
                            {t}
                          </span>
                        ))}
                        {matchedTerms.length > 4 && <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>+{matchedTerms.length - 4} more</span>}
                      </>
                    )}
                    <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                      {chunk?.metadata?.chunk_index != null && <span>chunk #{chunk.metadata.chunk_index}</span>}
                      {chunk?.semantic_score != null && <span>· sem {Number(chunk.semantic_score).toFixed(2)}</span>}
                      <span style={{ color: 'var(--accent-purple)', fontWeight: 600 }}>View chunk →</span>
                    </span>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Grounding note */}
          <div style={{ marginTop: '10px', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.7rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="16" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
            Every claim above is grounded in the cited chunk. Click any citation badge or card to inspect full evidence.
          </div>
        </div>
      )}
    </div>
  );
}
