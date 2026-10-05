import React, { useState, useRef } from 'react';

export function Sidebar({ documents, onSelectPrompt, onIngest, isIngesting, onUpload, isUploading }) {
  const samplePrompts = [
    "What is the company leave policy?",
    "Which are the top 5 customers by revenue?",
    "What is the refund policy and how much was refunded last month?",
    "What are the customer support SLA response times?"
  ];

  const fileInputRef = useRef(null);
  const [feedback, setFeedback] = useState(null);

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = '';

    const ALLOWED_EXTS = ['.pdf', '.docx', '.txt', '.md', '.markdown'];
    const fileName = file.name || '';
    const ext = '.' + (fileName.split('.').pop() || '').toLowerCase();

    // 1. Validate file extension
    if (!ALLOWED_EXTS.includes(ext)) {
      setFeedback({
        type: 'error',
        message: `Unsupported format "${ext}". Allowed: ${ALLOWED_EXTS.join(', ')}`
      });
      return;
    }

    // 2. Validate empty file
    if (file.size === 0) {
      setFeedback({
        type: 'error',
        message: `"${fileName}" is empty (0 bytes). Please upload a valid document.`
      });
      return;
    }

    // 3. Validate maximum size (15MB)
    const MAX_SIZE_MB = 15;
    const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;
    if (file.size > MAX_SIZE_BYTES) {
      const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
      setFeedback({
        type: 'error',
        message: `"${fileName}" is ${sizeMb}MB. Maximum allowed size is ${MAX_SIZE_MB}MB.`
      });
      return;
    }

    // 4. Validate duplicate document name
    const isDuplicate = (documents || []).some(
      (d) => (d.source || '').toLowerCase() === fileName.toLowerCase()
    );
    if (isDuplicate) {
      const overwrite = window.confirm(
        `"${fileName}" already exists in the Knowledge Base.\n\nDo you want to overwrite and re-index it?`
      );
      if (!overwrite) return;
    }

    setFeedback({
      type: 'info',
      message: `Uploading and indexing "${fileName}"...`
    });

    try {
      const res = await onUpload(file);
      setFeedback({
        type: 'success',
        message: res.message || `Indexed ${res.chunks_indexed || 0} chunks for "${fileName}".`
      });
      setTimeout(() => {
        setFeedback((prev) => (prev?.type === 'success' ? null : prev));
      }, 5000);
    } catch (err) {
      setFeedback({
        type: 'error',
        message: err.message || 'Failed to upload document.'
      });
    }
  };

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

          {/* Hidden file input */}
          <input
            type="file"
            ref={fileInputRef}
            accept=".pdf,.docx,.txt,.md,.markdown"
            style={{ display: 'none' }}
            onChange={handleFileSelect}
          />

          {/* Upload Button */}
          <button
            type="button"
            className="btn-upload"
            disabled={isUploading || isIngesting}
            onClick={() => fileInputRef.current?.click()}
            title="Upload and index a document (.pdf, .docx, .txt, .md)"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span>{isUploading ? 'Uploading & Indexing...' : 'Upload Document'}</span>
          </button>

          {/* Validation / Feedback Banner */}
          {feedback && (
            <div className={`upload-feedback upload-feedback-${feedback.type}`}>
              <div style={{ display: 'flex', gap: '6px', alignItems: 'flex-start', flex: 1 }}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0, marginTop: '2px' }}>
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <span>{feedback.message}</span>
              </div>
              <button
                type="button"
                className="upload-feedback-close"
                onClick={() => setFeedback(null)}
              >
                ✕
              </button>
            </div>
          )}

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
