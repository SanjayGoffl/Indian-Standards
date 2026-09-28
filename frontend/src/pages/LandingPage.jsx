import React, { useEffect, useState } from 'react';
import * as api from '../services/api';
import './LandingPage.css';

/*
 * Public landing page shown before sign-in.
 * The catalogue preview is live data from the public GET /api/standards
 * endpoint; it is hidden if the backend cannot be reached.
 */

const STEPS = [
  ['Submit the tender', 'Paste specification text or upload the RFP — PDF, DOCX, TXT or a scanned image.'],
  ['Extract requirements', 'An LLM pulls out materials, ratings, dimensions and test requirements; OCR reads scanned pages.'],
  ['Match standards', 'Hybrid search combines exact IS-number lookup, semantic vectors and keywords over the BIS catalogue.'],
  ['Review the report', 'Each standard comes with its reason, related standards, revision status, certification and tender gaps.'],
];

const TECH = [
  ['LLM requirement extraction', 'Groq-hosted large language model orchestrated with LangChain and LangGraph.'],
  ['Semantic embeddings', 'all-MiniLM-L6-v2 sentence-transformer vectors for every standard.'],
  ['Vector search', 'ChromaDB vector store, combined with PostgreSQL keyword and exact-number lookup.'],
  ['Document OCR', 'PaddleOCR reads scanned tender pages and images.'],
  ['BIS catalogue connector', 'Syncs from the BIS public “Know Your Standards” search with SHA-256 change detection.'],
  ['Secure platform', 'FastAPI backend with JWT authentication, React front end, per-user data isolation.'],
];

const REPORT = [
  'Extracted technical requirements',
  'Recommended IS with reasoning and field-by-field comparison',
  'Normative references, test methods and related standards',
  'Revision and amendment status',
  'BIS / ISI / CRS certification guidance',
  'Tender gaps and items needing official verification',
];

export default function LandingPage({ onSignIn, onSignUp }) {
  const [catalog, setCatalog] = useState(null);

  useEffect(() => {
    api.getIndianStandards()
      .then((data) => {
        const list = data?.standards || [];
        setCatalog({
          total: typeof data?.total === 'number' ? data.total : list.length,
          categories: new Set(list.map((s) => s.category).filter(Boolean)).size,
          // Prefer canonical "IS …" records for the preview; all rows are real catalogue data.
          sample: [...new Set([...list.filter((s) => /^IS\s/.test(s.standard_number || '')), ...list])].slice(0, 5),
        });
      })
      .catch(() => setCatalog(null));
  }, []);

  return (
    <div className="lp">
      <header className="lp-nav">
        <div className="lp-container lp-nav-inner">
          <div className="lp-brand">
            <span className="lp-brand-mark">IS</span>
            <span>
              <strong>Standards Engine</strong>
              <small>BIS procurement advisor</small>
            </span>
          </div>
          <nav className="lp-nav-links" aria-label="Page sections">
            <a href="#how">How it works</a>
            <a href="#tech">Technology</a>
            <a href="#report">Report</a>
          </nav>
          <div className="lp-nav-actions">
            <button type="button" className="lp-btn lp-btn--ghost" onClick={onSignIn}>Sign in</button>
            <button type="button" className="lp-btn lp-btn--primary" onClick={onSignUp}>Get started</button>
          </div>
        </div>
      </header>

      <main>
        <section className="lp-hero">
          <div className="lp-container lp-hero-grid">
            <div>
              <span className="lp-kicker">AI for public procurement</span>
              <h1>Find the right Indian Standards for every tender specification.</h1>
              <p className="lp-lead">
                Upload a tender or paste its specification. Get the applicable BIS standards, why they apply,
                certification requirements, and the gaps to fix before you publish.
              </p>
              <div className="lp-hero-actions">
                <button type="button" className="lp-btn lp-btn--primary lp-btn--lg" onClick={onSignUp}>Create account</button>
                <button type="button" className="lp-btn lp-btn--secondary lp-btn--lg" onClick={onSignIn}>Sign in</button>
              </div>
              <p className="lp-note">Advisory tool. Always confirm revisions and certification orders on the official BIS portal.</p>
            </div>

            {catalog && catalog.total > 0 && (
              <div className="lp-preview" aria-label="Live catalogue preview">
                <div className="lp-preview-head">
                  <span className="lp-live-dot" aria-hidden="true" />
                  Live knowledge base
                </div>
                <div className="lp-preview-stats">
                  <div><strong>{catalog.total.toLocaleString('en-IN')}</strong><span>Indian Standards</span></div>
                  <div><strong>{catalog.categories}</strong><span>Product categories</span></div>
                </div>
                <ul className="lp-preview-list">
                  {catalog.sample.map((s) => (
                    <li key={s.id || s.standard_number}>
                      <span className="lp-code">{s.standard_number}</span>
                      <span className="lp-preview-title">{s.title}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </section>

        <section id="how" className="lp-section">
          <div className="lp-container">
            <h2>How it works</h2>
            <ol className="lp-steps">
              {STEPS.map(([title, text], i) => (
                <li key={title}>
                  <span className="lp-step-num">{String(i + 1).padStart(2, '0')}</span>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="tech" className="lp-section lp-section--alt">
          <div className="lp-container">
            <h2>Technology</h2>
            <p className="lp-section-lead">The models and infrastructure behind every recommendation.</p>
            <div className="lp-tech">
              {TECH.map(([title, text]) => (
                <div key={title} className="lp-tech-card">
                  <h3>{title}</h3>
                  <p>{text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="report" className="lp-section">
          <div className="lp-container lp-report">
            <div>
              <h2>One report, ready for tender review</h2>
              <p className="lp-section-lead">
                Every analysis produces a printable report in the order a technical evaluator reads it.
              </p>
              <button type="button" className="lp-btn lp-btn--primary lp-btn--lg" onClick={onSignUp}>Analyze your first tender</button>
            </div>
            <ol className="lp-report-list">
              {REPORT.map((item) => <li key={item}>{item}</li>)}
            </ol>
          </div>
        </section>
      </main>

      <footer className="lp-footer">
        <div className="lp-container">
          Standards Engine is an independent advisory tool and is not affiliated with the Bureau of Indian Standards.
          Match scores are internal retrieval indicators, not official compliance decisions.
        </div>
      </footer>
    </div>
  );
}
