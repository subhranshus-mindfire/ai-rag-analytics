import React, { useRef, useEffect } from 'react';
import { MessageBubble } from './MessageBubble';

function EmptyState({ onSelectPrompt }) {
  const starters = [
    {
      tag: 'Document RAG',
      text: 'What is the company leave policy?',
    },
    {
      tag: 'SQL Analytics',
      text: 'Which are the top 5 customers by revenue?',
    },
    {
      tag: 'Hybrid Routing',
      text: 'What is the refund policy and how much was refunded last month?',
    },
    {
      tag: 'Document RAG',
      text: 'What are the customer support SLA response times?',
    },
  ];

  return (
    <div className="empty-state">
      <div className="empty-icon-glow">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3z" />
        </svg>
      </div>
      <h2 className="empty-title">Enterprise Data Assistant</h2>
      <p className="empty-desc">
        Chat with company policy documents and query relational PostgreSQL database analytics in real time.
      </p>
      <div className="starter-grid">
        {starters.map((item, idx) => (
          <div
            key={idx}
            className="starter-card"
            onClick={() => onSelectPrompt(item.text)}
          >
            <div className="starter-tag">{item.tag}</div>
            <div className="starter-text">{item.text}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ChatWindow({ messages, isProcessing, streamingMessage, onSelectPrompt }) {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isProcessing, streamingMessage]);

  return (
    <section className="chat-messages">
      <div className="messages-inner">
        {messages.length === 0 && !streamingMessage ? (
          <EmptyState onSelectPrompt={onSelectPrompt} />
        ) : (
          messages.map((msg, index) => (
            <MessageBubble key={index} message={msg} />
          ))
        )}

        {streamingMessage && (
          <MessageBubble message={streamingMessage} isLiveStreaming={true} />
        )}

        {isProcessing && !streamingMessage && (
          <div className="message-row assistant">
            <div className="avatar-badge assistant-avatar">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3z" />
              </svg>
            </div>
            <div className="message-body">
              <div className="assistant-bubble typing-box">
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </section>
  );
}
