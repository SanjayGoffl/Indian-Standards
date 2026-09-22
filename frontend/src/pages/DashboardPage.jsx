import React, { useEffect, useState } from 'react';
import * as api from '../services/api';

export default function DashboardPage({ onNavigate }) {
  const [summary, setSummary] = useState(null);
  const [recentRequests, setRecentRequests] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboardData() {
      try {
        setLoading(true);
        const [sumData, reqsData] = await Promise.all([
          api.getProcurementAnalyticsSummary().catch(() => null),
          api.getUserProcurementRequests().catch(() => ({ requests: [] }))
        ]);
        setSummary(sumData);
        setRecentRequests(reqsData?.requests || []);
      } catch (err) {
        console.error("Dashboard load error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadDashboardData();
  }, []);

  return (
    <div className="dashboard-container" style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Government Portal Header Banner */}
      <div style={{
        background: 'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)',
        color: '#ffffff',
        padding: '24px 32px',
        borderRadius: '12px',
        marginBottom: '28px',
        boxShadow: '0 8px 24px rgba(30, 60, 114, 0.25)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <span style={{ fontSize: '0.85rem', textTransform: 'uppercase', tracking: '0.05em', background: 'rgba(255,255,255,0.15)', padding: '4px 10px', borderRadius: '4px' }}>
              e-Procurement Technical Standards Engine
            </span>
            <h1 style={{ fontSize: '1.8rem', fontWeight: '700', marginTop: '10px', marginBottom: '6px' }}>
              Indian Standards Recommendation Dashboard
            </h1>
            <p style={{ margin: 0, opacity: 0.9, fontSize: '0.95rem' }}>
              Identify mandatory & applicable BIS (IS) codes, test methods, and certification requirements for tender specifications.
            </p>
          </div>
          <button
            onClick={() => onNavigate('new-recommendation')}
            style={{
              background: '#00c853',
              color: '#ffffff',
              border: 'none',
              padding: '12px 24px',
              borderRadius: '8px',
              fontSize: '1rem',
              fontWeight: '600',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: '0 4px 12px rgba(0,200,83,0.3)',
              transition: 'all 0.2s'
            }}
          >
            <span>+ New Specification Analysis</span>
          </button>
        </div>
      </div>

      {/* KPI Stats Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '20px', marginBottom: '32px' }}>
        <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
          <div style={{ fontSize: '0.85rem', color: '#64748b', fontWeight: '600', textTransform: 'uppercase' }}>Total Analyses</div>
          <div style={{ fontSize: '2.2rem', fontWeight: '800', color: '#1e293b', marginTop: '8px' }}>
            {loading ? '...' : (summary?.total_procurement_analyses || 0)}
          </div>
          <div style={{ fontSize: '0.8rem', color: '#10b981', marginTop: '6px' }}>Specifications processed</div>
        </div>

        <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
          <div style={{ fontSize: '0.85rem', color: '#64748b', fontWeight: '600', textTransform: 'uppercase' }}>Mandatory Certifications</div>
          <div style={{ fontSize: '2.2rem', fontWeight: '800', color: '#0284c7', marginTop: '8px' }}>
            {loading ? '...' : (summary?.mandatory_certifications_flagged || 0)}
          </div>
          <div style={{ fontSize: '0.8rem', color: '#0284c7', marginTop: '6px' }}>BIS / ISI / CRS Flagged</div>
        </div>

        <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
          <div style={{ fontSize: '0.85rem', color: '#64748b', fontWeight: '600', textTransform: 'uppercase' }}>Top Product Category</div>
          <div style={{ fontSize: '1.2rem', fontWeight: '700', color: '#1e293b', marginTop: '12px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {loading ? '...' : (summary?.top_product_categories?.[0]?.category || 'Electrical & Cables')}
          </div>
          <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '6px' }}>Most frequent procurement scope</div>
        </div>

        <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
          <div style={{ fontSize: '0.85rem', color: '#64748b', fontWeight: '600', textTransform: 'uppercase' }}>Knowledge Base Status</div>
          <div style={{ fontSize: '1.2rem', fontWeight: '700', color: '#10b981', marginTop: '12px' }}>
            Active & Verified
          </div>
          <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '6px' }}>Authentic BIS Catalogue Sync</div>
        </div>
      </div>

      {/* Quick Action Navigation */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px', marginBottom: '32px' }}>
        <div 
          onClick={() => onNavigate('new-recommendation')}
          style={{ background: '#ffffff', border: '1px dashed #3b82f6', borderRadius: '10px', padding: '20px', cursor: 'pointer', transition: 'all 0.2s', display: 'flex', alignItems: 'center', gap: '16px' }}
        >
          <div style={{ background: '#eff6ff', color: '#2563eb', padding: '14px', borderRadius: '10px', fontSize: '1.4rem' }}>📝</div>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#1e293b' }}>Analyze Tender / RFP Specs</h3>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: '#64748b' }}>Paste technical text or upload RFP PDFs to get IS standard recommendations.</p>
          </div>
        </div>

        <div 
          onClick={() => onNavigate('standards')}
          style={{ background: '#ffffff', border: '1px dashed #10b981', borderRadius: '10px', padding: '20px', cursor: 'pointer', transition: 'all 0.2s', display: 'flex', alignItems: 'center', gap: '16px' }}
        >
          <div style={{ background: '#ecfdf5', color: '#059669', padding: '14px', borderRadius: '10px', fontSize: '1.4rem' }}>📚</div>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#1e293b' }}>Browse BIS Standards Catalog</h3>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: '#64748b' }}>Search official Indian Standards, scopes, amendments, and test codes.</p>
          </div>
        </div>
      </div>

      {/* Recent Procurement Analyses */}
      <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '24px', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '1.2rem', fontWeight: '700', color: '#1e293b', margin: 0 }}>Recent Specification Analyses</h2>
          <button onClick={() => onNavigate('history')} style={{ background: 'none', border: 'none', color: '#2563eb', fontWeight: '600', cursor: 'pointer', fontSize: '0.9rem' }}>
            View All History →
          </button>
        </div>

        {loading ? (
          <div style={{ padding: '20px', textAlign: 'center', color: '#64748b' }}>Loading recent analyses...</div>
        ) : recentRequests.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: '#64748b', background: '#f8fafc', borderRadius: '8px' }}>
            <p style={{ margin: 0, fontSize: '1rem' }}>No procurement analyses conducted yet.</p>
            <button 
              onClick={() => onNavigate('new-recommendation')}
              style={{ marginTop: '12px', background: '#2563eb', color: '#ffffff', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer' }}
            >
              Start Your First Analysis
            </button>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
              <thead>
                <tr style={{ background: '#f8fafc', borderBottom: '2px solid #e2e8f0', color: '#475569' }}>
                  <th style={{ padding: '12px 16px' }}>Date</th>
                  <th style={{ padding: '12px 16px' }}>Product Category</th>
                  <th style={{ padding: '12px 16px' }}>Summary</th>
                  <th style={{ padding: '12px 16px' }}>Recommended IS Codes</th>
                  <th style={{ padding: '12px 16px' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {recentRequests.slice(0, 5).map((req) => (
                  <tr key={req.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '14px 16px', color: '#64748b', whiteSpace: 'nowrap' }}>
                      {req.created_at ? new Date(req.created_at).toLocaleDateString() : 'Recent'}
                    </td>
                    <td style={{ padding: '14px 16px', fontWeight: '600', color: '#1e293b' }}>
                      <span style={{ background: '#eff6ff', color: '#1d4ed8', padding: '4px 8px', borderRadius: '4px', fontSize: '0.8rem' }}>
                        {req.product_category || 'General'}
                      </span>
                    </td>
                    <td style={{ padding: '14px 16px', color: '#334155', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {req.summary}
                    </td>
                    <td style={{ padding: '14px 16px', fontWeight: '600', color: '#059669' }}>
                      {req.recommended_count} Standard(s)
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      <button
                        onClick={() => onNavigate('results', req.id)}
                        style={{ background: '#2563eb', color: '#ffffff', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem' }}
                      >
                        View Report
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
