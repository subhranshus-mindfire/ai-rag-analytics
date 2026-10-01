import { API } from "./api.js";

// Application State
const state = {
  sessionId: localStorage.getItem("genai_session_id") || `session_${Date.now()}`,
  isProcessing: false,
  documents: [],
};

localStorage.setItem("genai_session_id", state.sessionId);

// DOM Elements
const elements = {
  chatMessages: document.getElementById("chatMessages"),
  chatInput: document.getElementById("chatInput"),
  sendBtn: document.getElementById("sendBtn"),
  docList: document.getElementById("docList"),
  docCountBadge: document.getElementById("docCountBadge"),
  healthStatusText: document.getElementById("healthStatusText"),
  ingestBtn: document.getElementById("ingestBtn"),
  clearChatBtn: document.getElementById("clearChatBtn"),
  sampleChips: document.querySelectorAll(".query-chip"),
};

/**
 * Initialize application listeners and data
 */
async function init() {
  setupEventListeners();
  await refreshHealthStatus();
  await refreshDocumentsList();
}

/**
 * Register user interactions
 */
function setupEventListeners() {
  // Input auto-expand and Enter key
  elements.chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  elements.chatInput.addEventListener("input", () => {
    elements.chatInput.style.height = "auto";
    elements.chatInput.style.height = `${Math.min(elements.chatInput.scrollHeight, 120)}px`;
  });

  elements.sendBtn.addEventListener("click", handleSend);

  // Ingest documents button
  elements.ingestBtn.addEventListener("click", async () => {
    elements.ingestBtn.disabled = true;
    elements.ingestBtn.textContent = "Ingesting...";
    try {
      const res = await API.ingestDocuments();
      alert(`Ingestion Successful!\n${res.total_chunks_indexed} chunks indexed across ${res.files_processed} files.`);
      await refreshDocumentsList();
      await refreshHealthStatus();
    } catch (err) {
      alert(`Ingestion Failed: ${err.message}`);
    } finally {
      elements.ingestBtn.disabled = false;
      elements.ingestBtn.innerHTML = "<span>🔄</span> Ingest Documents";
    }
  });

  // Clear chat
  elements.clearChatBtn.addEventListener("click", () => {
    state.sessionId = `session_${Date.now()}`;
    localStorage.setItem("genai_session_id", state.sessionId);
    elements.chatMessages.innerHTML = `
      <div class="empty-state" id="emptyState">
        <div class="empty-icon">🤖</div>
        <h2 class="empty-title">Local GenAI Data Assistant</h2>
        <p class="empty-desc">
          Ask questions about enterprise policy documents or query relational PostgreSQL database analytics.
        </p>
      </div>
    `;
  });

  // Sample prompt chips
  elements.sampleChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      elements.chatInput.value = chip.textContent.trim();
      handleSend();
    });
  });
}

/**
 * Handle user message submission
 */
async function handleSend() {
  const message = elements.chatInput.value.trim();
  if (!message || state.isProcessing) return;

  // Clear empty state if present
  const emptyState = document.getElementById("emptyState");
  if (emptyState) emptyState.remove();

  // Render user message
  appendUserMessage(message);
  elements.chatInput.value = "";
  elements.chatInput.style.height = "auto";

  // Set processing state
  setProcessing(true);
  const typingIndicator = appendTypingIndicator();

  try {
    const response = await API.sendMessage(message, state.sessionId);
    typingIndicator.remove();
    appendAssistantMessage(response);
  } catch (err) {
    typingIndicator.remove();
    appendErrorMessage(err.message);
  } finally {
    setProcessing(false);
  }
}

/**
 * Renders user message bubble
 */
function appendUserMessage(text) {
  const msgEl = document.createElement("div");
  msgEl.className = "message user";
  msgEl.innerHTML = `
    <div class="avatar">👤</div>
    <div class="message-content">
      <div class="bubble">${escapeHTML(text)}</div>
    </div>
  `;
  elements.chatMessages.appendChild(msgEl);
  scrollToBottom();
}

/**
 * Renders assistant message with intent badge, markdown, citations, and SQL logs
 */
function appendAssistantMessage(data) {
  const msgEl = document.createElement("div");
  msgEl.className = "message assistant";

  // Intent badge styling
  const intent = (data.intent || "rag").toLowerCase();
  const intentLabel = intent.toUpperCase();

  // Format citations if available
  let sourcesHTML = "";
  if (data.sources && data.sources.length > 0) {
    sourcesHTML = `
      <div class="meta-row">
        ${data.sources.map((src) => `<span class="source-badge">📄 ${escapeHTML(src)}</span>`).join("")}
      </div>
    `;
  }

  // Format SQL Accordion if query was executed
  let sqlHTML = "";
  if (data.sql_query) {
    const latency = data.sql_logs?.latency_ms ? `${data.sql_logs.latency_ms}ms` : "";
    const rows = data.sql_logs?.row_count !== undefined ? `${data.sql_logs.row_count} rows` : "";
    sqlHTML = `
      <details class="sql-accordion">
        <summary>⚡ View Executed SQL Query (${latency} ${rows})</summary>
        <pre class="sql-code-block"><code>${escapeHTML(data.sql_query)}</code></pre>
        ${data.sql_logs ? `<div class="sql-meta-info">Engine: ${data.sql_logs.db_type || "PostgreSQL"} • Timestamp: ${data.sql_logs.timestamp || ""}</div>` : ""}
      </details>
    `;
  }

  const formattedAnswer = renderMarkdown(data.answer);

  msgEl.innerHTML = `
    <div class="avatar">🤖</div>
    <div class="message-content">
      <div class="meta-row">
        <span class="intent-badge ${intent}">${intentLabel}</span>
      </div>
      <div class="bubble">
        ${formattedAnswer}
        ${sqlHTML}
      </div>
      ${sourcesHTML}
    </div>
  `;

  elements.chatMessages.appendChild(msgEl);
  scrollToBottom();
}

