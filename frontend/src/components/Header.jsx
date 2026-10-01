import React from 'react';

export function Header({ health, onClearChat }) {
  const dbType = health?.database?.type ? health.database.type.toUpperCase() : 'PostgreSQL';
  const vectorStore = health?.vector_store?.status === 'connected' ? 'Qdrant Ready' : 'Vector DB';
  const provider = health?.llm_provider ? health.llm_provider.toUpperCase() : 'Gemini / Groq';

  return (
    <header className="chat-header">
      <div className="header-status">
        <div className="status-badge">
          <div className="status-pulse"></div>
          <span>{dbType} · {vectorStore} · {provider}</span>
        </div>
      </div>
      <button
        type="button"
        className="btn-icon-label"
        onClick={onClearChat}
        title="Start fresh conversation"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="3 6 5 6 21 6" />
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
        </svg>
        <span>New Chat</span>
      </button>
    </header>
  );
}
