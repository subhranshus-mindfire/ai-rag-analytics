import React, { useState } from 'react';

// Lightweight Markdown parser
function parseMarkdown(md) {
  if (!md) return '';
  let html = md
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Fenced Code blocks
  html = html.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const raw = code.trim();
    const encoded = encodeURIComponent(raw);
    return `<div class="code-block-wrapper">
      <div class="code-block-header">
        <span>${lang || 'code'}</span>
        <button type="button" class="copy-code-btn" onclick="navigator.clipboard.writeText(decodeURIComponent('${encoded}')).then(()=>{this.textContent='Copied!';setTimeout(()=>this.textContent='Copy',2000)})">Copy</button>
      </div>
      <pre><code>${raw}</code></pre>
    </div>`;
  });

  // Tables
  html = html.replace(/((?:\|[^\n]+\|\r?\n)+)/g, (tableMatch) => {
    const rows = tableMatch.trim().split('\n').filter((r) => r.trim());
    if (rows.length < 2) return tableMatch;
    let tableHtml = '<div class="table-responsive"><table class="markdown-table">';
    rows.forEach((row, idx) => {
      if (row.includes('---')) return;
      const cols = row.split('|').filter((_, i, arr) => i > 0 && i < arr.length - 1);
      const tag = idx === 0 ? 'th' : 'td';
      tableHtml += '<tr>' + cols.map((c) => `<${tag}>${c.trim()}</${tag}>`).join('') + '</tr>';
    });
    tableHtml += '</table></div>';
    return tableHtml;
  });

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

  // Headers
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

  // Bold & Italics
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // Blockquotes
  html = html.replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>');

  // Lists
  html = html.replace(/^\s*[-*]\s+(.*$)/gim, '<ul><li>$1</li></ul>');
  html = html.replace(/<\/ul>\s*<ul>/g, '');
  html = html.replace(/^\s*\d+\.\s+(.*$)/gim, '<ol><li>$1</li></ol>');
  html = html.replace(/<\/ol>\s*<ol>/g, '');

  // Paragraphs
  html = html
    .split('\n\n')
    .map((chunk) => {
      const trimmed = chunk.trim();
      if (!trimmed) return '';
      if (
        trimmed.startsWith('<h') ||
        trimmed.startsWith('<ul') ||
        trimmed.startsWith('<ol') ||
        trimmed.startsWith('<div') ||
        trimmed.startsWith('<blockquote') ||
        trimmed.startsWith('<table')
      ) {
        return trimmed;
      }
      return `<p>${trimmed.replace(/\n/g, '<br/>')}</p>`;
    })
    .join('');

  return html;
}

function SQLAccordion({ query, logs }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(query);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <details className="sql-card">
      <summary>
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <ellipse cx="12" cy="5" rx="9" ry="3" />
            <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
            <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
          </svg>
          Executed SQL Query
        </span>
        <div className="sql-metrics">
          {logs?.latency_ms !== undefined && (
            <span className="metric-tag">{logs.latency_ms}ms</span>
          )}
          {logs?.row_count !== undefined && (
            <span className="metric-tag">{logs.row_count} rows</span>
          )}
        </div>
      </summary>
      <div className="sql-content">
        <pre className="sql-code">{query}</pre>
        <div className="sql-footer">
          <span>Engine: {logs?.db_type || 'PostgreSQL'}</span>
          <button type="button" className="copy-code-btn" onClick={handleCopy}>
            {copied ? '✓ Copied' : 'Copy SQL'}
          </button>
        </div>
      </div>
    </details>
  );
}

export function MessageBubble({ message, isLiveStreaming = false }) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="message-row user">
        <div className="message-body">
          <div className="user-bubble">{message.content}</div>
        </div>
        <div className="avatar-badge user-avatar">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        </div>
      </div>
    );
  }

  const intent = (message.intent || 'rag').toLowerCase();
  const intentLabels = {
    rag: 'Document RAG',
    sql: 'SQL Analytics',
    combined: 'Hybrid RAG + SQL',
    general: 'General Assistant',
    error: 'System Notice',
  };

  const formattedHtml = parseMarkdown(message.content);

  return (
    <div className="message-row assistant">
      <div className="avatar-badge assistant-avatar">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3z" />
        </svg>
      </div>
      <div className="message-body">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {message.intent && (
            <span className={`intent-pill ${intent}`}>
              {intentLabels[intent] || intent.toUpperCase()}
            </span>
          )}

          {isLiveStreaming && message.status && (
            <span className="status-pill">
              <span className="status-spinner" />
              {message.status}
            </span>
          )}
        </div>

        <div className="assistant-bubble">
          {message.content ? (
            <div className="markdown-body">
              <div dangerouslySetInnerHTML={{ __html: formattedHtml }} />
              {isLiveStreaming && <span className="streaming-cursor" />}
            </div>
          ) : (
            isLiveStreaming && (
              <div className="streaming-loading-box">
                <div className="typing-dot" />
                <div className="typing-dot" />
                <div className="typing-dot" />
              </div>
            )
          )}

          {message.sql_query && (
            <SQLAccordion query={message.sql_query} logs={message.sql_logs} />
          )}

          {message.sources && message.sources.length > 0 && (
            <div className="sources-container">
              <span className="sources-label">Sources:</span>
              {message.sources.map((src, i) => (
                <span key={i} className="source-chip">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                  {src}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
