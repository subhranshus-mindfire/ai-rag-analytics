import React, { useState, useEffect } from 'react';
import { api } from './services/api';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { ChatWindow } from './components/ChatWindow';
import { ChatInput } from './components/ChatInput';

export function App() {
  const [sessionId, setSessionId] = useState(() => {
    return localStorage.getItem('genai_react_session_id') || `session_${Date.now()}`;
  });

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [documents, setDocuments] = useState([]);
  const [health, setHealth] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);

  useEffect(() => {
    localStorage.setItem('genai_react_session_id', sessionId);
  }, [sessionId]);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const [docsData, healthData] = await Promise.all([
        api.getDocuments().catch(() => ({ documents: [] })),
        api.getHealth().catch(() => null),
      ]);
      setDocuments(docsData.documents || []);
      setHealth(healthData);
    } catch (err) {
      console.error('Failed to load initial data:', err);
    }
  };

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || isProcessing) return;

    const userMessage = { role: 'user', content: trimmed };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsProcessing(true);

    try {
      const res = await api.sendMessage(trimmed, sessionId);
      const assistantMessage = {
        role: 'assistant',
        content: res.answer,
        intent: res.intent,
        sources: res.sources,
        sql_query: res.sql_query,
        sql_logs: res.sql_logs,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `⚠️ Error: ${err.message}`,
          intent: 'error',
        },
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSelectPrompt = (prompt) => {
    setInput(prompt);
  };

  const handleIngest = async () => {
    setIsIngesting(true);
    try {
      const res = await api.ingestDocuments();
      alert(`Ingestion Successful!\n${res.total_chunks_indexed} chunks indexed across ${res.files_processed} files.`);
      await loadInitialData();
    } catch (err) {
      alert(`Ingestion Failed: ${err.message}`);
    } finally {
      setIsIngesting(false);
    }
  };

  const [isUploading, setIsUploading] = useState(false);

  const handleUpload = async (file) => {
    setIsUploading(true);
    try {
      const res = await api.uploadDocument(file);
      await loadInitialData();
      return res;
    } finally {
      setIsUploading(false);
    }
  };

  const handleClearChat = () => {
    const newSession = `session_${Date.now()}`;
    setSessionId(newSession);
    setMessages([]);
  };

  return (
    <div className="app-container">
      <Sidebar
        documents={documents}
        onSelectPrompt={handleSelectPrompt}
        onIngest={handleIngest}
        isIngesting={isIngesting}
        onUpload={handleUpload}
        isUploading={isUploading}
      />

      <main className="chat-area">
        <Header health={health} onClearChat={handleClearChat} />
        <ChatWindow
          messages={messages}
          isProcessing={isProcessing}
          onSelectPrompt={handleSelectPrompt}
        />
        <ChatInput
          input={input}
          setInput={setInput}
          onSend={handleSend}
          isProcessing={isProcessing}
        />
      </main>
    </div>
  );
}

export default App;
