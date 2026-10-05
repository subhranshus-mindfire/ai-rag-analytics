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
  const [streamingMessage, setStreamingMessage] = useState(null);

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

    const activeStream = {
      role: 'assistant',
      content: '',
      status: 'Analyzing query intent...',
      intent: null,
      sources: [],
      sql_query: null,
      sql_logs: null,
      isStreaming: true,
    };
    setStreamingMessage({ ...activeStream });

    try {
      await api.sendMessageStream(trimmed, sessionId, {
        onStatus: (step) => {
          activeStream.status = step;
          setStreamingMessage({ ...activeStream });
        },
        onIntent: (intent) => {
          activeStream.intent = intent;
          setStreamingMessage({ ...activeStream });
        },
        onSources: (sources) => {
          activeStream.sources = sources;
          setStreamingMessage({ ...activeStream });
        },
        onSqlQuery: (query, logs) => {
          activeStream.sql_query = query;
          activeStream.sql_logs = logs;
          setStreamingMessage({ ...activeStream });
        },
        onToken: (token) => {
          activeStream.content += token;
          setStreamingMessage({ ...activeStream });
        },
        onDone: (event) => {
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content: event.final_answer || activeStream.content,
              intent: event.intent || activeStream.intent,
              sources: event.sources || activeStream.sources || [],
              sql_query: event.sql_query || activeStream.sql_query,
              sql_logs: event.sql_logs || activeStream.sql_logs,
            },
          ]);
          setStreamingMessage(null);
        },
        onError: (errMessage) => {
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content: `⚠️ Error: ${errMessage}`,
              intent: 'error',
            },
          ]);
          setStreamingMessage(null);
        },
      });
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `⚠️ Error: ${err.message}`,
          intent: 'error',
        },
      ]);
      setStreamingMessage(null);
    } finally {
      setIsProcessing(false);
      setStreamingMessage(null);
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

  const handleDeleteDocument = async (docId) => {
    const res = await api.deleteDocument(docId);
    await loadInitialData();
    return res;
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
        onDeleteDocument={handleDeleteDocument}
      />

      <main className="chat-area">
        <Header health={health} onClearChat={handleClearChat} />
        <ChatWindow
          messages={messages}
          isProcessing={isProcessing}
          streamingMessage={streamingMessage}
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
