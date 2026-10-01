import React from 'react';

export function Header({ health, onClearChat }) {
  const dbType = health?.database?.type ? health.database.type.toUpperCase() : 'DB';
  const qdrantStatus = health?.vector_store?.status === 'connected' ? 'Qdrant Online' : 'Vector Ready';
  const provider = health?.llm_provider ? health.llm_provider.toUpperCase() : 'AI';

  return (
    <header className="chat-header">
      <div className="header-status">
        <div className="status-indicator"></div>
        <span>{dbType} • {qdrantStatus} • {provider}</span>
      </div>
      <div>
        <button
          type="button"
          className="btn-secondary"
          onClick={onClearChat}
          style={{ padding: '6px 12px', fontSize: '12px' }}
        >
          <span>🗑️</span> New Chat
        </button>
      </div>
    </header>
  );
}
