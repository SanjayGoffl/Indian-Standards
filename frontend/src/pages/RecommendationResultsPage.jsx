import React, { useEffect, useState } from 'react';
import * as api from '../services/api';

export default function RecommendationResultsPage({ requestId, onBack }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function loadReport() {
      if (!requestId) return;
      try {
        setLoading(true);
        const data = await api.getProcurementRequestDetail(requestId);
        setReport(data);
      } catch (err) {
        console.error("Load report error:", err);
        setError("Failed to load recommendation report details.");
      } finally {
        setLoading(false);
      }
    }
    loadReport();
  }, [requestId]);

  const handlePrint = () => {
    window.print();
  };

  if (loading) {
    return (
      <div style={{ padding: '60px', textAlign: 'center', color: '#64748b' }}>
        <div style={{ fontSize: '2rem', marginBottom: '12px' }}>📊</div>
        <div>Generating evidence-based recommendation report...</div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div style={{ padding: '40px', maxWidth: '800px', margin: '0 auto', textAlign: 'center' }}>
        <div style={{ color: '#ef4444', fontSize: '1.2rem', fontWeight: '700', marginBottom: '16px' }}>{error || 'Report unavailable'}</div>
        <button onClick={onBack} style={{ background: '#2563eb', color: '#ffffff', border: 'none', padding: '10px 20px', borderRadius: '6px', cursor: 'pointer' }}>
          ← Back to Dashboard
        </button>
      </div>
    );
  }

  const getStatusBadgeStyle = (status) => {
    switch (status) {
      case 'Recommended':
      case 'Analysis Validated':
        return { background: '#dcfce7', color: '#15803d', border: '1px solid #86efac' };
      case 'Potentially Applicable':
      case 'Analysis Completed – Verification Required':
      case 'Analysis Completed - Verification Required':
        return { background: '#fef3c7', color: '#b45309', border: '1px solid #fde68a' };
      case 'No Applicable Standard Confirmed':
      case 'No Directly Applicable Standard Confirmed - Manual Verification Required':
        return { background: '#fff7ed', color: '#c2410c', border: '1px solid #fed7aa' };
      default:
        return { background: '#fee2e2', color: '#b91c1c', border: '1px solid #fca5a5' };
    }
  };

  const getNoMatchBulletPoints = (productCategory) => {
    const cat = (productCategory || '').toLowerCase();
    if (cat.includes('glove') || cat.includes('hand protection')) {
      return [
        "Glove material (e.g. nitrile, neoprene, latex, PVC)",
        "Specific chemicals and concentration levels",
        "Required protection duration and breakthrough time",
        "Glove thickness and cuff length",
        "Applicable test methods (e.g. EN 388, EN ISO 374)",
        "Required certification and safety standards",
        "Intended working conditions and laboratory environment"
      ];
    } else if (cat.includes('cable') || cat.includes('wire') || cat.includes('electrical')) {
      return [
        "Conductor material (Copper / Aluminium)",
        "Insulation material (PVC / XLPE)",
        "Working voltage rating (e.g. 1100 V)",
        "FRLS / LSZH specification",
        "Sheath material and thickness",
        "Applicable test methods and standards"
      ];
    } else if (cat.includes('insulation') || cat.includes('thermal') || cat.includes('turbine')) {
      return [
        "Material composition (ceramic fiber, mineral wool, silica)",
        "Maximum operating temperature (°C)",
        "Thermal conductivity (W/m·K) requirement",
        "Thickness and density specifications",
        "Applicable test methods and standards"
      ];
    } else if (cat.includes('pipe') || cat.includes('hdpe')) {
      return [
        "HDPE pipe material grade (PE 63, PE 80, PE 100)",
        "Nominal outer diameter and pressure rating (PN rating)",
        "Fluid transported and temperature limits",
        "Applicable test methods and standards"
      ];
    } else if (cat.includes('helmet')) {
      return [
        "Helmet shell material (HDPE, ABS, Fiberglass)",
        "Impact resistance and penetration resistance specifications",
        "Electrical insulation rating",
        "Applicable test methods and standards"
      ];
    } else {
      return [
        "Specific material grade or composition",
        "Dimensional tolerances and thickness specifications",
        "Operating temperature and environmental exposure limits",
        "Applicable mechanical or physical test requirements",
        "Required certification or purchaser specification"
      ];
    }
  };

  return (
    <div className="recommendation-report" style={{ padding: '24px', maxWidth: '1100px', margin: '0 auto' }}>
      {/* Printable Header Branding */}
      <div className="print-only-branding" style={{ display: 'none', marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '2px solid #0f172a', paddingBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: '36px', height: '36px', background: '#0f172a', color: '#ffffff', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', fontSize: '1.2rem' }}>
              🇮🇳
            </div>
            <div>
              <div style={{ fontSize: '1.15rem', fontWeight: '800', color: '#0f172a', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                IS Procurement AI Engine
              </div>
              <div style={{ fontSize: '0.75rem', color: '#475569', fontWeight: '600' }}>
                BIS Standards Applicability & Technical Evaluation Report
              </div>
            </div>
          </div>
          <div style={{ textAlign: 'right', fontSize: '0.8rem', color: '#475569' }}>
            <div><strong>Official Technical Report</strong></div>
            <div>Ref: {report.request_id || 'REF-BIS-SPEC-001'}</div>
          </div>
        </div>
      </div>

      {/* Action Header */}
      <div className="no-print" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <button
          onClick={onBack}
          className="back-button"
          style={{ background: '#f1f5f9', color: '#334155', border: '1px solid #cbd5e1', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', fontWeight: '600' }}
        >
          ← Back to History
        </button>
        <button
          onClick={handlePrint}
          className="print-button"
          style={{ background: '#1e293b', color: '#ffffff', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          🖨️ Export PDF / Print Report
        </button>
      </div>

      {/* Official Banner Header */}
      <div className="report-header-banner" style={{ background: '#1e293b', color: '#ffffff', padding: '24px', borderRadius: '12px 12px 0 0' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', background: 'rgba(255,255,255,0.15)', padding: '4px 8px', borderRadius: '4px' }}>
              Evidence-Based Technical Evaluation
            </span>
            <h1 className="report-section-title" style={{ fontSize: '1.6rem', fontWeight: '800', marginTop: '8px', margin: '8px 0 4px 0' }}>
              Indian Standards Recommendation & Validation Report
            </h1>
            <p style={{ margin: 0, opacity: 0.85, fontSize: '0.9rem' }}>
              Procurement Domain: <strong style={{ color: '#38bdf8' }}>{report.product_category || 'General Procurement'}</strong>
              {report.product_type && report.product_type !== report.product_category && (
                <> | Product Type: <strong style={{ color: '#38bdf8' }}>{report.product_type}</strong></>
              )}
              | Generated: {report.created_at ? new Date(report.created_at).toLocaleDateString() : 'Today'}
            </p>
          </div>
          <div style={{ textAlign: 'right' }}>
            <span style={{
              padding: '6px 14px',
              borderRadius: '20px',
              fontSize: '0.85rem',
              fontWeight: '700',
              ...getStatusBadgeStyle(report.overall_status)
            }}>
              {report.overall_status || 'Analysis Completed – Verification Required'}
            </span>
          </div>
        </div>
      </div>

      {/* Report Body */}
      <div className="report-body-container" style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderTop: 'none', borderRadius: '0 0 12px 12px', padding: '28px', boxShadow: '0 4px 16px rgba(0,0,0,0.04)' }}>
        
        {/* Zero Match / Manual Verification Notice Banner */}
        {report.notice && (
          <div className="report-banner report-card" style={{ background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: '8px', padding: '16px 20px', marginBottom: '24px', color: '#c2410c', fontSize: '0.95rem', fontWeight: '700', display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            <span style={{ fontSize: '1.3rem' }}>⚠️</span>
            <div>
              <div className="report-section-title" style={{ fontSize: '1rem', fontWeight: '800', marginBottom: '4px' }}>
                No Directly Applicable Standard Confirmed
              </div>
              <div style={{ fontSize: '0.9rem', fontWeight: '500', lineHeight: '1.5' }}>
                {report.notice}
              </div>
            </div>
          </div>
        )}

        {/* Mandatory Internal AI Score Disclaimer */}
        <div className="disclaimer-box report-card" style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: '8px', padding: '14px 18px', marginBottom: '24px', color: '#1e40af', fontSize: '0.85rem', display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
          <span style={{ fontSize: '1.2rem' }}>ℹ️</span>
          <div>
            <strong>AI Retrieval Match Score Notice:</strong>
            <div style={{ marginTop: '2px', lineHeight: '1.4' }}>
              {report.disclaimer || "This score is an internal semantic retrieval indicator. It does not represent official BIS approval, compliance, certification, legal validity, or applicability."}
            </div>
          </div>
        </div>

        {/* Section 1: Procurement Summary */}
        <div className="report-section report-card" style={{ marginBottom: '28px', background: '#f8fafc', borderLeft: '4px solid #2563eb', padding: '16px 20px', borderRadius: '4px' }}>
          <h3 className="report-section-title" style={{ margin: '0 0 8px 0', fontSize: '1.05rem', color: '#1e293b' }}>1. Procurement Requirement Summary</h3>
          <p style={{ margin: 0, color: '#334155', fontSize: '0.95rem', lineHeight: '1.5' }}>
            {report.procurement_summary}
          </p>
        </div>

        {/* Section 2: Missing Technical Information */}
        <div className="report-section report-card" style={{ marginBottom: '28px', background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: '8px', padding: '18px 20px' }}>
          <h3 className="report-section-title" style={{ margin: '0 0 10px 0', fontSize: '1.05rem', color: '#c2410c', fontWeight: '700' }}>
            2. Missing Technical Information Required for Accurate Standards Matching
          </h3>
          {report.missing_requirements && report.missing_requirements.length > 0 ? (
            <ul style={{ margin: 0, paddingLeft: '20px', color: '#9a3412', fontSize: '0.88rem', lineHeight: '1.6' }}>
              {report.missing_requirements.map((item, mIdx) => (
                <li key={mIdx}>{item}</li>
              ))}
            </ul>
          ) : (
            <p style={{ margin: 0, color: '#9a3412', fontSize: '0.88rem' }}>
              No critical technical information is missing based on the provided input.
            </p>
          )}
        </div>

        {/* Section 3: Extracted Technical Requirements */}
        {report.extracted_requirements && report.extracted_requirements.length > 0 && (
          <div className="report-section" style={{ marginBottom: '32px' }}>
            <h3 className="report-section-title" style={{ fontSize: '1.1rem', color: '#1e293b', marginBottom: '14px', borderBottom: '2px solid #e2e8f0', paddingBottom: '6px' }}>
              3. Extracted Technical Requirements
            </h3>
            <div className="extracted-reqs-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px' }}>
              {report.extracted_requirements.map((req, idx) => (
                <div key={idx} className="report-card" style={{ background: '#f1f5f9', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '12px 16px' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: '700', color: '#2563eb', textTransform: 'uppercase' }}>
                    {req.category}
                  </div>
                  <div style={{ fontWeight: '700', color: '#0f172a', fontSize: '0.95rem', marginTop: '2px' }}>
                    {req.parameter}
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#475569', marginTop: '4px' }}>
                    <span style={{ background: '#ffffff', padding: '2px 6px', borderRadius: '4px', border: '1px solid #cbd5e1' }}>
                      {req.value_spec}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section 4: Recommended & Potentially Applicable Standards */}
        <div className="report-section" style={{ marginBottom: '36px' }}>
          <h3 className="report-section-title" style={{ fontSize: '1.1rem', color: '#1e293b', marginBottom: '16px', borderBottom: '2px solid #e2e8f0', paddingBottom: '8px' }}>
            4. Recommended & Potentially Applicable Standards
          </h3>

          {((report.recommended_standards && report.recommended_standards.length > 0) ||
            (report.potentially_applicable_standards && report.potentially_applicable_standards.length > 0)) ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              {[...(report.recommended_standards || []), ...(report.potentially_applicable_standards || [])].map((std, idx) => {
                const badgeStyle = getStatusBadgeStyle(std.applicability_status);
                const scoreVal = std.internal_match_score !== undefined && std.internal_match_score !== null
                  ? std.internal_match_score
                  : (std.relevance_score ? (std.relevance_score / 100.0) : 0.75);

                return (
                  <div key={idx} className="report-card" style={{ border: '1px solid #cbd5e1', borderRadius: '10px', overflow: 'hidden', background: '#ffffff', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
                    
                    {/* Card Header */}
                    <div style={{ background: '#f8fafc', padding: '16px 20px', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '1.2rem', fontWeight: '800', color: '#1e293b' }}>
                          {std.standard_number}
                        </span>
                        <span style={{ fontSize: '0.8rem', fontWeight: '700', padding: '4px 10px', borderRadius: '12px', ...badgeStyle }}>
                          {std.applicability_status}
                        </span>
                        {std.revision_verification_status && (
                          <span style={{ fontSize: '0.75rem', padding: '2px 8px', borderRadius: '4px', background: std.revision_verification_status === 'Verified' ? '#dcfce7' : '#fff7ed', color: std.revision_verification_status === 'Verified' ? '#15803d' : '#c2410c', border: std.revision_verification_status === 'Verified' ? '1px solid #86efac' : '1px solid #fed7aa', fontWeight: '600' }}>
                            Revision: {std.revision_verification_status}
                          </span>
                        )}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: '#ffffff', border: '1px solid #e2e8f0', padding: '6px 12px', borderRadius: '8px' }}>
                        <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Internal Match Score:</span>
                        <span style={{ fontWeight: '800', fontSize: '0.9rem', color: '#2563eb' }}>{scoreVal.toFixed(2)}</span>
                        <span style={{ fontSize: '0.75rem', background: scoreVal >= 0.8 ? '#dcfce7' : (scoreVal >= 0.5 ? '#eff6ff' : '#fef3c7'), color: scoreVal >= 0.8 ? '#15803d' : (scoreVal >= 0.5 ? '#1d4ed8' : '#b45309'), padding: '2px 6px', borderRadius: '4px', fontWeight: '600' }}>
                          {std.match_strength || 'Medium'} Match
                        </span>
                      </div>
                    </div>

                    {/* Card Body */}
                    <div style={{ padding: '20px' }}>
                      <h4 className="report-section-title" style={{ margin: '0 0 10px 0', fontSize: '1.05rem', color: '#0f172a' }}>
                        {std.title}
                      </h4>
                      <p style={{ fontSize: '0.9rem', color: '#334155', lineHeight: '1.5', margin: '0 0 16px 0' }}>
                        <strong>Scope:</strong> {std.scope || 'Covers general product requirements and testing.'}
                      </p>

                      <div style={{ background: '#f8fafc', borderLeft: '3px solid #3b82f6', padding: '12px 16px', borderRadius: '4px', marginBottom: '16px', fontSize: '0.9rem', color: '#1e293b' }}>
                        <strong>Applicability Evaluation:</strong> {std.reasoning}
                      </div>

                      {/* Field Comparison Matrix Table */}
                      {std.field_comparison_matrix && std.field_comparison_matrix.length > 0 && (
                        <div style={{ marginBottom: '16px' }}>
                          <div style={{ fontSize: '0.85rem', fontWeight: '700', color: '#475569', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                            📋 Field Comparison Matrix (Requirement vs Provision)
                          </div>
                          <table className="field-matrix-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', border: '1px solid #e2e8f0', borderRadius: '6px', overflow: 'hidden' }}>
                            <thead>
                              <tr style={{ background: '#f1f5f9', color: '#334155', textAlign: 'left' }}>
                                <th className="matrix-col-param" style={{ padding: '8px 12px', borderBottom: '1px solid #cbd5e1' }}>Parameter</th>
                                <th className="matrix-col-spec" style={{ padding: '8px 12px', borderBottom: '1px solid #cbd5e1' }}>Extracted Spec</th>
                                <th className="matrix-col-prov" style={{ padding: '8px 12px', borderBottom: '1px solid #cbd5e1' }}>Standard Provision</th>
                                <th className="matrix-col-res" style={{ padding: '8px 12px', borderBottom: '1px solid #cbd5e1' }}>Result</th>
                              </tr>
                            </thead>
                            <tbody>
                              {std.field_comparison_matrix.map((matrixItem, mIdx) => {
                                const isMatch = matrixItem.result === 'Match';
                                const isMismatch = matrixItem.result === 'Mismatch' || matrixItem.result === 'No Match';
                                const rowBg = isMatch ? '#f0fdf4' : (isMismatch ? '#fef2f2' : '#ffffff');
                                const badgeBg = isMatch ? '#dcfce7' : (isMismatch ? '#fee2e2' : '#f1f5f9');
                                const badgeColor = isMatch ? '#15803d' : (isMismatch ? '#b91c1c' : '#475569');

                                return (
                                  <tr key={mIdx} style={{ background: rowBg, borderBottom: '1px solid #f1f5f9' }}>
                                    <td className="matrix-col-param" style={{ padding: '8px 12px', fontWeight: '600', color: '#1e293b' }}>{matrixItem.parameter}</td>
                                    <td className="matrix-col-spec" style={{ padding: '8px 12px', color: '#334155' }}>{matrixItem.required_value}</td>
                                    <td className="matrix-col-prov" style={{ padding: '8px 12px', color: '#334155' }}>{matrixItem.standard_provision}</td>
                                    <td className="matrix-col-res" style={{ padding: '8px 12px' }}>
                                      <span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: '700', background: badgeBg, color: badgeColor }}>
                                        {matrixItem.result}
                                      </span>
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      )}

                      {/* Revision Status */}
                      <div style={{ background: '#fff7ed', border: '1px solid #fed7aa', padding: '10px 14px', borderRadius: '6px', fontSize: '0.85rem', color: '#c2410c' }}>
                        <strong>Revision Status:</strong> {std.latest_revision || 'Revision status requires verification from the official BIS standards catalogue.'}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="report-card" style={{ padding: '20px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.95rem', fontWeight: '700', color: '#334155', marginBottom: '8px' }}>
                No potentially applicable Indian Standards matched this specification.
              </div>
              <p style={{ margin: '0 0 10px 0', fontSize: '0.88rem', color: '#475569', lineHeight: '1.5' }}>
                No potentially applicable Indian Standards were identified from the available standards database for this procurement description.
              </p>
              <p style={{ margin: '0 0 12px 0', fontSize: '0.85rem', color: '#64748b', lineHeight: '1.5', fontStyle: 'italic' }}>
                This does not mean that no standard exists. The result indicates that no technically relevant standard was confirmed using the available catalogue and extracted requirements.
              </p>
              <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: '6px', padding: '12px 16px', fontSize: '0.85rem', color: '#334155' }}>
                <strong>Further verification is recommended after providing:</strong>
                <ul style={{ margin: '6px 0 0 0', paddingLeft: '20px', lineHeight: '1.6', color: '#475569' }}>
                  {getNoMatchBulletPoints(report.product_category).map((bItem, bIdx) => (
                    <li key={bIdx}>{bItem}</li>
                  ))}
                </ul>
              </div>
              <div style={{ marginTop: '14px', fontSize: '0.8rem', color: '#94a3b8', fontStyle: 'italic' }}>
                No field comparison matrix is available because no technically applicable standard was identified.
              </div>
            </div>
          )}
        </div>

        {/* Section 5: Standards Requiring Official Verification */}
        <div className="report-section" style={{ marginBottom: '32px' }}>
          <h3 className="report-section-title" style={{ fontSize: '1.1rem', color: '#b45309', marginBottom: '14px', borderBottom: '2px solid #fde68a', paddingBottom: '6px' }}>
            5. Standards Requiring Official Verification
          </h3>
          {report.standards_requiring_verification && report.standards_requiring_verification.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {report.standards_requiring_verification.map((vItem, vIdx) => (
                <div key={vIdx} className="report-card" style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '8px', padding: '14px 18px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                    <span style={{ fontWeight: '800', color: '#92400e', fontSize: '1rem' }}>
                      {vItem.standard_number}
                    </span>
                    <span style={{ background: '#fef3c7', color: '#92400e', padding: '3px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: '700', border: '1px solid #fde68a' }}>
                      Status: {vItem.verification_status || 'Verification Required'}
                    </span>
                  </div>
                  <div style={{ color: '#1e293b', fontWeight: '600', marginTop: '4px', fontSize: '0.9rem' }}>
                    {vItem.title}
                  </div>
                  <div style={{ marginTop: '8px', fontSize: '0.8rem' }}>
                    <a href={vItem.source_url || `https://www.bis.gov.in/index.php/standard-search/?std_no=${vItem.standard_number}`} target="_blank" rel="noopener noreferrer" style={{ color: '#2563eb', fontWeight: '600', textDecoration: 'underline' }}>
                      Official BIS Standard Catalogue Verification Link ↗
                    </a>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="report-card" style={{ padding: '16px', background: '#f8fafc', border: '1px solid #e2e8f0', color: '#475569', borderRadius: '6px', fontSize: '0.9rem' }}>
              No standards require official verification based on the current analysis.
            </div>
          )}
        </div>

        {/* Section 6: Excluded or Not Applicable Standards */}
        <div className="report-section" style={{ marginBottom: '32px' }}>
          <h3 className="report-section-title" style={{ fontSize: '1.1rem', color: '#991b1b', marginBottom: '14px', borderBottom: '2px solid #fee2e2', paddingBottom: '6px' }}>
            6. Excluded or Not Applicable Standards
          </h3>
          {report.excluded_standards && report.excluded_standards.length > 0 ? (
            <div className="excluded-standards-container" style={{ background: '#fff5f5', border: '1px solid #fed7d7', borderRadius: '8px', padding: '16px' }}>
              <p style={{ margin: '0 0 12px 0', fontSize: '0.85rem', color: '#7f1d1d' }}>
                The following candidate standards were retrieved by vector search but <strong>excluded</strong> due to product domain or technical parameter mismatches:
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {report.excluded_standards.map((ex, eIdx) => (
                  <div key={eIdx} className="report-card" style={{ background: '#ffffff', border: '1px solid #fca5a5', padding: '10px 14px', borderRadius: '6px', fontSize: '0.85rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: '700', color: '#991b1b' }}>{ex.standard_number}</span>
                      <span style={{ background: '#fee2e2', color: '#991b1b', padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: '600' }}>
                        Category: {ex.category}
                      </span>
                    </div>
                    <div style={{ color: '#334155', fontWeight: '600', marginTop: '2px' }}>{ex.title}</div>
                    <div style={{ color: '#991b1b', fontSize: '0.8rem', marginTop: '4px' }}>
                      <strong>Exclusion Reason:</strong> {ex.exclusion_reason}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="report-card" style={{ padding: '16px', background: '#f8fafc', border: '1px solid #e2e8f0', color: '#475569', borderRadius: '6px', fontSize: '0.9rem' }}>
              No candidate standards were excluded for this procurement requirement.
            </div>
          )}
        </div>

        {/* Section 7: Certification and Regulatory Guidance */}
        <div className="report-section" style={{ marginBottom: '32px' }}>
          <h3 className="report-section-title" style={{ fontSize: '1.1rem', color: '#1e293b', marginBottom: '14px', borderBottom: '2px solid #e2e8f0', paddingBottom: '6px' }}>
            7. Certification and Regulatory Guidance
          </h3>

          {report.certification_guidance && report.certification_guidance.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {report.certification_guidance.map((cert, cIdx) => (
                <div key={cIdx} className="report-card" style={{ background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '8px', padding: '14px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                    <span style={{ fontWeight: '700', color: '#1e293b', fontSize: '0.95rem' }}>
                      {cert.certification_type}
                    </span>
                    <span style={{ background: cert.applicability === 'Confirmed Applicable' ? '#dcfce7' : '#fef3c7', color: cert.applicability === 'Confirmed Applicable' ? '#15803d' : '#b45309', padding: '3px 8px', borderRadius: '4px', fontSize: '0.8rem', fontWeight: '700' }}>
                      Status: {cert.applicability}
                    </span>
                  </div>
                  <p style={{ margin: '8px 0 0 0', fontSize: '0.85rem', color: '#475569', lineHeight: '1.4' }}>
                    {cert.evidence_text || cert.verification_status}
                  </p>
                  {cert.source_url && (
                    <div className="no-print" style={{ marginTop: '8px' }}>
                      <a href={cert.source_url} target="_blank" rel="noopener noreferrer" style={{ color: '#2563eb', fontSize: '0.8rem', textDecoration: 'underline' }}>
                        Official Source / Gazette Link ↗
                      </a>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="report-card" style={{ padding: '16px', background: '#fff7ed', border: '1px solid #fed7aa', color: '#c2410c', borderRadius: '6px', fontSize: '0.85rem' }}>
              Certification applicability could not be confirmed. Please verify the latest applicable BIS notification or Quality Control Order from the official authority.
            </div>
          )}
        </div>

        {/* Section 8: Legal Disclaimer & Verification Notice */}
        <div className="disclaimer-box report-card" style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', padding: '16px', color: '#991b1b', fontSize: '0.85rem' }}>
          <h3 className="report-section-title" style={{ margin: '0 0 6px 0', fontSize: '1rem', color: '#991b1b', fontWeight: '800' }}>
            8. Legal Disclaimer & Verification Notice
          </h3>
          <ul style={{ margin: '6px 0 0 0', paddingLeft: '20px', lineHeight: '1.5' }}>
            <li>The internal match score is an AI retrieval indicator and does not constitute official BIS compliance or certification.</li>
            <li>Where exact revision dates or Quality Control Orders are unconfirmed in local records, manual verification from the official BIS portal (www.bis.gov.in) is required prior to tender publication.</li>
          </ul>
        </div>

        {/* Printable Footer */}
        <div className="print-footer" style={{ display: 'none' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>Generated by <strong>IS Procurement AI Engine</strong></div>
            <div>Date: {report.created_at ? new Date(report.created_at).toLocaleDateString() : new Date().toLocaleDateString()}</div>
            <div>AI-generated analysis requires official verification.</div>
          </div>
        </div>

      </div>
    </div>
  );
}

