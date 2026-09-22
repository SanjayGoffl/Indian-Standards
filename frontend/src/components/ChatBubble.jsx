import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function ChatBubble({ message, onSelectSource }) {
  const { sender, text, sources, timestamp } = message;
  const isUser = sender === 'user';

  const [copied, setCopied] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const supportsTTS =
    typeof window !== 'undefined' &&
    'speechSynthesis' in window;

  const handleReadAloud = () => {
    if (!supportsTTS || !text || !text.trim()) return;

    window.speechSynthesis.cancel();

    const speechText = (
      message.speech_text ||
      text
    )
      .replace(/\[\s*\d+(?:\s*,\s*\d+)*\s*\]/g, '')
      .replace(/\*\*/g, '')
      .replace(/^#{1,6}\s+/gm, '')
      .replace(/^[-*]\s+/gm, '')
      .replace(/^\d+\.\s+/gm, '')
      .replace(/\s{2,}/g, ' ')
      .trim();

    const utterance = new SpeechSynthesisUtterance(
      speechText
    );

    utterance.onstart = () => {
      setIsSpeaking(true);
    };

    utterance.onend = () => {
      setIsSpeaking(false);
    };

    utterance.onerror = () => {
      setIsSpeaking(false);
    };

    window.speechSynthesis.speak(utterance);
  };

  const handleStop = () => {
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(text || '');
      setCopied(true);

      setTimeout(() => {
        setCopied(false);
      }, 2000);
    } catch (error) {
      console.error('Failed to copy response:', error);
    }
  };

  const formatTime = (isoString) => {
    try {
      const date = new Date(isoString);

      return date.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch (error) {
      return '';
    }
  };

  /*
   * Markdown rendering components.
   *
   * These styles are intentionally kept here so the change remains
   * isolated to ChatBubble.jsx and does not affect the rest of the app.
   */
  const markdownComponents = {
    h1: ({ children }) => (
      <h1
        style={{
          margin: '0 0 14px',
          fontSize: '1.35rem',
          lineHeight: '1.35',
          fontWeight: 700,
          color: 'var(--text-primary)',
        }}
      >
        {children}
      </h1>
    ),

    h2: ({ children }) => (
      <h2
        style={{
          margin: '18px 0 10px',
          fontSize: '1.15rem',
          lineHeight: '1.4',
          fontWeight: 700,
          color: 'var(--text-primary)',
        }}
      >
        {children}
      </h2>
    ),

    h3: ({ children }) => (
      <h3
        style={{
          margin: '18px 0 10px',
          fontSize: '1rem',
          lineHeight: '1.45',
          fontWeight: 700,
          color: 'var(--text-primary)',
        }}
      >
        {children}
      </h3>
    ),

    h4: ({ children }) => (
      <h4
        style={{
          margin: '14px 0 8px',
          fontSize: '0.96rem',
          lineHeight: '1.45',
          fontWeight: 700,
          color: 'var(--text-primary)',
        }}
      >
        {children}
      </h4>
    ),

    p: ({ children }) => (
      <p
        style={{
          margin: '0 0 12px',
          lineHeight: '1.7',
          textAlign: 'left',
          color: 'var(--text-primary)',
        }}
      >
        {children}
      </p>
    ),

    strong: ({ children }) => (
      <strong
        style={{
          fontWeight: 700,
          color: 'var(--text-primary)',
        }}
      >
        {children}
      </strong>
    ),

    em: ({ children }) => (
      <em>{children}</em>
    ),

    ul: ({ children }) => (
      <ul
        style={{
          margin: '8px 0 14px 20px',
          padding: 0,
          lineHeight: '1.65',
        }}
      >
        {children}
      </ul>
    ),

    ol: ({ children }) => (
      <ol
        style={{
          margin: '8px 0 14px 22px',
          padding: 0,
          lineHeight: '1.65',
        }}
      >
        {children}
      </ol>
    ),

    li: ({ children }) => (
      <li
        style={{
          marginBottom: '6px',
          paddingLeft: '4px',
          textAlign: 'left',
        }}
      >
        {children}
      </li>
    ),

    blockquote: ({ children }) => (
      <blockquote
        style={{
          margin: '12px 0',
          padding: '10px 14px',
          borderLeft: '3px solid var(--accent-purple)',
          background: 'hsla(263, 85%, 65%, 0.06)',
          borderRadius: '0 8px 8px 0',
        }}
      >
        {children}
      </blockquote>
    ),

    code: ({ inline, children }) =>
      inline ? (
        <code
          style={{
            padding: '2px 5px',
            borderRadius: '4px',
            background: 'hsla(240, 20%, 30%, 0.35)',
            fontSize: '0.88em',
            fontFamily:
              'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
          }}
        >
          {children}
        </code>
      ) : (
        <pre
          style={{
            margin: '12px 0',
            padding: '12px',
            overflowX: 'auto',
            borderRadius: '8px',
            background: 'hsla(240, 20%, 8%, 0.75)',
            border: '1px solid var(--border-color)',
          }}
        >
          <code
            style={{
              fontSize: '0.85rem',
              lineHeight: '1.55',
              fontFamily:
                'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
            }}
          >
            {children}
          </code>
        </pre>
      ),

    hr: () => (
      <hr
        style={{
          margin: '16px 0',
          border: 0,
          borderTop: '1px solid var(--border-color)',
        }}
      />
    ),

    table: ({ children }) => (
      <div
        style={{
          width: '100%',
          overflowX: 'auto',
          margin: '14px 0',
        }}
      >
        <table
          style={{
            width: '100%',
            minWidth: '520px',
            borderCollapse: 'collapse',
            fontSize: '0.88rem',
            lineHeight: '1.5',
          }}
        >
          {children}
        </table>
      </div>
    ),

    thead: ({ children }) => (
      <thead
        style={{
          background: 'hsla(263, 85%, 65%, 0.12)',
        }}
      >
        {children}
      </thead>
    ),

    th: ({ children }) => (
      <th
        style={{
          padding: '9px 10px',
          border: '1px solid var(--border-color)',
          textAlign: 'left',
          fontWeight: 700,
          color: 'var(--text-primary)',
        }}
      >
        {children}
      </th>
    ),

    td: ({ children }) => (
      <td
        style={{
          padding: '9px 10px',
          border: '1px solid var(--border-color)',
          textAlign: 'left',
          verticalAlign: 'top',
          color: 'var(--text-primary)',
        }}
      >
        {children}
      </td>
    ),

    a: ({ children, href }) => (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        style={{
          color: 'var(--accent-blue)',
          textDecoration: 'underline',
        }}
      >
        {children}
      </a>
    ),
  };

  return (
    <div
      className="animate-fade-in"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start',
        marginBottom: '20px',
        width: '100%',
        maxWidth: '85%',
        alignSelf: isUser ? 'flex-end' : 'flex-start',
      }}
    >
      {/* Sender Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          marginBottom: '6px',
          fontSize: '0.8rem',
          color: 'var(--text-muted)',
        }}
      >
        {!isUser && (
          <div
            style={{
              width: '24px',
              height: '24px',
              borderRadius: '6px',
              background:
                'linear-gradient(135deg, var(--accent-purple), var(--accent-blue))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
            }}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 2a10 10 0 0 1 8 12.83V19a2 2 0 0 1-2 2h-1.5a1 1 0 0 0-.7.3l-1.5 1.5a1 1 0 0 1-1.4 0l-1.5-1.5a1 1 0 0 0-.7-.3H10a2 2 0 0 1-2-2v-4.17A10 10 0 0 1 12 2z" />
            </svg>
          </div>
        )}

        <span
          style={{
            fontWeight: 600,
            color: isUser
              ? 'var(--text-secondary)'
              : 'var(--text-primary)',
          }}
        >
          {isUser ? 'You' : 'AI Assistant'}
        </span>

        <span>•</span>

        <span>{formatTime(timestamp)}</span>
      </div>

      {/* Bubble Body */}
      <div
        className={isUser ? '' : 'glass-card'}
        style={{
          padding: '16px',
          borderRadius: isUser
            ? '16px 16px 4px 16px'
            : '16px 16px 16px 4px',
          background: isUser
            ? 'linear-gradient(135deg, var(--accent-purple), var(--accent-blue))'
            : 'var(--bg-surface)',
          border: isUser
            ? 'none'
            : '1px solid var(--border-color)',
          color: '#fff',
          lineHeight: '1.6',
          fontSize: '0.95rem',
          position: 'relative',
          boxShadow: isUser
            ? '0 4px 12px hsla(263, 85%, 65%, 0.15)'
            : 'var(--glass-shadow)',
          width: '100%',
        }}
      >
        {/* Copy Button */}
        <button
          onClick={copyToClipboard}
          style={{
            position: 'absolute',
            top: '12px',
            right: '12px',
            background: 'transparent',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            opacity: 0.6,
            transition: 'opacity 0.2s',
            zIndex: 2,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.opacity = 1;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.opacity = 0.6;
          }}
          title="Copy to clipboard"
        >
          {copied ? (
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--accent-emerald)"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="20 6 9 17 4 12" />
            </svg>
          ) : (
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect
                x="9"
                y="9"
                width="13"
                height="13"
                rx="2"
              />
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
            </svg>
          )}
        </button>

        {/* Message Text */}
        <div
          style={{
            paddingRight: '28px',
            textAlign: 'left',
            color: 'var(--text-primary)',
          }}
        >
          {isUser ? (
            <div
              style={{
                whiteSpace: 'pre-wrap',
                lineHeight: '1.6',
              }}
            >
              {text}
            </div>
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={markdownComponents}
            >
              {text || ''}
            </ReactMarkdown>
          )}
        </div>

        {/* TTS Controls */}
        {!isUser && supportsTTS && (
          <div
            style={{
              marginTop: '12px',
              display: 'flex',
            }}
          >
            {!isSpeaking ? (
              <button
                onClick={handleReadAloud}
                aria-label="Read response aloud"
                title="Read response aloud"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: 'transparent',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-muted)',
                  padding: '4px 10px',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background =
                    'hsla(240, 20%, 30%, 0.15)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background =
                    'transparent';
                }}
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                Read Aloud
              </button>
            ) : (
              <button
                onClick={handleStop}
                aria-label="Stop reading"
                title="Stop reading"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: 'hsla(0, 70%, 50%, 0.1)',
                  border:
                    '1px solid hsla(0, 70%, 50%, 0.3)',
                  color: 'var(--text-primary)',
                  padding: '4px 10px',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background =
                    'hsla(0, 70%, 50%, 0.2)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background =
                    'hsla(0, 70%, 50%, 0.1)';
                }}
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <rect
                    x="6"
                    y="6"
                    width="12"
                    height="12"
                  />
                </svg>
                Stop
              </button>
            )}
          </div>
        )}

        {/* Sources Attribution Panel */}
        {!isUser &&
          sources &&
          sources.length > 0 && (
            <div
              style={{
                marginTop: '16px',
                paddingTop: '12px',
                borderTop:
                  '1px solid var(--border-color)',
              }}
            >
              <span
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  color: 'var(--text-muted)',
                  display: 'block',
                  marginBottom: '8px',
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase',
                }}
              >
                Sources Used ({sources.length})
              </span>

              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '8px',
                }}
              >
                {sources.map((source, idx) => (
                  <button
                    key={
                      source.chunk_id ||
                      source.reference ||
                      idx
                    }
                    onClick={() =>
                      onSelectSource &&
                      onSelectSource(
                        source,
                        message
                      )
                    }
                    className="badge badge-purple"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      cursor: 'pointer',
                      fontSize: '0.75rem',
                      transition:
                        'all 0.2s ease',
                      textTransform: 'none',
                      fontWeight: 500,
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform =
                        'translateY(-1px)';
                      e.currentTarget.style.boxShadow =
                        '0 2px 8px var(--accent-purple-glow)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform =
                        'translateY(0)';
                      e.currentTarget.style.boxShadow =
                        'none';
                    }}
                  >
                    <svg
                      width="12"
                      height="12"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                    </svg>

                    <span
                      style={{
                        maxWidth: '140px',
                        overflow: 'hidden',
                        textOverflow:
                          'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {source.source ||
                        source.metadata?.filename ||
                        'Retrieved document'}
                    </span>

                    <span
                      style={{
                        opacity: 0.6,
                        fontSize: '0.7rem',
                      }}
                    >
                      {source.reference ||
                        `[${idx + 1}]`}
                    </span>

                    <span
                      style={{
                        marginLeft: '4px',
                        padding: '2px 4px',
                        background:
                          'hsla(263, 85%, 65%, 0.25)',
                        borderRadius: '4px',
                        fontSize: '0.65rem',
                        color:
                          'var(--text-primary)',
                        fontWeight: 'bold',
                      }}
                    >
                      {Math.round(
                        Number(
                          source.relevance_score ||
                            0
                        ) * 100
                      )}
                      %
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
      </div>
    </div>
  );
}