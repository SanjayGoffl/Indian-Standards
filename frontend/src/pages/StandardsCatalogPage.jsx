import React, { useEffect, useState } from 'react';
import * as api from '../services/api';

export default function StandardsCatalogPage() {
  const [standards, setStandards] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [loading, setLoading] = useState(true);
  const [selectedStandard, setSelectedStandard] = useState(null);

  const categories = [
    "Electrical & Cables",
    "Renewable Energy & Solar",
    "Civil & Construction",
    "IT & Electronics",
    "Pipes & Water Management",
    "Water Quality & Environment",
    "Safety Equipment & PPE"
  ];

  useEffect(() => {
    async function fetchStandards() {
      try {
        setLoading(true);
        const data = await api.getIndianStandards(searchTerm, selectedCategory);
        setStandards(data.standards || []);
      } catch (err) {
        console.error("Fetch standards error:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchStandards();
  }, [searchTerm, selectedCategory]);

  const handleViewDetail = async (stdNum) => {
    try {
      const detail = await api.getIndianStandardDetail(stdNum);
      setSelectedStandard(detail);
    } catch (err) {
      console.error("Error fetching detail:", err);
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: '700', color: '#1e293b', margin: 0 }}>
          Indian Standards (BIS) Reference Catalog
        </h1>
        <p style={{ color: '#64748b', fontSize: '0.95rem', marginTop: '6px' }}>
          Browse authentic Indian Standards, specifications, scopes, amendments, and mandatory certification schemes for public procurement.
        </p>
      </div>

      {/* Filter & Search Bar */}
      <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '16px', marginBottom: '24px', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
        <input
          type="text"
          placeholder="Search by IS Code (e.g. IS 694, IS 456), title, or keyword..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{ flex: 1, minWidth: '260px', padding: '10px 14px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.95rem' }}
        />
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          style={{ padding: '10px 14px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.95rem', background: '#ffffff' }}
        >
          <option value="">All Categories / Sectors</option>
          {categories.map((cat, idx) => (
            <option key={idx} value={cat}>{cat}</option>
          ))}
        </select>
      </div>

      {/* Main Grid or Modal */}
      {loading ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>Loading Indian Standards Catalog...</div>
      ) : standards.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', color: '#64748b' }}>
          No Indian Standards found matching query.
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '20px' }}>
          {standards.map((std) => (
            <div key={std.id} style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', boxShadow: '0 2px 6px rgba(0,0,0,0.02)' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                  <span style={{ fontSize: '1.1rem', fontWeight: '800', color: '#1e293b' }}>
                    {std.standard_number}
                  </span>
                  <span style={{ background: '#eff6ff', color: '#2563eb', padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: '600' }}>
                    {std.category}
                  </span>
                </div>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '0.95rem', color: '#0f172a', lineHeight: '1.4' }}>
                  {std.title}
                </h3>
                <p style={{ fontSize: '0.85rem', color: '#475569', lineHeight: '1.4', margin: '0 0 12px 0' }}>
                  {std.scope}
                </p>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '12px' }}>
                  Revision: {std.revision}
                </div>
                <button
                  onClick={() => handleViewDetail(std.standard_number)}
                  style={{ width: '100%', background: '#f1f5f9', color: '#1e293b', border: '1px solid #cbd5e1', padding: '8px', borderRadius: '6px', fontSize: '0.85rem', fontWeight: '600', cursor: 'pointer' }}
                >
                  View Standard Details & Certifications
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Standard Detail Modal */}
      {selectedStandard && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px', zIndex: 1000 }}>
          <div style={{ background: '#ffffff', borderRadius: '12px', padding: '28px', maxWidth: '700px', width: '100%', maxHeight: '90vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
              <div>
                <span style={{ background: '#dcfce7', color: '#15803d', padding: '4px 8px', borderRadius: '4px', fontSize: '0.8rem', fontWeight: '700' }}>
                  {selectedStandard.category}
                </span>
                <h2 style={{ margin: '8px 0 4px 0', fontSize: '1.4rem', color: '#1e293b' }}>
                  {selectedStandard.standard_number}
                </h2>
              </div>
              <button onClick={() => setSelectedStandard(null)} style={{ background: 'none', border: 'none', fontSize: '1.4rem', cursor: 'pointer', color: '#64748b' }}>
                ✕
              </button>
            </div>

            <h3 style={{ margin: '0 0 12px 0', fontSize: '1.05rem', color: '#334155' }}>{selectedStandard.title}</h3>
            
            <div style={{ background: '#f8fafc', padding: '14px', borderRadius: '6px', fontSize: '0.9rem', color: '#475569', marginBottom: '16px' }}>
              <strong>Scope:</strong> {selectedStandard.scope}
            </div>

            {selectedStandard.evidence_text && (
              <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', padding: '12px', borderRadius: '6px', fontSize: '0.85rem', color: '#166534', marginBottom: '16px' }}>
                <strong>Quality Control Order / Gazette Evidence:</strong> {selectedStandard.evidence_text}
              </div>
            )}

            {selectedStandard.certifications && selectedStandard.certifications.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <h4 style={{ margin: '0 0 8px 0', fontSize: '0.95rem', color: '#1e293b' }}>Certification Requirements:</h4>
                {selectedStandard.certifications.map((c, i) => (
                  <div key={i} style={{ background: '#eff6ff', padding: '8px 12px', borderRadius: '6px', fontSize: '0.85rem', marginBottom: '6px', color: '#1e40af' }}>
                    <strong>{c.certification_type}</strong> - {c.applicability} ({c.verification_status})
                  </div>
                ))}
              </div>
            )}

            {selectedStandard.related_standards && selectedStandard.related_standards.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <h4 style={{ margin: '0 0 8px 0', fontSize: '0.95rem', color: '#1e293b' }}>Allied Standards (Test Methods / Normative References):</h4>
                <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.85rem', color: '#334155' }}>
                  {selectedStandard.related_standards.map((r, i) => (
                    <li key={i}>
                      <strong>{r.standard_number}</strong>: {r.title} ({r.relationship_type})
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <button
              onClick={() => setSelectedStandard(null)}
              style={{ width: '100%', marginTop: '16px', background: '#2563eb', color: '#ffffff', border: 'none', padding: '10px', borderRadius: '6px', fontWeight: '600', cursor: 'pointer' }}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
