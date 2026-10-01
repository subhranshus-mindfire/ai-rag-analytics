/**
 * Modern, Minimalist React 18 Single-Page Application
 * Zero-dependency, pure React components with integrated Markdown formatting and SVG iconography.
 */
import { API } from "./api.js";

const { useState, useEffect, useRef, createElement: h } = window.React || {};

// ==========================================
// Modern SVG Icons
// ==========================================
function IconSparkles({ size = 16, className = "" }) {
  return h(
    "svg",
    {
      width: size,
      height: size,
      viewBox: "0 0 24 24",
      fill: "none",
      stroke: "currentColor",
      strokeWidth: 2,
      strokeLinecap: "round",
      strokeLinejoin: "round",
      className,
    },
    h("path", { d: "m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3z" })
  );
}

function IconUser({ size = 16, className = "" }) {
  return h(
    "svg",
    {
      width: size,
      height: size,
      viewBox: "0 0 24 24",
      fill: "none",
      stroke: "currentColor",
      strokeWidth: 2,
      strokeLinecap: "round",
      strokeLinejoin: "round",
      className,
    },
    h("path", { d: "M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" }),
    h("circle", { cx: 12, cy: 7, r: 4 })
  );
}

function IconDocument({ size = 14, className = "" }) {
  return h(
    "svg",
    {
      width: size,
      height: size,
      viewBox: "0 0 24 24",
      fill: "none",
      stroke: "currentColor",
      strokeWidth: 2,
      strokeLinecap: "round",
      strokeLinejoin: "round",
      className,
    },
    h("path", { d: "M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" }),
    h("polyline", { points: "14 2 14 8 20 8" })
  );
}

function IconDatabase({ size = 14, className = "" }) {
  return h(
    "svg",
    {
      width: size,
      height: size,
      viewBox: "0 0 24 24",
      fill: "none",
      stroke: "currentColor",
      strokeWidth: 2,
      strokeLinecap: "round",
      strokeLinejoin: "round",
      className,
    },
    h("ellipse", { cx: 12, cy: 5, rx: 9, ry: 3 }),
    h("path", { d: "M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" }),
    h("path", { d: "M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" })
  );
}

function IconSend({ size = 16, className = "" }) {
  return h(
    "svg",
    {
      width: size,
      height: size,
      viewBox: "0 0 24 24",
      fill: "none",
      stroke: "currentColor",
      strokeWidth: 2.5,
      strokeLinecap: "round",
      strokeLinejoin: "round",
      className,
    },
    h("line", { x1: 12, y1: 19, x2: 12, y2: 5 }),
    h("polyline", { points: "5 12 12 5 19 12" })
  );
}

function IconTrash({ size = 14, className = "" }) {
  return h(
    "svg",
    {
      width: size,
      height: size,
      viewBox: "0 0 24 24",
      fill: "none",
      stroke: "currentColor",
      strokeWidth: 2,
      strokeLinecap: "round",
      strokeLinejoin: "round",
      className,
    },
    h("polyline", { points: "3 6 5 6 21 6" }),
    h("path", { d: "M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" })
  );
}

function IconRefresh({ size = 14, className = "" }) {
  return h(
    "svg",
    {
      width: size,
      height: size,
      viewBox: "0 0 24 24",
      fill: "none",
      stroke: "currentColor",
      strokeWidth: 2,
      strokeLinecap: "round",
      strokeLinejoin: "round",
      className,
    },
    h("path", { d: "M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" })
  );
}

function IconCopy({ size = 13, className = "" }) {
  return h(
    "svg",
    {
      width: size,
      height: size,
      viewBox: "0 0 24 24",
      fill: "none",
      stroke: "currentColor",
      strokeWidth: 2,
      strokeLinecap: "round",
      strokeLinejoin: "round",
      className,
    },
    h("rect", { width: 14, height: 14, x: 8, y: 8, rx: 2, ry: 2 }),
    h("path", { d: "M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" })
  );
}

