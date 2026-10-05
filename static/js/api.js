/**
 * API Service Layer for Local GenAI Data Assistant
 */
export const API = {
  /**
   * Send a chat message to the LangGraph router
   */
  async sendMessage(message, sessionId = "default") {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        session_id: sessionId,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Server error (${response.status})`);
    }

    return await response.json();
  },

  /**
   * Fetch all indexed documents from the vector store
   */
  async getDocuments() {
    const response = await fetch("/documents");
    if (!response.ok) {
      throw new Error(`Failed to fetch documents (${response.status})`);
    }
    return await response.json();
  },

  /**
   * Trigger bulk ingestion of data/documents/
   */
  async ingestDocuments() {
    const response = await fetch("/documents/ingest", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({}),
    });

    if (!response.ok) {
      throw new Error(`Failed to ingest documents (${response.status})`);
    }
    return await response.json();
  },

  /**
   * Upload and index a document with backend validation
   */
  async uploadDocument(file) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch("/documents/upload", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Upload failed (${response.status})`);
    }
    return await response.json();
  },

  /**
   * Delete document by filename/ID
   */
  async deleteDocument(documentId) {
    const response = await fetch(`/documents/${encodeURIComponent(documentId)}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Delete failed (${response.status})`);
    }
    return await response.json();
  },

  /**
   * Fetch diagnostic system health
   */
  async getHealth() {
    const response = await fetch("/health");
    if (!response.ok) {
      throw new Error(`Health check failed (${response.status})`);
    }
    return await response.json();
  },
};
