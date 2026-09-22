import React, { useState } from 'react';
import * as api from '../services/api';

export default function NewRecommendationPage({ onAnalysisComplete }) {
  const [productCategory, setProductCategory] = useState('');
  const [procurementPurpose, setProcurementPurpose] = useState('');
  const [technicalSpecs, setTechnicalSpecs] = useState('');
  const [targetLanguage, setTargetLanguage] = useState('en');
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progressMessage, setProgressMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  const sampleCategories = [
    "Electrical Wires & Power Cables",
    "Solar PV Modules & Inverters",
    "Reinforcement Steel & Concrete",
    "Water Supply Pipes & Valves",
    "IT Equipment & Hardware",
    "Industrial Safety Helmets & PPE",
    "Drinking Water Purification Systems"
  ];

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');

    if (!technicalSpecs.trim() && !selectedFile) {
      setErrorMessage("Please enter technical specifications text or upload an RFP/tender document.");
      return;
    }

    try {
      setLoading(true);
      setProgressMessage("Extracting technical parameters & running OCR if needed...");

      const formData = new FormData();
      if (productCategory) formData.append('product_category', productCategory);
      if (procurementPurpose) formData.append('procurement_purpose', procurementPurpose);
      if (technicalSpecs) formData.append('technical_specifications', technicalSpecs);
      if (selectedFile) formData.append('file', selectedFile);

      setTimeout(() => {
        setProgressMessage("Performing hybrid semantic search against Indian Standards database...");
      }, 2000);

      setTimeout(() => {
        setProgressMessage("Evaluating applicability, checking revisions, & resolving BIS/CRS certifications...");
      }, 4000);

      const result = await api.analyzeProcurementSpecification(formData);
      onAnalysisComplete(result.request_id || result);

    } catch (err) {
      console.error("Procurement analysis error:", err);
      if (api.isUnauthorizedError(err) || err.status === 401) {
        setErrorMessage("Your session has expired or authentication is invalid. Please log out and log in again to analyze specifications.");
      } else {
        setErrorMessage(err.message || "Failed to analyze procurement specification. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '960px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: '700', color: '#1e293b', margin: 0 }}>
          New Procurement Specification Analysis
        </h1>
        <p style={{ color: '#64748b', fontSize: '0.95rem', marginTop: '6px' }}>
          Enter product requirements or upload tender specifications (PDF, DOCX, TXT, scanned images) to identify mandatory & applicable Indian Standards (IS).
        </p>
      </div>

      {errorMessage && (
        <div style={{ background: '#fef2f2', border: '1px solid #fca5a5', color: '#991b1b', padding: '14px', borderRadius: '8px', marginBottom: '20px', fontSize: '0.9rem' }}>
          ⚠️ {errorMessage}
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '28px', boxShadow: '0 2px 10px rgba(0,0,0,0.03)' }}>
        {/* Product Category */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', fontWeight: '600', color: '#1e293b', marginBottom: '8px', fontSize: '0.9rem' }}>
            Product Category / Sector (Optional Hint)
          </label>
          <input
            type="text"
            value={productCategory}
            onChange={(e) => setProductCategory(e.target.value)}
            placeholder="e.g. Electrical Cables, Solar PV Modules, Steel Bars, HDPE Pipes..."
            style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.95rem', boxSizing: 'border-box' }}
          />
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '8px' }}>
            <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Quick Select:</span>
            {sampleCategories.map((cat, idx) => (
              <span
                key={idx}
                onClick={() => setProductCategory(cat)}
                style={{ fontSize: '0.75rem', background: '#f1f5f9', color: '#334155', padding: '2px 8px', borderRadius: '4px', cursor: 'pointer' }}
              >
                + {cat}
              </span>
            ))}
          </div>
        </div>

        {/* Procurement Purpose */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', fontWeight: '600', color: '#1e293b', marginBottom: '8px', fontSize: '0.9rem' }}>
            Procurement Purpose / End-Use Context
          </label>
          <input
            type="text"
            value={procurementPurpose}
            onChange={(e) => setProcurementPurpose(e.target.value)}
            placeholder="e.g. Public distribution tender, CPWD building infrastructure, Smart City water project..."
            style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.95rem', boxSizing: 'border-box' }}
          />
        </div>

        {/* Technical Specifications Input */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', fontWeight: '600', color: '#1e293b', marginBottom: '8px', fontSize: '0.9rem' }}>
            Technical Specification Text / Requirement Details
          </label>
          <textarea
            rows={6}
            value={technicalSpecs}
            onChange={(e) => setTechnicalSpecs(e.target.value)}
            placeholder="Paste technical requirements, material specifications, conductor details, voltage ratings, testing parameters, or performance criteria here..."
            style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.95rem', boxSizing: 'border-box', fontFamily: 'inherit' }}
          />
        </div>

        {/* Document Upload Option */}
        <div style={{ marginBottom: '24px', background: '#f8fafc', border: '2px dashed #cbd5e1', borderRadius: '10px', padding: '20px', textAlign: 'center' }}>
          <label style={{ cursor: 'pointer', display: 'block' }}>
            <div style={{ fontSize: '2rem', marginBottom: '8px' }}>📄</div>
            <div style={{ fontWeight: '600', color: '#1e293b', fontSize: '0.95rem' }}>
              {selectedFile ? selectedFile.name : 'Upload RFP / Tender Document'}
            </div>
            <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '4px' }}>
              Supports PDF, DOCX, TXT, or scanned document images (PaddleOCR enabled)
            </div>
            <input
              type="file"
              accept=".pdf,.docx,.doc,.txt,.png,.jpg,.jpeg"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />
          </label>
          {selectedFile && (
            <button
              type="button"
              onClick={() => setSelectedFile(null)}
              style={{ marginTop: '10px', background: '#ef4444', color: '#ffffff', border: 'none', padding: '4px 10px', borderRadius: '4px', fontSize: '0.75rem', cursor: 'pointer' }}
            >
              Remove File
            </button>
          )}
        </div>

        {/* Target Language */}
        <div style={{ marginBottom: '28px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <label style={{ fontWeight: '600', color: '#1e293b', fontSize: '0.9rem' }}>Language Context:</label>
          <select
            value={targetLanguage}
            onChange={(e) => setTargetLanguage(e.target.value)}
            style={{ padding: '8px 12px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.9rem' }}
          >
            <option value="en">English (Standard Tender Specs)</option>
            <option value="hi">Hindi (हिन्दी Procurement Context)</option>
          </select>
        </div>

        {/* Submit CTA */}
        <button
          type="submit"
          disabled={loading}
          style={{
            width: '100%',
            background: loading ? '#94a3b8' : 'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)',
            color: '#ffffff',
            border: 'none',
            padding: '16px',
            borderRadius: '8px',
            fontSize: '1.05rem',
            fontWeight: '700',
            cursor: loading ? 'not-allowed' : 'pointer',
            boxShadow: '0 4px 14px rgba(30,60,114,0.3)',
            transition: 'all 0.2s'
          }}
        >
          {loading ? (
            <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
              <span className="spinner">⏳</span> {progressMessage || 'Analyzing Specification...'}
            </span>
          ) : (
            '🔍 Analyze & Recommend Indian Standards'
          )}
        </button>
      </form>
    </div>
  );
}
