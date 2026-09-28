import React from 'react';

const fmtDateTime = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
};

export default function RequestsTable({ requests, onOpen, onDelete, deletingId }) {
  return (
    <div className="su-table-wrap">
      <table className="su-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Category</th>
            <th>Specification summary</th>
            <th className="su-num">IS codes</th>
            {onDelete && <th aria-label="Actions" />}
          </tr>
        </thead>
        <tbody>
          {requests.map((req) => (
            <tr
              key={req.id}
              className="su-row-clickable"
              onClick={() => onOpen(req.id)}
              onKeyDown={(e) => { if (e.key === 'Enter') onOpen(req.id); }}
              tabIndex={0}
              title="Open report"
            >
              <td style={{ whiteSpace: 'nowrap' }}>{fmtDateTime(req.created_at)}</td>
              <td style={{ whiteSpace: 'nowrap', color: 'var(--text-primary)', fontWeight: 500 }}>{req.product_category || '—'}</td>
              <td>
                <div className="su-truncate-2">{req.summary || '—'}</div>
                {req.procurement_purpose && <div className="su-muted" style={{ fontSize: '0.78rem', marginTop: 2 }}>Purpose: {req.procurement_purpose}</div>}
              </td>
              <td className="su-num">{req.recommended_count ?? 0}</td>
              {onDelete && (
                <td style={{ width: 1, whiteSpace: 'nowrap' }}>
                  <button
                    type="button"
                    className="su-btn su-btn--ghost"
                    style={{ color: 'var(--accent-rose)' }}
                    disabled={deletingId === req.id}
                    onClick={(e) => { e.stopPropagation(); onDelete(req); }}
                  >
                    {deletingId === req.id ? 'Deleting…' : 'Delete'}
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
