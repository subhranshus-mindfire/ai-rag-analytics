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
    <footer className="chat-input-container">
      <div className="input-box">
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          rows={1}
          placeholder="Ask a document question, SQL analytical query, or combined inquiry..."
          value={input}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={isProcessing}
        />
        <button
          type="button"
          className="send-btn"
          disabled={isProcessing || !input.trim()}
          onClick={onSend}
        >
          <span>Send</span>
          <span>➤</span>
        </button>
      </div>
    </footer>
  );
}
