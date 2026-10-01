import React, { useRef, useEffect } from 'react';
import { MessageBubble } from './MessageBubble';

export function ChatWindow({ messages, isProcessing }) {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isProcessing]);

  return (
    <section className="chat-messages">
      {messages.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">⚛️</div>
          <h2 className="empty-title">Local GenAI Assistant (React)</h2>
          <p className="empty-desc">
            Powered by LangGraph Router, Qdrant Document RAG, and PostgreSQL Text-to-SQL.
          </p>
        </div>
      ) : (
        messages.map((msg, index) => (
          <MessageBubble key={index} message={msg} />
        ))
      )}

      {isProcessing && (
        <div className="message assistant">
          <div className="avatar">🤖</div>
          <div className="message-content">
            <div className="bubble typing-indicator">
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
            </div>
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </section>
  );
}
