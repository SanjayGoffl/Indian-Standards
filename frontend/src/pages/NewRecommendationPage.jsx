import React, { useEffect, useRef, useState } from 'react';
import * as api from '../services/api';
import { ErrorState } from '../components/UiStates';
import './StandardsUI.css';

const ACCEPTED = '.pdf,.docx,.doc,.txt,.png,.jpg,.jpeg';

// Describes what POST /api/procurement/analyze actually does; not a live progress feed.
const PIPELINE = [
  'Extract technical parameters from the text (OCR for scanned documents)',
  'Hybrid search: exact IS number, semantic vectors and keywords',
  'Evaluate applicability against each candidate standard',
  'Resolve certification schemes and revision status',
];

const fmtSize = (bytes) => (bytes < 1024 * 1024 ? `${Math.round(bytes / 1024)} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`);

export default function NewRecommendationPage({ onAnalysisComplete }) {
  const [productCategory, setProductCategory] = useState('');
  const [procurementPurpose, setProcurementPurpose] = useState('');
  const [technicalSpecs, setTechnicalSpecs] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [dragging, setDragging] = useState(false);

  const [loading, setLoading] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState(null);
  const [validation, setValidation] = useState('');

  // Category suggestions come from the categories actually stored in the catalogue.
  const [categories, setCategories] = useState([]);
  const fileInput = useRef(null);

  useEffect(() => {
    api.getIndianStandards()
      .then((data) => {
        const cats = [...new Set((data?.standards || []).map((s) => s.category).filter(Boolean))].sort();
        setCategories(cats);
      })
      .catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    if (!loading) return undefined;
    setElapsed(0);
    const t = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [loading]);

  const pickFile = (file) => {
    if (file) {
      setSelectedFile(file);
      setValidation('');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!technicalSpecs.trim() && !selectedFile) {
      setValidation('Enter the technical specification text or attach a tender document.');
      return;
    }
    setValidation('');

    const formData = new FormData();
    if (productCategory.trim()) formData.append('product_category', productCategory.trim());
    if (procurementPurpose.trim()) formData.append('procurement_purpose', procurementPurpose.trim());
    if (technicalSpecs.trim()) formData.append('technical_specifications', technicalSpecs.trim());
    if (selectedFile) formData.append('file', selectedFile);

    setLoading(true);
    try {
      const result = await api.analyzeProcurementSpecification(formData);
      onAnalysisComplete(result.request_id || result);
    } catch (err) {
      console.error('Procurement analysis error:', err);
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="su-page">
      <header className="su-header">
        <div>
          <h1 className="su-title">Analyze tender</h1>
          <p className="su-subtitle">
            Paste the specification or attach the tender document to get applicable Indian Standards, certification
            requirements and gaps to fix before publishing.
          </p>
        </div>
      </header>

      {error && (
        <div style={{ marginBottom: 16 }}>
          <ErrorState title="The analysis did not complete" error={error} />
        </div>
      )}

      <div className="su-analyze-layout">
        <form className="su-card su-form" onSubmit={handleSubmit} noValidate>
          <div className="su-field su-field--full">
            <label className="su-label" htmlFor="spec-text">
              Technical specification <small>required unless a document is attached</small>
            </label>
            <textarea
              id="spec-text"
              className="su-input su-textarea"
              rows={8}
              value={technicalSpecs}
              onChange={(e) => { setTechnicalSpecs(e.target.value); setValidation(''); }}
              placeholder="e.g. 1.1 kV, 4-core, 25 sq.mm aluminium conductor, XLPE insulated, PVC sheathed armoured power cable, FRLS outer sheath…"
              disabled={loading}
            />
          </div>

          <div className="su-field su-field--full">
            <span className="su-label">Tender document <small>PDF, DOCX, TXT or scanned image</small></span>
            <div
              className={`su-dropzone${dragging ? ' is-drag' : ''}`}
              role="button"
              tabIndex={0}
              onClick={() => !loading && fileInput.current?.click()}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileInput.current?.click(); }}
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => { e.preventDefault(); setDragging(false); pickFile(e.dataTransfer.files?.[0]); }}
            >
              <span className="su-dropzone-icon" aria-hidden="true">
                <svg width="18" height="18" viewBox="0 0 17 17" fill="none">
                  <path d="M8.5 11V2.5M5 6l3.5-3.5L12 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M2.5 11v2.5a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              </span>
              <div style={{ minWidth: 0, flex: 1 }}>
                {selectedFile ? (
                  <>
                    <div style={{ fontWeight: 600, fontSize: '0.88rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{selectedFile.name}</div>
                    <div className="su-muted" style={{ fontSize: '0.78rem' }}>{fmtSize(selectedFile.size)}</div>
                  </>
                ) : (
                  <>
                    <div style={{ fontWeight: 600, fontSize: '0.88rem' }}>Drop a file here or click to browse</div>
                    <div className="su-muted" style={{ fontSize: '0.78rem' }}>Scanned pages are read with OCR</div>
                  </>
                )}
              </div>
              {selectedFile && !loading && (
                <button
                  type="button"
                  className="su-btn su-btn--ghost"
                  style={{ color: 'var(--accent-rose)' }}
                  onClick={(e) => { e.stopPropagation(); setSelectedFile(null); if (fileInput.current) fileInput.current.value = ''; }}
                >
                  Remove
                </button>
              )}
              <input
                ref={fileInput}
                type="file"
                accept={ACCEPTED}
                onChange={(e) => pickFile(e.target.files?.[0])}
                style={{ display: 'none' }}
              />
            </div>
          </div>

          <div className="su-field">
            <label className="su-label" htmlFor="category">Product category <small>optional</small></label>
            <input
              id="category"
              className="su-input"
              list="category-options"
              value={productCategory}
              onChange={(e) => setProductCategory(e.target.value)}
              placeholder="e.g. Electrical cables"
              disabled={loading}
            />
            <datalist id="category-options">
              {categories.map((c) => <option key={c} value={c} />)}
            </datalist>
            {categories.length > 0 && !productCategory && (
              <div className="su-suggest">
                {categories.slice(0, 4).map((c) => (
                  <button key={c} type="button" onClick={() => setProductCategory(c)}>{c}</button>
                ))}
              </div>
            )}
          </div>

          <div className="su-field">
            <label className="su-label" htmlFor="purpose">Procurement purpose <small>optional</small></label>
            <input
              id="purpose"
              className="su-input"
              value={procurementPurpose}
              onChange={(e) => setProcurementPurpose(e.target.value)}
              placeholder="e.g. Substation cabling for a municipal project"
              disabled={loading}
            />
          </div>

          <div className="su-form-actions">
            <span className="su-muted" style={{ fontSize: '0.8rem' }} role="status" aria-live="polite">
              {validation
                ? <span style={{ color: 'var(--accent-rose)' }}>{validation}</span>
                : loading ? `Analyzing… ${elapsed}s elapsed. Large or scanned documents can take a minute or more.` : ''}
            </span>
            <button type="submit" className="su-btn su-btn--primary" disabled={loading} style={{ minWidth: 200 }}>
              {loading && <span className="su-spinner" />}
              {loading ? 'Analyzing…' : 'Analyze & recommend standards'}
            </button>
          </div>
        </form>

        <aside className="su-card">
          <div className="su-rec-label">What the analysis does</div>
          <ol className="su-steps">
            {PIPELINE.map((step, i) => (
              <li key={step}><span>{i + 1}</span><span>{step}</span></li>
            ))}
          </ol>
          <p className="su-muted" style={{ fontSize: '0.78rem', marginTop: 12, lineHeight: 1.5 }}>
            Results are advisory. Always confirm revisions and certification orders on the official BIS portal.
          </p>
        </aside>
      </div>
    </div>
  );
}
