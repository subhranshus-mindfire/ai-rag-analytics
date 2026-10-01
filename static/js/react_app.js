/**
 * React 18 Production Single-Page Application
 * Follows modern React component patterns, hooks, and clean state boundaries.
 */
import { API } from "./api.js";

const { useState, useEffect, useRef, createElement: h } = window.React || {};

/**
 * Message Bubble Component
 */
function MessageBubble({ message }) {
  const isUser = message.role === "user";

  if (isUser) {
    return h(
      "div",
      { className: "message user" },
      h("div", { className: "avatar" }, "👤"),
      h(
        "div",
        { className: "message-content" },
        h("div", { className: "bubble" }, message.content)
      )
    );
  }

  const intent = (message.intent || "rag").toLowerCase();

  return h(
    "div",
    { className: "message assistant" },
    h("div", { className: "avatar" }, "🤖"),
    h(
      "div",
      { className: "message-content" },
      message.intent &&
        h(
          "div",
          { className: "meta-row" },
          h(
            "span",
            { className: `intent-badge ${intent}` },
            intent.toUpperCase()
          )
        ),
      h(
        "div",
        { className: "bubble" },
        h("div", { style: { whiteSpace: "pre-wrap", lineHeight: "1.6" } }, message.content),
        message.sql_query &&
          h(
            "details",
            { className: "sql-accordion" },
            h(
              "summary",
              null,
              `⚡ View Executed SQL Query (${message.sql_logs?.latency_ms ? `${message.sql_logs.latency_ms}ms` : ""} ${message.sql_logs?.row_count !== undefined ? `${message.sql_logs.row_count} rows` : ""})`
            ),
            h(
              "pre",
              { className: "sql-code-block" },
              h("code", null, message.sql_query)
            ),
            message.sql_logs &&
              h(
                "div",
                { className: "sql-meta-info" },
                `Engine: ${message.sql_logs.db_type || "PostgreSQL"} • ${message.sql_logs.timestamp || ""}`
              )
          )
      ),
      message.sources &&
        message.sources.length > 0 &&
        h(
          "div",
          { className: "meta-row" },
          message.sources.map((src, i) =>
            h("span", { key: i, className: "source-badge" }, `📄 ${src}`)
          )
        )
    )
  );
}

/**
 * Header Component
 */
function Header({ health, onClearChat }) {
  const dbType = health?.database?.type ? health.database.type.toUpperCase() : "DB";
  const qdrantStatus = health?.vector_store?.status === "connected" ? "Qdrant Online" : "Vector Ready";
  const provider = health?.llm_provider ? health.llm_provider.toUpperCase() : "AI";

  return h(
    "header",
    { className: "chat-header" },
    h(
      "div",
      { className: "header-status" },
      h("div", { className: "status-indicator" }),
      h("span", null, `${dbType} • ${qdrantStatus} • ${provider}`)
    ),
    h(
      "div",
      null,
      h(
        "button",
        {
          type: "button",
          className: "btn-secondary",
          onClick: onClearChat,
          style: { padding: "6px 12px", fontSize: "12px" },
        },
        h("span", null, "🗑️"),
        " New Chat"
      )
    )
  );
}

/**
 * Sidebar Component
 */
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
      h("div", { className: "logo-badge" }, "⚛️"),
      h(
        "div",
        null,
        h("div", { className: "app-title" }, "GenAI Assistant"),
        h("div", { className: "app-subtitle" }, "React 18 • RAG & SQL")
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
          h("span", { className: "doc-tag" }, `${documents.length} Files`)
        ),
        h(
          "ul",
          { className: "doc-list" },
          documents.length === 0
            ? h("li", { style: { fontSize: "12px", color: "var(--text-muted)" } }, "No documents indexed.")
            : documents.map((doc) =>
                h(
                  "li",
                  { key: doc.document_id || doc.source, className: "doc-item" },
                  h("span", { className: "doc-name", title: doc.source }, `📄 ${doc.source}`),
                  h("span", { className: "doc-tag" }, `${doc.chunks_count || 1} chunks`)
                )
              )
        )
      ),
      h(
        "div",
        null,
        h("div", { className: "section-label" }, "Example Inquiries"),
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
          className: "btn-secondary",
          disabled: isIngesting,
          onClick: onIngest,
        },
        h("span", null, "🔄"),
        isIngesting ? " Ingesting..." : " Ingest Documents"
      )
    )
  );
}

/**
 * Chat Input Component
 */
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
    "footer",
    { className: "chat-input-container" },
    h(
      "div",
      { className: "input-box" },
      h("textarea", {
        ref: textareaRef,
        className: "chat-textarea",
        rows: 1,
        placeholder: "Ask a document question, SQL analytical query, or combined inquiry...",
        value: input,
        onChange: handleChange,
        onKeyDown: handleKeyDown,
        disabled: isProcessing,
      }),
      h(
        "button",
        {
          type: "button",
          className: "send-btn",
          disabled: isProcessing || !input.trim(),
          onClick: onSend,
        },
        h("span", null, "Send "),
        h("span", null, "➤")
      )
    )
  );
}

/**
 * Root Application Component
 */
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
      console.error(err);
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
          content: `⚠️ Error: ${err.message}`,
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
      alert(`Ingestion Successful!\n${res.total_chunks_indexed} chunks indexed across ${res.files_processed} files.`);
      await loadData();
    } catch (err) {
      alert(`Ingestion Failed: ${err.message}`);
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
        messages.length === 0
          ? h(
              "div",
              { className: "empty-state" },
              h("div", { className: "empty-icon" }, "⚛️"),
              h("h2", { className: "empty-title" }, "Local GenAI Assistant (React 18)"),
              h(
                "p",
                { className: "empty-desc" },
                "Ask questions about enterprise policy documents, query relational PostgreSQL database analytics, or perform combined multi-agent synthesis."
              )
            )
          : messages.map((msg, i) => h(MessageBubble, { key: i, message: msg })),
        isProcessing &&
          h(
            "div",
            { className: "message assistant" },
            h("div", { className: "avatar" }, "🤖"),
            h(
              "div",
              { className: "message-content" },
              h(
                "div",
                { className: "bubble typing-indicator" },
                h("div", { className: "typing-dot" }),
                h("div", { className: "typing-dot" }),
                h("div", { className: "typing-dot" })
              )
            )
          ),
        h("div", { ref: messagesEndRef })
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
