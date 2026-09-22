import React, { useState, useEffect } from 'react';
import * as api from '../services/api';

export default function HistoryPage({ onViewReport }) {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState('');

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const data = await api.getUserProcurementRequests();
      setRequests(data.requests || []);
    } catch (err) {
      console.error("Fetch history error:", err);
      setError("Failed to load procurement analysis history.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleDelete = async (requestId, e) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this procurement analysis record?")) return;
    try {
      await api.deleteProcurementRequest(requestId);
      setRequests((prev) => prev.filter((r) => r.id !== requestId));
    } catch (err) {
      alert("Failed to delete record: " + err.message);
    }
  };

  const filteredRequests = requests.filter((r) => {
    const term = searchTerm.toLowerCase();
    return (
      (r.product_category || '').toLowerCase().includes(term) ||
      (r.summary || '').toLowerCase().includes(term) ||
      (r.procurement_purpose || '').toLowerCase().includes(term)
    );
  });

  return (
    <div style={{ padding: '24px', maxWidth: '1100px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: '700', color: '#1e293b', margin: 0 }}>
          Procurement Specification History
        </h1>
        <p style={{ color: '#64748b', fontSize: '0.95rem', marginTop: '6px' }}>
          View, review, or delete past Indian Standards recommendation reports and technical analyses.
        </p>
      </div>

      {/* Search Bar */}
      <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '16px', marginBottom: '24px' }}>
        <input
          type="text"
          placeholder="Filter history by category, purpose, or keyword..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{ width: '100%', padding: '10px 14px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.95rem', boxSizing: 'border-box' }}
        />
      </div>

      {loading ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>Loading specification history...</div>
      ) : filteredRequests.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', color: '#64748b' }}>
          No procurement history matching filter.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {filteredRequests.map((req) => (
            <div
              key={req.id}
              onClick={() => onViewReport(req.id)}
              style={{
                background: '#ffffff',
                border: '1px solid #e2e8f0',
                borderRadius: '10px',
                padding: '20px',
                cursor: 'pointer',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '16px',
                transition: 'all 0.2s',
                boxShadow: '0 2px 6px rgba(0,0,0,0.02)'
              }}
            >
              <div style={{ flex: 1, minWidth: '280px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                  <span style={{ background: '#eff6ff', color: '#1d4ed8', fontWeight: '700', padding: '3px 8px', borderRadius: '4px', fontSize: '0.8rem' }}>
                    {req.product_category || 'General Procurement'}
                  </span>
                  <span style={{ fontSize: '0.8rem', color: '#64748b' }}>
                    {req.created_at ? new Date(req.created_at).toLocaleString() : ''}
                  </span>
                </div>
                <h3 style={{ margin: '0 0 6px 0', fontSize: '1.05rem', color: '#0f172a' }}>
                  {req.summary}
                </h3>
                {req.procurement_purpose && (
                  <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
                    Purpose: {req.procurement_purpose}
                  </div>
                )}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ background: '#dcfce7', color: '#15803d', padding: '6px 12px', borderRadius: '20px', fontSize: '0.8rem', fontWeight: '700' }}>
                  {req.recommended_count} IS Code(s)
                </span>
                <button
                  onClick={(e) => handleDelete(req.id, e)}
                  style={{ background: '#fef2f2', color: '#ef4444', border: '1px solid #fca5a5', padding: '6px 10px', borderRadius: '6px', fontSize: '0.8rem', cursor: 'pointer' }}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}