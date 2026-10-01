import React from 'react';

export function MessageBubble({ message }) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="message user">
        <div className="avatar">👤</div>
        <div className="message-content">
          <div className="bubble">{message.content}</div>
        </div>
      </div>
    );
  }

  const intent = (message.intent || 'rag').toLowerCase();

  return (
    <div className="message assistant">
      <div className="avatar">🤖</div>
      <div className="message-content">
        {message.intent && (
          <div className="meta-row">
            <span className={`intent-badge ${intent}`}>{intent.toUpperCase()}</span>
          </div>
        )}

        <div className="bubble">
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>
            {message.content}
          </div>

          {message.sql_query && (
            <details className="sql-accordion">
              <summary>
                ⚡ View Executed SQL Query ({message.sql_logs?.latency_ms ? `${message.sql_logs.latency_ms}ms` : ''}{' '}
                {message.sql_logs?.row_count !== undefined ? `${message.sql_logs.row_count} rows` : ''})
              </summary>
              <pre className="sql-code-block">
                <code>{message.sql_query}</code>
              </pre>
              {message.sql_logs && (
                <div className="sql-meta-info">
                  Engine: {message.sql_logs.db_type || 'PostgreSQL'} • {message.sql_logs.timestamp || ''}
                </div>
              )}
            </details>
          )}
        </div>

        {message.sources && message.sources.length > 0 && (
          <div className="meta-row">
            {message.sources.map((src, i) => (
              <span key={i} className="source-badge">
                📄 {src}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
