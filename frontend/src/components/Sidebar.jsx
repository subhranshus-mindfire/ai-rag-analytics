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
        <div className="sidebar-brand">
          <div className="brand-icon-wrapper">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3z" />
            </svg>
          </div>
          <div className="brand-text">
            <div className="app-title">Data Assistant</div>
            <div className="app-subtitle">LangGraph · RAG · SQL</div>
          </div>
        </div>
      </div>

      <div className="sidebar-content">
        <div>
          <div className="section-label">
            <span>Knowledge Base</span>
            <span className="doc-count-badge">{documents.length} Files</span>
          </div>
          <ul className="doc-list">
            {documents.length === 0 ? (
              <li style={{ fontSize: '12px', color: 'var(--text-dim)', padding: '4px 8px' }}>
                No documents indexed.
              </li>
            ) : (
              documents.map((doc) => {
                const ext = (doc.source || "").split(".").pop().toUpperCase() || "DOC";
                return (
                  <li key={doc.document_id || doc.source} className="doc-item">
                    <div className="doc-info">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="doc-icon">
                        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                        <polyline points="14 2 14 8 20 8" />
                      </svg>
                      <span className="doc-name" title={doc.source}>{doc.source}</span>
                    </div>
                    <span className="doc-tag">{ext}</span>
                  </li>
                );
              })
            )}
          </ul>
        </div>

        <div>
          <div className="section-label">Suggested Queries</div>
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
          className="btn-sidebar"
          disabled={isIngesting}
          onClick={onIngest}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
          </svg>
          <span>{isIngesting ? 'Ingesting Documents...' : 'Re-index Knowledge Base'}</span>
        </button>
      </div>
    </aside>
  );
}
