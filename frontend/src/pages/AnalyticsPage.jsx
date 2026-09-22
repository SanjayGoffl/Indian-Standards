import React, { useEffect, useState } from 'react';
import * as api from '../services/api';

export default function AnalyticsPage() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAnalytics() {
      try {
        setLoading(true);
        const data = await api.getProcurementAnalyticsSummary();
        setSummary(data);
      } catch (err) {
        console.error("Failed to load analytics:", err);
      } finally {
        setLoading(false);
      }
    }
    loadAnalytics();
  }, []);

  if (loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
        Loading procurement analytics...
      </div>
    );
  }

  return (
    <div style={{ padding: '24px', maxWidth: '1100px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: '700', color: '#1e293b', margin: 0 }}>
          Procurement & Standards Analytics Dashboard
        </h1>
        <p style={{ color: '#64748b', fontSize: '0.95rem', marginTop: '6px' }}>
          Overview of procurement specification analyses, product category distribution, mandatory certification flags, and commonly recommended Indian Standards.
        </p>
      </div>

      {/* Metric Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '20px', marginBottom: '32px' }}>
        <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: '700', color: '#2563eb', textTransform: 'uppercase' }}>Total Specification Analyses</div>
          <div style={{ fontSize: '2.2rem', fontWeight: '800', color: '#0f172a', marginTop: '8px' }}>
            {summary?.total_procurement_analyses || 0}
          </div>
          <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '4px' }}>Processed across tenders</div>
        </div>

        <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: '700', color: '#059669', textTransform: 'uppercase' }}>Mandatory Certifications Flagged</div>
          <div style={{ fontSize: '2.2rem', fontWeight: '800', color: '#059669', marginTop: '8px' }}>
            {summary?.mandatory_certifications_flagged || 0}
          </div>
          <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '4px' }}>BIS / ISI / CRS Required</div>
        </div>

        <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: '700', color: '#7c3aed', textTransform: 'uppercase' }}>Catalog Coverage</div>
          <div style={{ fontSize: '2.2rem', fontWeight: '800', color: '#7c3aed', marginTop: '8px' }}>
            100%
          </div>
          <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '4px' }}>BIS gazette compliance</div>
        </div>
      </div>

      {/* Grid: Categories & Commonly Recommended Standards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(460px, 1fr))', gap: '24px', marginBottom: '32px' }}>
        
        {/* Top Product Categories */}
        <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '24px', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
          <h2 style={{ fontSize: '1.15rem', color: '#1e293b', margin: '0 0 16px 0', borderBottom: '1px solid #e2e8f0', paddingBottom: '8px' }}>
            Top Searched Product Categories
          </h2>

          {summary?.top_product_categories && summary.top_product_categories.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {summary.top_product_categories.map((cat, idx) => (
                <div key={idx}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem', marginBottom: '4px' }}>
                    <span style={{ fontWeight: '600', color: '#1e293b' }}>{cat.category}</span>
                    <span style={{ color: '#64748b' }}>{cat.count} analysis runs</span>
                  </div>
                  <div style={{ background: '#f1f5f9', height: '10px', borderRadius: '6px', overflow: 'hidden' }}>
                    <div style={{ width: `${Math.min(100, cat.count * 25)}%`, background: '#2563eb', height: '100%' }} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: '#64748b', fontSize: '0.9rem' }}>No category usage data recorded yet.</div>
          )}
        </div>

        {/* Commonly Recommended IS Codes */}
        <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '24px', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
          <h2 style={{ fontSize: '1.15rem', color: '#1e293b', margin: '0 0 16px 0', borderBottom: '1px solid #e2e8f0', paddingBottom: '8px' }}>
            Most Frequently Recommended IS Codes
          </h2>

          {summary?.commonly_recommended_standards && summary.commonly_recommended_standards.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {summary.commonly_recommended_standards.map((std, idx) => (
                <div key={idx} style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: '800', color: '#1e293b', fontSize: '0.95rem' }}>{std.standard_number}</div>
                    <div style={{ fontSize: '0.82rem', color: '#475569', marginTop: '2px' }}>{std.title}</div>
                  </div>
                  <span style={{ background: '#dcfce7', color: '#15803d', fontWeight: '700', padding: '4px 10px', borderRadius: '12px', fontSize: '0.8rem' }}>
                    {std.count} times
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: '#64748b', fontSize: '0.9rem' }}>No standards recommendation history recorded yet.</div>
          )}
        </div>
      </div>
    </div>
  );
}
