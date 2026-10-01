import React, { useRef, useEffect } from 'react';

export function ChatInput({ input, setInput, onSend, isProcessing }) {
  const textareaRef = useRef(null);

  useEffect(() => {
    if (!isProcessing && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isProcessing]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  const handleChange = (e) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  };

  return (
    <div className="chat-input-wrapper">
      <div className="input-container">
        <div className="input-row">
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            rows={1}
            placeholder="Ask about company documents, query database analytics, or hybrid inquiries..."
            value={input}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            disabled={isProcessing}
          />
          <button
            type="button"
            className="send-button"
            disabled={isProcessing || !input.trim()}
            onClick={onSend}
            title="Send question (Enter)"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="12" y1="19" x2="12" y2="5" />
              <polyline points="5 12 12 5 19 12" />
            </svg>
          </button>
        </div>
        <div className="input-hint-row">
          <span className="input-hint">Enter to send · Shift+Enter for new line</span>
          <span className="input-hint">SELECT-only guardrails active</span>
        </div>
      </div>
    </div>
  );
}
