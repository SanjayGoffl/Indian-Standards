import React, { useState, useEffect } from 'react';
import FileUploader from '../components/FileUploader';
import Footer from '../components/Footer';
import * as api from '../services/api';

export default function UploadPage({ onStartChat }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState(null);

  const fetchDocs = async () => {
    try {
      const docs = await api.getDocuments();
      setDocuments(docs);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  useEffect(() => {
    if (!documents.some(doc => doc.status === 'parsing')) return undefined;

    const interval = setInterval(fetchDocs, 3000);
    return () => clearInterval(interval);
  }, [documents]);
  
  const handleDelete = async (id) => {
    const confirmed = window.confirm(
      'Are you sure you want to delete this document?'
    );

    if (!confirmed) {
      return;
    }

    setDeletingId(id);

    try {
      await api.deleteDocument(id);
      setDocuments(prev => prev.filter(doc => doc.id !== id));
    } catch (e) {
      alert('Failed to delete document');
    } finally {
      setDeletingId(null);
    }
  };

  const formatBytes = (bytes, decimals = 2) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  };

  const formatDate = (isoString) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return '';
    }
  };

  // Stats calculation
  const totalSize = documents.reduce((acc, curr) => acc + curr.size, 0);
  const readyDocsCount = documents.filter(d => d.status === 'indexed').length;

  return (
    <div style={{ padding: '40px', maxWidth: '1200px', width: '100%', margin: '0 auto' }}>
      
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
        <div>
          <h1 style={{ fontSize: '2.2rem', fontWeight: 700, marginBottom: '6px', textAlign: 'left' }}>
            Knowledge Base
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '1rem', textAlign: 'left' }}>
            Upload files to build your custom database context. The AI chatbot will retrieve answers directly from these files.
          </p>
        </div>
        <button onClick={onStartChat} className="btn btn-primary">
          <span>Start Chatting</span>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="5" y1="12" x2="19" y2="12"/>
            <polyline points="12 5 19 12 12 19"/>
          </svg>
        </button>
      </div>

      {/* Stats Board */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '20px', marginBottom: '32px' }}>
        <div className="glass-card" style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'hsla(263, 85%, 65%, 0.12)', color: 'var(--accent-purple)', display: 'flex', alignItems: 'center', justifySelf: 'center', justifyContent: 'center' }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
          </div>
          <div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block' }}>Total Documents</span>
            <span style={{ fontSize: '1.6rem', fontWeight: 700 }}>{documents.length}</span>
          </div>
        </div>

        <div className="glass-card" style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'hsla(210, 100%, 60%, 0.12)', color: 'var(--accent-blue)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
              <line x1="9" y1="3" x2="9" y2="21"/>
            </svg>
          </div>
          <div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block' }}>KB Storage Size</span>
            <span style={{ fontSize: '1.6rem', fontWeight: 700 }}>{formatBytes(totalSize)}</span>
          </div>
        </div>
      </div>

      {/* Grid: Upload Widget on Left, Documents on Right */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '32px' }}>
        
        {/* Left Side: Upload Zone */}
        <div>
          <h2 style={{ fontSize: '1.3rem', marginBottom: '16px', textAlign: 'left' }}>Upload Document</h2>
          <FileUploader onUploadComplete={fetchDocs} />
        </div>

        {/* Right Side: Document Inventory */}
        <div>
          <h2 style={{ fontSize: '1.3rem', marginBottom: '16px', textAlign: 'left' }}>Document Repository</h2>
          <div className="glass-panel" style={{ padding: '20px', minHeight: '300px' }}>
            {loading ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '220px', color: 'var(--text-secondary)' }}>
                <span>Loading Repository...</span>
              </div>
            ) : documents.length === 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '220px', color: 'var(--text-muted)' }}>
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: '12px' }}>
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                </svg>
                <span>No documents in knowledge base yet.</span>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {documents.map((doc) => (
                  <div 
                    key={doc.id}
                    className="glass-card"
                    style={{ 
                      padding: '14px 18px', 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'space-between',
                      border: '1px solid var(--border-color)',
                      borderRadius: '10px',
                      background: 'hsla(240, 25%, 12%, 0.35)'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px', maxWidth: '70%' }}>
                      {/* Format Icon */}
                      <div style={{ 
                        width: '36px', 
                        height: '36px', 
                        borderRadius: '8px', 
                        background: 'hsla(240, 20%, 30%, 0.15)',
                        color: 'var(--text-secondary)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0
                      }}>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                          <polyline points="14 2 14 8 20 8"/>
                        </svg>
                      </div>

                      {/* Info block */}
                      <div style={{ textAlign: 'left', minWidth: 0 }}>
                        <h4 style={{ fontSize: '0.95rem', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: '2px' }} title={doc.name}>
                          {doc.name}
                        </h4>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          <span>{formatBytes(doc.size)}</span>
                          <span>•</span>
                          <span>{formatDate(doc.uploadedAt)}</span>
                        </div>
                      </div>
                    </div>

                    {/* Status & Actions */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                        {doc.status === 'indexed' ? (
                          <span className="badge badge-success" style={{ fontSize: '0.65rem' }}>Indexed</span>
                        ) : doc.status === 'failed' ? (
                          <span className="badge badge-error" style={{ fontSize: '0.65rem' }}>Failed</span>
                        ) : (
                          <span className="badge badge-warning" style={{ fontSize: '0.65rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <span className="typing-dot" style={{ width: '4px', height: '4px', background: 'currentColor' }}></span>
                            Parsing
                          </span>
                        )}
                      </div>

                      <button
                        onClick={() => handleDelete(doc.id)}
                        disabled={deletingId === doc.id}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          color: deletingId === doc.id ? 'var(--text-muted)' : 'var(--accent-rose)',
                          opacity: 0.7,
                          cursor: deletingId === doc.id ? 'not-allowed' : 'pointer',
                          padding: '6px',
                          borderRadius: '6px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          transition: 'all 0.2s'
                        }}
                        onMouseEnter={(e) => { if (deletingId !== doc.id) { e.currentTarget.style.opacity = 1; e.currentTarget.style.background = 'hsla(350, 80%, 60%, 0.1)'; } }}
                        onMouseLeave={(e) => { e.currentTarget.style.opacity = 0.7; e.currentTarget.style.background = 'transparent'; }}
                        title="Delete document"
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="3 6 5 6 21 6"/>
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                          <line x1="10" y1="11" x2="10" y2="17"/>
                          <line x1="14" y1="11" x2="14" y2="17"/>
                        </svg>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

      </div>
      
      {/* Page Footer */}
      <Footer />
    </div>
  );
}