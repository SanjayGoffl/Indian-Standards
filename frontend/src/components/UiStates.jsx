import React from 'react';

/*
 * Shared loading / error / empty / verification states for the
 * standards pages. Styling lives in pages/StandardsUI.css.
 */

export function LoadingState({ label = 'Loading…', rows = 3 }) {
  return (
    <div className="su-state su-state--loading" role="status" aria-live="polite">
      <div className="su-skeleton-stack" aria-hidden="true">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="su-skeleton" style={{ width: `${92 - i * 14}%` }} />
        ))}
      </div>
      <p className="su-state-label">{label}</p>
    </div>
  );
}

export function ErrorState({ title = 'Something went wrong', error, onRetry, action }) {
  const message = typeof error === 'string' ? error : error?.message;
  const status = typeof error === 'object' ? error?.status : null;

  let hint = null;
  if (status === 401) hint = 'Your session has expired. Sign out and sign in again.';
  else if (status === 403) hint = 'This action requires an Admin account.';
  else if (!status && message && /fetch|network|connect/i.test(message)) {
    hint = 'The backend could not be reached. Check that the FastAPI server is running.';
  }

  return (
    <div className="su-state su-state--error" role="alert">
      <div className="su-state-icon" aria-hidden="true">!</div>
      <h3 className="su-state-title">{title}</h3>
      {message && <p className="su-state-text">{message}{status ? ` (HTTP ${status})` : ''}</p>}
      {hint && <p className="su-state-hint">{hint}</p>}
      <div className="su-state-actions">
        {onRetry && (
          <button type="button" className="su-btn su-btn--secondary" onClick={onRetry}>
            Try again
          </button>
        )}
        {action}
      </div>
    </div>
  );
}

export function EmptyState({ title, text, action }) {
  return (
    <div className="su-state su-state--empty">
      <div className="su-state-icon su-state-icon--muted" aria-hidden="true">∅</div>
      <h3 className="su-state-title">{title}</h3>
      {text && <p className="su-state-text">{text}</p>}
      {action && <div className="su-state-actions">{action}</div>}
    </div>
  );
}

/*
 * Tone mapping for status strings coming from the backend.
 * Unknown values fall back to neutral rather than guessing.
 */
function toneFor(value) {
  const v = String(value || '').toLowerCase();
  if (!v) return 'neutral';
  if (/(^|\s)(failed|error|mismatch|no match|not applicable|withdrawn|superseded)/.test(v)) return 'danger';
  if (/(verification|unverified|not confirmed|potential|pending|required|with_errors|with errors|running|started|unknown)/.test(v)) return 'warn';
  if (/(verified|recommended|confirmed|active|completed|indexed|match|mandatory|high)/.test(v)) return 'ok';
  return 'neutral';
}

export function Badge({ children, tone, title }) {
  const t = tone || toneFor(children);
  return (
    <span className={`su-badge su-badge--${t}`} title={title}>
      {children}
    </span>
  );
}

export function StatTile({ label, value, hint, tone = 'neutral' }) {
  const display = value === null || value === undefined ? '—' : value;
  return (
    <div className={`su-stat su-stat--${tone}`}>
      <div className="su-stat-label">{label}</div>
      <div className="su-stat-value">{typeof display === 'number' ? display.toLocaleString('en-IN') : display}</div>
      {hint && <div className="su-stat-hint">{hint}</div>}
    </div>
  );
}

export function VerificationNotice({ children, title = 'Verification required' }) {
  return (
    <div className="su-notice su-notice--warn">
      <strong>{title}</strong>
      <div>{children}</div>
    </div>
  );
}
