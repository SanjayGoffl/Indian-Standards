import React from 'react';

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer style={{
      marginTop: '64px',
      borderTop: '1px solid var(--border-color)',
      padding: '40px 0 24px',
      width: '100%',
      display: 'flex',
      flexDirection: 'column',
      gap: '32px'
    }}>
      {/* Top Section */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '32px',
        textAlign: 'left'
      }}>
        {/* Brand Info */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxBreakInside: 'avoid' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            
             
            <span style={{ fontWeight: 700, fontSize: '1.1rem', letterSpacing: '-0.02em' }}>RAG Chatbot</span>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: '1.5' }}>
            {/* An advanced Retrieval-Augmented Generation workspace for indexing enterprise documents and chatting with AI in real-time. */}
          </p>
        </div>

        {/* Quick Links Column */}
        <div>
          <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-primary)', marginBottom: '16px' }}>
            Navigation
          </h4>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {['Knowledge Base', 'AI Chatbot', 'API Console', 'System Status'].map((item) => (
              <li key={item}>
                <a
                  href="#"
                  onClick={(e) => e.preventDefault()}
                  style={{
                    fontSize: '0.85rem',
                    color: 'var(--text-secondary)',
                    textDecoration: 'none',
                    transition: 'color 0.2s',
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-purple)'}
                  onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-secondary)'}
                >
                  {item}
                </a>
              </li>
            ))}
          </ul>
        </div>

        {/* Documentation Column */}
        <div>
          <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-primary)', marginBottom: '16px' }}>
            Resources
          </h4>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {['RAG Architecture', 'Supported Formats', 'Vector Embeddings', 'Developer Guide'].map((item) => (
              <li key={item}>
                <a
                  href="#"
                  onClick={(e) => e.preventDefault()}
                  style={{
                    fontSize: '0.85rem',
                    color: 'var(--text-secondary)',
                    textDecoration: 'none',
                    transition: 'color 0.2s',
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
                  onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-secondary)'}
                >
                  {item}
                </a>
              </li>
            ))}
          </ul>
        </div>

        {/* Tech Stack Badge Info */}
        <div>
          <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-primary)', marginBottom: '16px' }}>
            Technologies
          </h4>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            <span className="badge badge-purple" style={{ fontSize: '0.65rem' }}>React 18</span>
            <span className="badge badge-blue" style={{ fontSize: '0.65rem' }}>Vite</span>
            <span className="badge badge-success" style={{ fontSize: '0.65rem', color: 'var(--accent-cyan)', border: '1px solid hsla(180, 100%, 50%, 0.3)', background: 'hsla(180, 100%, 50%, 0.08)' }}>RAG</span>
          </div>
        </div>
      </div>

      {/* Bottom Section */}
      <div style={{
        borderTop: '1px solid var(--border-color)',
        paddingTop: '20px',
        display: 'flex',
        flexDirection: 'row',
        flexWrap: 'wrap',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '16px',
        fontSize: '0.8rem',
        color: 'var(--text-muted)'
      }}>
        <div>
          &copy; {currentYear} Chatbot Workspace. All rights reserved.
        </div>
        <div style={{ display: 'flex', gap: '16px' }}>
          <a href="#" onClick={(e) => e.preventDefault()} style={{ color: 'var(--text-muted)', textDecoration: 'none', transition: 'color 0.2s' }} onMouseEnter={(e) => e.currentTarget.style.color = 'var(--text-primary)'} onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}>Privacy Policy</a>
          <span>&middot;</span>
          <a href="#" onClick={(e) => e.preventDefault()} style={{ color: 'var(--text-muted)', textDecoration: 'none', transition: 'color 0.2s' }} onMouseEnter={(e) => e.currentTarget.style.color = 'var(--text-primary)'} onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}>Terms of Service</a>
          <span>&middot;</span>
          <a href="#" onClick={(e) => e.preventDefault()} style={{ color: 'var(--text-muted)', textDecoration: 'none', transition: 'color 0.2s' }} onMouseEnter={(e) => e.currentTarget.style.color = 'var(--text-primary)'} onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}>Security</a>
        </div>
      </div>
    </footer>
  );
}