// ==========================================
// Zero-Dependency Secure Markdown Formatter
// ==========================================
function parseMarkdown(md) {
  if (!md) return "";

  // 1. Escape HTML
  let html = md
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // 2. Fenced Code blocks
  html = html.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const raw = code.trim();
    const encoded = encodeURIComponent(raw);
    return `<div class="code-block-wrapper">
      <div class="code-block-header">
        <span>${lang || "code"}</span>
        <button type="button" class="copy-code-btn" onclick="navigator.clipboard.writeText(decodeURIComponent('${encoded}')).then(()=>{this.textContent='Copied!';setTimeout(()=>this.textContent='Copy',2000)})">Copy</button>
      </div>
      <pre><code>${raw}</code></pre>
    </div>`;
  });

  // 3. Tables
  html = html.replace(/((?:\|[^\n]+\|\r?\n)+)/g, (tableMatch) => {
    const rows = tableMatch.trim().split("\n").filter((r) => r.trim());
    if (rows.length < 2) return tableMatch;
    let tableHtml = '<div class="table-responsive"><table class="markdown-table">';
    rows.forEach((row, idx) => {
      if (row.includes("---")) return;
      const cols = row.split("|").filter((_, i, arr) => i > 0 && i < arr.length - 1);
      const tag = idx === 0 ? "th" : "td";
      tableHtml += "<tr>" + cols.map((c) => `<${tag}>${c.trim()}</${tag}>`).join("") + "</tr>";
    });
    tableHtml += "</table></div>";
    return tableHtml;
  });

  // 4. Inline code
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

  // 5. Headers
  html = html.replace(/^### (.*$)/gim, "<h3>$1</h3>");
  html = html.replace(/^## (.*$)/gim, "<h2>$1</h2>");
  html = html.replace(/^# (.*$)/gim, "<h1>$1</h1>");

  // 6. Bold & Italics
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");

  // 7. Blockquotes
  html = html.replace(/^\> (.*$)/gim, "<blockquote>$1</blockquote>");

  // 8. Unordered Lists
  html = html.replace(/^\s*[-*]\s+(.*$)/gim, "<ul><li>$1</li></ul>");
  html = html.replace(/<\/ul>\s*<ul>/g, "");

  // 9. Ordered Lists
  html = html.replace(/^\s*\d+\.\s+(.*$)/gim, "<ol><li>$1</li></ol>");
  html = html.replace(/<\/ol>\s*<ol>/g, "");

  // 10. Paragraphs
  html = html
    .split("\n\n")
    .map((chunk) => {
      const trimmed = chunk.trim();
      if (!trimmed) return "";
      if (
        trimmed.startsWith("<h") ||
        trimmed.startsWith("<ul") ||
        trimmed.startsWith("<ol") ||
        trimmed.startsWith("<div") ||
        trimmed.startsWith("<blockquote") ||
        trimmed.startsWith("<table")
      ) {
        return trimmed;
      }
      return `<p>${trimmed.replace(/\n/g, "<br/>")}</p>`;
    })
    .join("");

  return html;
}

// ==========================================
// SQL Accordion Component
// ==========================================
function SQLAccordion({ query, logs }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(query);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return h(
    "details",
    { className: "sql-card" },
    h(
      "summary",
      null,
      h("span", { style: { display: "flex", alignItems: "center", gap: "6px" } },
        h(IconDatabase, { size: 14 }),
        "Executed SQL Query"
      ),
      h(
        "div",
        { className: "sql-metrics" },
        logs?.latency_ms !== undefined &&
          h("span", { className: "metric-tag" }, `${logs.latency_ms}ms`),
        logs?.row_count !== undefined &&
          h("span", { className: "metric-tag" }, `${logs.row_count} rows`)
      )
    ),
    h(
      "div",
      { className: "sql-content" },
      h("pre", { className: "sql-code" }, query),
      h(
        "div",
        { className: "sql-footer" },
        h("span", null, `Engine: ${logs?.db_type || "PostgreSQL"}`),
        h(
          "button",
          {
            type: "button",
            className: "copy-code-btn",
            onClick: handleCopy,
          },
          copied ? "✓ Copied" : "Copy SQL"
        )
      )
    )
  );
}

// ==========================================
// Message Bubble Component
// ==========================================
function MessageBubble({ message }) {
  const isUser = message.role === "user";

  if (isUser) {
    return h(
      "div",
      { className: "message-row user" },
      h(
        "div",
        { className: "message-body" },
        h("div", { className: "user-bubble" }, message.content)
      ),
      h(
        "div",
        { className: "avatar-badge user-avatar" },
        h(IconUser, { size: 16 })
      )
    );
  }

  const intent = (message.intent || "rag").toLowerCase();
  const intentLabels = {
    rag: "Document RAG",
    sql: "SQL Analytics",
    combined: "Hybrid RAG + SQL",
    error: "System Notice",
  };

  const formattedHtml = parseMarkdown(message.content);

  return h(
    "div",
    { className: "message-row assistant" },
    h(
      "div",
      { className: "avatar-badge assistant-avatar" },
      h(IconSparkles, { size: 16 })
    ),
    h(
      "div",
      { className: "message-body" },
      message.intent &&
        h(
          "div",
          null,
          h(
            "span",
            { className: `intent-pill ${intent}` },
            intentLabels[intent] || intent.toUpperCase()
          )
        ),
      h(
        "div",
        { className: "assistant-bubble" },
        h("div", {
          className: "markdown-body",
          dangerouslySetInnerHTML: { __html: formattedHtml },
        }),
        message.sql_query &&
          h(SQLAccordion, { query: message.sql_query, logs: message.sql_logs }),
        message.sources &&
          message.sources.length > 0 &&
          h(
            "div",
            { className: "sources-container" },
            h("span", { className: "sources-label" }, "Sources:"),
            message.sources.map((src, i) =>
              h(
                "span",
                { key: i, className: "source-chip" },
                h(IconDocument, { size: 12 }),
                src
              )
            )
          )
      )
    )
  );
}

// ==========================================
// Header Component
// ==========================================
function Header({ health, onClearChat }) {
  const dbType = health?.database?.type ? health.database.type.toUpperCase() : "PostgreSQL";
  const vectorStore = health?.vector_store?.status === "connected" ? "Qdrant Ready" : "Vector DB";
  const provider = health?.llm_provider ? health.llm_provider.toUpperCase() : "Gemini / Groq";

  return h(
    "header",
    { className: "chat-header" },
    h(
      "div",
      { className: "header-status" },
      h(
        "div",
        { className: "status-badge" },
        h("div", { className: "status-pulse" }),
        h("span", null, `${dbType} · ${vectorStore} · ${provider}`)
      )
    ),
    h(
      "button",
      {
        type: "button",
        className: "btn-icon-label",
        onClick: onClearChat,
        title: "Start a fresh session",
      },
      h(IconTrash, { size: 13 }),
      h("span", null, "New Chat")
    )
  );
}

// ==========================================
// Sidebar Component
// ==========================================
function Sidebar({ documents, onSelectPrompt, onIngest, isIngesting }) {
  const samplePrompts = [
    "What is the company leave policy?",
    "Which are the top 5 customers by revenue?",
    "What is the refund policy and how much was refunded last month?",
    "What are the customer support SLA response times?",
  ];

  return h(
    "aside",
    { className: "sidebar" },
    h(
      "div",
      { className: "sidebar-header" },
      h(
        "div",
        { className: "sidebar-brand" },
        h(
          "div",
          { className: "brand-icon-wrapper" },
          h(IconSparkles, { size: 18 })
        ),
        h(
          "div",
          { className: "brand-text" },
          h("div", { className: "app-title" }, "Data Assistant"),
          h("div", { className: "app-subtitle" }, "LangGraph · RAG · SQL")
        )
      )
    ),
    h(
      "div",
      { className: "sidebar-content" },
      h(
        "div",
        null,
        h(
          "div",
          { className: "section-label" },
          h("span", null, "Knowledge Base"),
          h("span", { className: "doc-count-badge" }, `${documents.length} Files`)
        ),
        h(
          "ul",
          { className: "doc-list" },
          documents.length === 0
            ? h("li", { style: { fontSize: "12px", color: "var(--text-dim)", padding: "4px 8px" } }, "No documents indexed.")
            : documents.map((doc) => {
                const ext = (doc.source || "").split(".").pop().toUpperCase() || "DOC";
                return h(
                  "li",
                  { key: doc.document_id || doc.source, className: "doc-item" },
                  h(
                    "div",
                    { className: "doc-info" },
                    h(IconDocument, { size: 13, className: "doc-icon" }),
                    h("span", { className: "doc-name", title: doc.source }, doc.source)
                  ),
                  h("span", { className: "doc-tag" }, ext)
                );
              })
        )
      ),
      h(
        "div",
        null,
        h("div", { className: "section-label" }, "Suggested Queries"),
        h(
          "div",
          { className: "sample-queries" },
          samplePrompts.map((prompt, idx) =>
            h(
              "button",
              {
                key: idx,
                type: "button",
                className: "query-chip",
                onClick: () => onSelectPrompt(prompt),
              },
              prompt
            )
          )
        )
      )
    ),
    h(
      "div",
      { className: "sidebar-footer" },
      h(
        "button",
        {
          type: "button",
          className: "btn-sidebar",
          disabled: isIngesting,
          onClick: onIngest,
        },
        h(IconRefresh, { size: 14 }),
        h("span", null, isIngesting ? "Ingesting Documents..." : "Re-index Knowledge Base")
      )
    )
  );
}

// ==========================================
// Modern Chat Input Component
// ==========================================
function ChatInput({ input, setInput, onSend, isProcessing }) {
  const textareaRef = useRef(null);

  useEffect(() => {
    if (!isProcessing && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isProcessing]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  const handleChange = (e) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  };

  return h(
    "div",
    { className: "chat-input-wrapper" },
    h(
      "div",
      { className: "input-container" },
      h(
        "div",
        { className: "input-row" },
        h("textarea", {
          ref: textareaRef,
          className: "chat-textarea",
          rows: 1,
          placeholder: "Ask about company documents, query database analytics, or hybrid inquiries...",
          value: input,
          onChange: handleChange,
          onKeyDown: handleKeyDown,
          disabled: isProcessing,
        }),
        h(
          "button",
          {
            type: "button",
            className: "send-button",
            disabled: isProcessing || !input.trim(),
            onClick: onSend,
            title: "Send question (Enter)",
          },
          h(IconSend, { size: 16 })
        )
      ),
      h(
        "div",
        { className: "input-hint-row" },
        h("span", { className: "input-hint" }, "Enter to send · Shift+Enter for new line"),
        h("span", { className: "input-hint" }, "SELECT-only guardrails active")
      )
    )
  );
}

// ==========================================
// Welcome / Empty State Component
// ==========================================
function EmptyState({ onSelectPrompt }) {
  const starters = [
    {
      tag: "Document RAG",
      text: "What is the company leave policy?",
    },
    {
      tag: "SQL Analytics",
      text: "Which are the top 5 customers by revenue?",
    },
    {
      tag: "Hybrid Routing",
      text: "What is the refund policy and how much was refunded last month?",
    },
    {
      tag: "Document RAG",
      text: "What are the customer support SLA response times?",
    },
  ];

  return h(
    "div",
    { className: "empty-state" },
    h(
      "div",
      { className: "empty-icon-glow" },
      h(IconSparkles, { size: 28 })
    ),
    h("h2", { className: "empty-title" }, "Enterprise Data Assistant"),
    h(
      "p",
      { className: "empty-desc" },
      "Chat with company policy documents and query relational PostgreSQL database analytics in real time."
    ),
    h(
      "div",
      { className: "starter-grid" },
      starters.map((item, idx) =>
        h(
          "div",
          {
            key: idx,
            className: "starter-card",
            onClick: () => onSelectPrompt(item.text),
          },
          h("div", { className: "starter-tag" }, item.tag),
          h("div", { className: "starter-text" }, item.text)
        )
      )
    )
  );
}

// ==========================================
// Root Application Component
// ==========================================
export function App() {
  const [sessionId, setSessionId] = useState(() => {
    return localStorage.getItem("genai_react_session") || `session_${Date.now()}`;
  });
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [documents, setDocuments] = useState([]);
  const [health, setHealth] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);

  const messagesEndRef = useRef(null);

  useEffect(() => {
    localStorage.setItem("genai_react_session", sessionId);
  }, [sessionId]);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isProcessing]);

  const loadData = async () => {
    try {
      const [docsData, healthData] = await Promise.all([
        API.getDocuments().catch(() => ({ documents: [] })),
        API.getHealth().catch(() => null),
      ]);
      setDocuments(docsData.documents || []);
      setHealth(healthData);
    } catch (err) {
      console.error("Failed to load initial data:", err);
    }
  };

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || isProcessing) return;

    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setInput("");
    setIsProcessing(true);

    try {
      const res = await API.sendMessage(trimmed, sessionId);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.answer,
          intent: res.intent,
          sources: res.sources,
          sql_query: res.sql_query,
          sql_logs: res.sql_logs,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `⚠️ An error occurred: ${err.message}`,
          intent: "error",
        },
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleIngest = async () => {
    setIsIngesting(true);
    try {
      const res = await API.ingestDocuments();
      alert(`Knowledge base updated:\n${res.total_chunks_indexed} chunks indexed across ${res.files_processed} files.`);
      await loadData();
    } catch (err) {
      alert(`Ingestion failed: ${err.message}`);
    } finally {
      setIsIngesting(false);
    }
  };

  const handleClearChat = () => {
    setSessionId(`session_${Date.now()}`);
    setMessages([]);
  };

  return h(
    "div",
    { className: "app-container" },
    h(Sidebar, {
      documents,
      onSelectPrompt: (p) => setInput(p),
      onIngest: handleIngest,
      isIngesting,
    }),
    h(
      "main",
      { className: "chat-area" },
      h(Header, { health, onClearChat: handleClearChat }),
      h(
        "section",
        { className: "chat-messages" },
        h(
          "div",
          { className: "messages-inner" },
          messages.length === 0
            ? h(EmptyState, { onSelectPrompt: (p) => setInput(p) })
            : messages.map((msg, i) => h(MessageBubble, { key: i, message: msg })),
          isProcessing &&
            h(
              "div",
              { className: "message-row assistant" },
              h(
                "div",
                { className: "avatar-badge assistant-avatar" },
                h(IconSparkles, { size: 16 })
              ),
              h(
                "div",
                { className: "message-body" },
                h(
                  "div",
                  { className: "assistant-bubble typing-box" },
                  h("div", { className: "typing-dot" }),
                  h("div", { className: "typing-dot" }),
                  h("div", { className: "typing-dot" })
                )
              )
            ),
          h("div", { ref: messagesEndRef })
        )
      ),
      h(ChatInput, {
        input,
        setInput,
        onSend: handleSend,
        isProcessing,
      })
    )
  );
}

// Mount React Root
if (window.ReactDOM && window.React) {
  const root = window.ReactDOM.createRoot(document.getElementById("root"));
  root.render(h(App));
}
