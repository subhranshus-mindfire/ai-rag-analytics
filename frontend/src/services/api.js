/**
 * API Service for communication with FastAPI backend
 */
export const api = {
  /**
   * Send chat prompt to /chat endpoint
   */
  async sendMessage(message, sessionId = 'default') {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error (${res.status})`);
    }

    return await res.json();
  },

  /**
   * Stream chat prompt with live agent events & tokens via /chat/stream
   */
  async sendMessageStream(message, sessionId = 'default', callbacks = {}) {
    const res = await fetch('/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error (${res.status})`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop(); // Keep unparsed trailing data

      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6);
        try {
          const event = JSON.parse(payload);
          if (event.type === 'status' && callbacks.onStatus) {
            callbacks.onStatus(event.step);
          } else if (event.type === 'intent' && callbacks.onIntent) {
            callbacks.onIntent(event.intent);
          } else if (event.type === 'token' && callbacks.onToken) {
            callbacks.onToken(event.content);
          } else if (event.type === 'sources' && callbacks.onSources) {
            callbacks.onSources(event.sources);
          } else if (event.type === 'sql_query' && callbacks.onSqlQuery) {
            callbacks.onSqlQuery(event.query, event.logs);
          } else if (event.type === 'done' && callbacks.onDone) {
            callbacks.onDone(event);
          } else if (event.type === 'error' && callbacks.onError) {
            callbacks.onError(event.message);
          }
        } catch (e) {
          console.error('Failed to parse SSE event:', e);
        }
      }
    }
  },

  /**
   * Fetch indexed documents list
   */
  async getDocuments() {
    const res = await fetch('/documents');
    if (!res.ok) throw new Error('Failed to load documents');
    return await res.json();
  },

  /**
   * Trigger bulk ingestion
   */
  async ingestDocuments() {
    const res = await fetch('/documents/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (!res.ok) throw new Error('Ingestion failed');
    return await res.json();
  },

  /**
   * Upload and index a document with validation
   */
  async uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/documents/upload', {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Upload failed (${res.status})`);
    }
    return await res.json();
  },

  /**
   * Delete document by filename/ID
   */
  async deleteDocument(documentId) {
    const res = await fetch(`/documents/${encodeURIComponent(documentId)}`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to delete document (${res.status})`);
    }
    return await res.json();
  },

  /**
   * Fetch system health
   */
  async getHealth() {
    const res = await fetch('/health');
    if (!res.ok) throw new Error('Health check failed');
    return await res.json();
  },
};
