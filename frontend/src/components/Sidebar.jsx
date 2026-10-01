import React from 'react';

export function Sidebar({ documents, onSelectPrompt, onIngest, isIngesting }) {
  const samplePrompts = [
    "What is the company leave policy?",
    "Which are the top 5 customers by revenue?",
    "What is the refund policy and how much was refunded last month?",
    "What are the customer support SLA response times?"
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo-badge">⚡</div>
        <div>
          <div className="app-title">GenAI Assistant</div>
          <div className="app-subtitle">React + Document RAG & SQL</div>
        </div>
      </div>

      <div className="sidebar-content">
        <div>
          <div className="section-label">
            <span>Knowledge Base</span>
            <span className="doc-tag">{documents.length} Files</span>
          </div>
          <ul className="doc-list">
            {documents.length === 0 ? (
              <li style={{ fontSize: '12px', color: 'var(--text-muted)' }}>No documents indexed.</li>
            ) : (
              documents.map((doc) => (
                <li key={doc.document_id || doc.source} className="doc-item">
                  <span className="doc-name" title={doc.source}>📄 {doc.source}</span>
                  <span className="doc-tag">{doc.chunks_count || 1} chunks</span>
                </li>
              ))
            )}
          </ul>
        </div>

        <div>
          <div className="section-label">Example Inquiries</div>
          <div className="sample-queries">
            {samplePrompts.map((prompt, idx) => (
              <button
                key={idx}
                type="button"
                className="query-chip"
                onClick={() => onSelectPrompt(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="sidebar-footer">
        <button
          type="button"
          className="btn-secondary"
          disabled={isIngesting}
          onClick={onIngest}
        >
          <span>🔄</span> {isIngesting ? 'Ingesting...' : 'Ingest Documents'}
        </button>
      </div>
    </aside>
  );
}