/**
 * Renders typing skeleton indicator
 */
function appendTypingIndicator() {
  const typingEl = document.createElement("div");
  typingEl.className = "message assistant";
  typingEl.innerHTML = `
    <div class="avatar">🤖</div>
    <div class="message-content">
      <div class="bubble typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>
  `;
  elements.chatMessages.appendChild(typingEl);
  scrollToBottom();
  return typingEl;
}

/**
 * Renders error message bubble
 */
function appendErrorMessage(errText) {
  const msgEl = document.createElement("div");
  msgEl.className = "message assistant";
  msgEl.innerHTML = `
    <div class="avatar" style="background: var(--accent-red);">⚠️</div>
    <div class="message-content">
      <div class="bubble" style="border-color: var(--accent-red); color: var(--accent-red);">
        <strong>Error:</strong> ${escapeHTML(errText)}
      </div>
    </div>
  `;
  elements.chatMessages.appendChild(msgEl);
  scrollToBottom();
}

/**
 * Fetch and render documents list in sidebar
 */
async function refreshDocumentsList() {
  try {
    const res = await API.getDocuments();
    state.documents = res.documents || [];
    elements.docCountBadge.textContent = `${res.total_documents || 0} Files`;

    if (state.documents.length === 0) {
      elements.docList.innerHTML = `<li style="font-size:12px; color:var(--text-muted);">No documents indexed yet.</li>`;
      return;
    }

    elements.docList.innerHTML = state.documents
      .map(
        (doc) => `
        <li class="doc-item">
          <span class="doc-name" title="${escapeHTML(doc.source)}">📄 ${escapeHTML(doc.source)}</span>
          <span class="doc-tag">${doc.chunks_count || 1} chunks</span>
        </li>
      `
      )
      .join("");
  } catch (err) {
    elements.docList.innerHTML = `<li style="font-size:12px; color:var(--accent-red);">Error loading docs</li>`;
  }
}

/**
 * Fetch and update health bar status
 */
async function refreshHealthStatus() {
  try {
    const health = await API.getHealth();
    const dbType = health.database?.type ? health.database.type.toUpperCase() : "DB";
    const qdrant = health.vector_store?.status === "connected" ? "Qdrant Online" : "Vector Ready";
    elements.healthStatusText.textContent = `${dbType} • ${qdrant} • ${health.llm_provider.toUpperCase()}`;
  } catch (err) {
    elements.healthStatusText.textContent = "Offline / Connecting...";
  }
}

function setProcessing(isProcessing) {
  state.isProcessing = isProcessing;
  elements.sendBtn.disabled = isProcessing;
  elements.chatInput.disabled = isProcessing;
  if (!isProcessing) {
    elements.chatInput.focus();
  }
}

function scrollToBottom() {
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

function escapeHTML(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/**
 * Lightweight, safe Markdown renderer for bold, lists, headers, code, tables
 */
function renderMarkdown(md) {
  if (!md) return "";
  let html = escapeHTML(md);

  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

  // Code blocks ```code```
  html = html.replace(/```([a-z]*)\n([\s\S]*?)```/g, "<pre><code>$2</code></pre>");

  // Inline code `code`
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Headers
  html = html.replace(/^### (.*$)/gim, "<h3>$1</h3>");
  html = html.replace(/^## (.*$)/gim, "<h2>$1</h2>");
  html = html.replace(/^# (.*$)/gim, "<h1>$1</h1>");

  // Tables
  if (html.includes("|")) {
    const lines = html.split("\n");
    let inTable = false;
    let tableHTML = "";
    const remaining = [];

    for (let line of lines) {
      if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
        if (!inTable) {
          inTable = true;
          tableHTML += "<table>";
        }
        // Header separator line |---|---|
        if (line.includes("---")) continue;

        const cells = line
          .split("|")
          .slice(1, -1)
          .map((c) => c.trim());
        const tag = tableHTML.includes("<tbody>") ? "td" : "th";
        if (tag === "td" && !tableHTML.includes("<tbody>")) {
          tableHTML += "<tbody>";
        }
        tableHTML += "<tr>" + cells.map((c) => `<${tag}>${c}</${tag}>`).join("") + "</tr>";
      } else {
        if (inTable) {
          inTable = false;
          tableHTML += "</tbody></table>";
          remaining.push(tableHTML);
          tableHTML = "";
        }
        remaining.push(line);
      }
    }
    if (inTable) {
      tableHTML += "</tbody></table>";
      remaining.push(tableHTML);
    }
    html = remaining.join("\n");
  }

  // Bullet points
  html = html.replace(/^\s*[-*]\s+(.*$)/gim, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>");

  // Line breaks
  html = html.replace(/\n\n/g, "<br><br>");

  return html;
}

// Boot application
init();
