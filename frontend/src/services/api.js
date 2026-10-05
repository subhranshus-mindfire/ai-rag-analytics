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
   * Fetch system health
   */
  async getHealth() {
    const res = await fetch('/health');
    if (!res.ok) throw new Error('Health check failed');
    return await res.json();
  },
};
