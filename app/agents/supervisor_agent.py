import re
from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END
from app.agents.base_agent import AgentState
from app.services.core_services.retrieval_service import retrieval_service
from app.agents.retriever_agent import sql_agent
from app.llms.llm_factory import get_llm
from app.schemas.core_schemas.structured_output_schema import RouteDecision

# In-memory session store for conversation history
session_memory_store: Dict[str, List[Dict[str, str]]] = {}

def classify_intent(state: AgentState) -> Dict[str, Any]:
    """Classifies user query into 'general' (greetings/chitchat), 'rag' (documents), 'sql' (database), or 'combined' (both)."""
    question = state["question"]
    history = state.get("messages", [])

    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in history[-4:]]) if history else "None"

    # Fast-path for instant response on greetings, dismissals, and acknowledgments
    q_clean = re.sub(r"[^\w\s]", "", question.lower()).strip()
    tokens = q_clean.split()
    conversational_phrases = {
        "hi", "hii", "hello", "hey", "greetings", "howdy", "sup", "yo",
        "thanks", "thank you", "thx", "ok", "okay", "got it", "understood", "alright", "cool",
        "leave it", "leave that", "never mind", "nevermind", "forget it", "drop it", "cancel", "no worries"
    }
    if q_clean in conversational_phrases or (tokens and tokens[0] in {"hi", "hii", "hello", "hey"} and len(tokens) <= 4):
        return {"intent": "general"}
    if any(phrase in q_clean for phrase in [
        "leave it", "never mind", "nevermind", "forget it", "drop it",
        "good morning", "good afternoon", "good evening", "who are you", "what can you do", "help me"
    ]):
        return {"intent": "general"}

    prompt = (
        "You are an intelligent query router for an enterprise GenAI assistant.\n"
        "Classify the user's inquiry into exactly one of four categories:\n"
        "- 'general': Greetings, small talk, dismissals (e.g. 'leave it', 'never mind'), pleasantries (e.g. 'hi', 'thanks'), or questions asking who you are or what you can do.\n"
        "- 'sql': Inquiries about numerical data, orders, revenue, customer accounts, sales figures, product stock, or database tables.\n"
        "- 'rag': Inquiries about company policies, employee leave/PTO, SLAs, security guidelines, onboarding, employee manuals, or documentation.\n"
        "- 'combined': Inquiries that explicitly ask for BOTH policy/documentation information AND numerical database/order metrics.\n\n"
        f"### Recent Conversation History:\n{history_text}\n\n"
        f"### User Question:\n{question}\n\n"
        "Provide your routing decision as a structured object with 'intent' and 'reasoning'."
    )

    def _apply_heuristic(q: str) -> str:
        q_clean = re.sub(r"[^\w\s]", "", q.lower()).strip()
        tokens = q_clean.split()
        if q_clean in conversational_phrases or (tokens and tokens[0] in {"hi", "hii", "hello", "hey"} and len(tokens) <= 4):
            return "general"
        if any(phrase in q_clean for phrase in [
            "leave it", "never mind", "nevermind", "forget it", "drop it",
            "good morning", "good afternoon", "good evening", "who are you", "what can you do", "help me"
        ]):
            return "general"

        sql_keywords = ["order", "revenue", "customer", "sale", "price", "count", "top", "sum", "avg", "spend"]
        doc_keywords = ["policy", "pto", "sla", "rule", "conduct", "handbook", "guideline", "security", "vacation"]
        has_sql = any(k in q.lower() for k in sql_keywords)
        has_doc = any(k in q.lower() for k in doc_keywords) or ("leave" in q.lower() and "leave it" not in q_clean)
        if has_sql and has_doc:
            return "combined"
        elif has_sql:
            return "sql"
        return "rag"

    try:
        llm = get_llm(temperature=0.0)

        # 1. First-class structured output via Pydantic model
        if hasattr(llm, "with_structured_output"):
            try:
                structured_llm = llm.with_structured_output(RouteDecision)
                decision = structured_llm.invoke(prompt)
                if isinstance(decision, RouteDecision):
                    return {"intent": decision.intent, "reasoning": decision.reasoning}
                elif isinstance(decision, dict) and "intent" in decision:
                    valid_decision = RouteDecision.model_validate(decision)
                    return {"intent": valid_decision.intent, "reasoning": valid_decision.reasoning}
            except (NotImplementedError, Exception):
                pass

        # 2. Resilient Fallback: text extraction with Pydantic JSON validation
        response = llm.invoke(prompt)
        text_resp = response.content if hasattr(response, "content") else str(response)
        if isinstance(text_resp, list):
            text_resp = " ".join([p.get("text", "") for p in text_resp if isinstance(p, dict)])
        clean_text = str(text_resp).strip()

        # Try parsing JSON into RouteDecision
        if "{" in clean_text and "}" in clean_text:
            try:
                start = clean_text.find("{")
                end = clean_text.rfind("}")
                parsed = RouteDecision.model_validate_json(clean_text[start:end+1])
                return {"intent": parsed.intent, "reasoning": parsed.reasoning}
            except Exception:
                pass

        clean_intent = clean_text.lower()
        if "general" in clean_intent:
            intent = "general"
        elif "combined" in clean_intent:
            intent = "combined"
        elif "sql" in clean_intent:
            intent = "sql"
        elif "rag" in clean_intent:
            intent = "rag"
        else:
            intent = _apply_heuristic(question)
    except Exception:
        intent = _apply_heuristic(question)

    return {"intent": intent}


def rag_node(state: AgentState) -> Dict[str, Any]:
    """Handles questions requiring document search and retrieval."""
    res = retrieval_service.ask(state["question"])
    return {
        "rag_result": res,
        "final_answer": res["answer"],
        "sources": res.get("sources", []),
        "sql_logs": None
    }


def sql_node(state: AgentState) -> Dict[str, Any]:
    """Handles questions requiring PostgreSQL data analytics."""
    res = sql_agent.answer_question(state["question"])
    return {
        "sql_result": res,
        "final_answer": res["answer"],
        "sources": [],
        "sql_logs": res.get("logs")
    }


def combined_node(state: AgentState) -> Dict[str, Any]:
    """Handles multi-faceted questions needing both RAG documents and SQL data."""
    question = state["question"]
    rag_res = retrieval_service.ask(question)
    sql_res = sql_agent.answer_question(question)

    synthesis_prompt = (
        "You are an enterprise AI data assistant. Synthesize a single comprehensive, "
        "coherent response answering all parts of the user's question by combining the document context "
        "and database results below.\n\n"
        f"### User Question:\n{question}\n\n"
        f"### Document Findings:\n{rag_res.get('answer', 'N/A')}\n\n"
        f"### Database Analytics:\n{sql_res.get('answer', 'N/A')}\n"
        f"Executed SQL: {sql_res.get('sql_query', 'N/A')}\n\n"
        "### Final Combined Answer:"
    )

    llm = get_llm(temperature=0.2)
    try:
        response = llm.invoke(synthesis_prompt)
        text_resp = response.content if hasattr(response, "content") else str(response)
        if isinstance(text_resp, list):
            text_resp = " ".join([p.get("text", "") for p in text_resp if isinstance(p, dict)])
        final_answer = str(text_resp).strip()
    except Exception as e:
        final_answer = (
            f"**Document Policy:**\n{rag_res.get('answer')}\n\n"
            f"**Database Analytics:**\n{sql_res.get('answer')}"
        )

    return {
        "rag_result": rag_res,
        "sql_result": sql_res,
        "final_answer": final_answer,
        "sources": rag_res.get("sources", []),
        "sql_logs": sql_res.get("logs")
    }


def general_node(state: AgentState) -> Dict[str, Any]:
    """Handles conversational greetings, dismissals, acknowledgments, and bot capabilities."""
    q = state["question"].strip().lower()

    if any(k in q for k in ["thank", "thx"]):
        answer = "You're welcome! Let me know if you need anything else from our documents or database."
    elif any(k in q for k in ["leave it", "never mind", "nevermind", "forget it", "drop it", "cancel", "no worries", "leave that"]):
        answer = "No problem! Let me know whenever you're ready to query your documents or database."
    elif any(k in q for k in ["ok", "okay", "got it", "understood", "alright", "cool", "fine"]):
        answer = "Understood! Feel free to ask whenever you need help."
    else:
        answer = (
            "Hello! I am your enterprise GenAI Data Assistant. I can help you with:\n"
            "1. 📊 **Database Analytics (Text-to-SQL)**: Query customer data, revenue, orders, and sales figures.\n"
            "2. 📄 **Document Search (RAG)**: Search company policies, employee handbook, PTO, security protocols, and SLAs.\n\n"
            "How can I assist you today?"
        )
    return {
        "final_answer": answer,
        "sources": [],
        "sql_logs": None
    }


def route_decision(state: AgentState) -> str:
    """Routing condition for conditional edge."""
    intent = state.get("intent", "rag")
    if intent == "general":
        return "general_agent"
    elif intent == "sql":
        return "sql_agent"
    elif intent == "combined":
        return "combined_agent"
    return "rag_agent"


# Build the LangGraph State Machine
workflow = StateGraph(AgentState)

workflow.add_node("classifier", classify_intent)
workflow.add_node("general_agent", general_node)
workflow.add_node("rag_agent", rag_node)
workflow.add_node("sql_agent", sql_node)
workflow.add_node("combined_agent", combined_node)

workflow.add_edge(START, "classifier")
workflow.add_conditional_edges(
    "classifier",
    route_decision,
    {
        "general_agent": "general_agent",
        "rag_agent": "rag_agent",
        "sql_agent": "sql_agent",
        "combined_agent": "combined_agent"
    }
)
workflow.add_edge("general_agent", END)
workflow.add_edge("rag_agent", END)
workflow.add_edge("sql_agent", END)
workflow.add_edge("combined_agent", END)

orchestration_graph = workflow.compile()


def process_chat_message(message: str, session_id: str = "default") -> Dict[str, Any]:
    """High-level conversation coordinator with multi-turn history."""
    if session_id not in session_memory_store:
        session_memory_store[session_id] = []

    history = session_memory_store[session_id]

    initial_state: AgentState = {
        "session_id": session_id,
        "messages": history,
        "question": message,
        "intent": None,
        "rag_result": None,
        "sql_result": None,
        "final_answer": None,
        "sources": [],
        "sql_logs": None
    }

    final_state = orchestration_graph.invoke(initial_state)

    # Append to session history
    session_memory_store[session_id].append({"role": "user", "content": message})
    session_memory_store[session_id].append({"role": "assistant", "content": final_state.get("final_answer", "")})

    return {
        "session_id": session_id,
        "intent": final_state.get("intent"),
        "answer": final_state.get("final_answer"),
        "sources": final_state.get("sources", []),
        "sql_query": final_state.get("sql_result", {}).get("sql_query") if final_state.get("sql_result") else None,
        "sql_logs": final_state.get("sql_logs")
    }


def process_chat_stream(message: str, session_id: str = "default"):
    """
    High-level conversation coordinator yielding real-time events and token chunks.
    Yields events:
      - {"type": "status", "step": "..."}
      - {"type": "intent", "intent": "..."}
      - {"type": "sources", "sources": [...]}
      - {"type": "sql_query", "query": "...", "logs": {...}}
      - {"type": "token", "content": "..."}
      - {"type": "done", "session_id": "...", "final_answer": "...", ...}
    """
    if session_id not in session_memory_store:
        session_memory_store[session_id] = []

    history = session_memory_store[session_id]

    yield {"type": "status", "step": "Analyzing query intent..."}

    initial_state: AgentState = {
        "session_id": session_id,
        "messages": history,
        "question": message,
        "intent": None,
        "rag_result": None,
        "sql_result": None,
        "final_answer": None,
        "sources": [],
        "sql_logs": None
    }

    # 1. Classify intent
    class_res = classify_intent(initial_state)
    intent = class_res["intent"]
    yield {"type": "intent", "intent": intent}

    full_tokens = []
    sources = []
    sql_query = None
    sql_logs = None

    if intent == "general":
        yield {"type": "status", "step": "Generating response..."}
        gen_res = general_node(initial_state)
        final_answer = gen_res["final_answer"]
        words = final_answer.split(" ")
        for i, w in enumerate(words):
            token = w + (" " if i < len(words) - 1 else "")
            full_tokens.append(token)
            yield {"type": "token", "content": token}

    elif intent == "rag":
        yield {"type": "status", "step": "Searching knowledge base in vector database..."}
        hits = retrieval_service.retrieve(message, top_k=3)
        relevant_hits = [h for h in hits if h.get("score", 0) >= 0.40]

        if not relevant_hits:
            yield {"type": "status", "step": "No matching documents found, providing guidance..."}
            fallback_res = retrieval_service.ask(message)
            final_answer = fallback_res["answer"]
            words = final_answer.split(" ")
            for i, w in enumerate(words):
                token = w + (" " if i < len(words) - 1 else "")
                full_tokens.append(token)
                yield {"type": "token", "content": token}
        else:
            sources = list({h["metadata"].get("source", "Unknown") for h in relevant_hits})
            yield {"type": "sources", "sources": sources}
            yield {"type": "status", "step": f"Found {len(relevant_hits)} relevant document chunk(s). Synthesizing answer..."}

            available_docs = [d.get("source") for d in retrieval_service.vector_store.list_documents() if d.get("source")]
            docs_summary = ", ".join(sorted(set(available_docs))[:5]) if available_docs else "company policies and guides"

            context_text = "\n\n---\n\n".join(
                f"[Source: {hit['metadata'].get('source', 'Unknown')} - Score: {hit['score']:.2f}]\n{hit['content']}"
                for hit in relevant_hits
            )
            prompt = (
                "You are a helpful, accurate, and polite enterprise AI assistant.\n"
                "Answer the user's question clearly and accurately using the provided context below.\n"
                "If the answer cannot be found in the context, do NOT say 'The information is not available in the provided context'. "
                f"Instead, politely explain that details on that specific topic were not found in the current documents ({docs_summary}), "
                "and invite the user to upload the relevant file using the 'Upload Document' button in the sidebar.\n\n"
                f"### Context:\n{context_text}\n\n"
                f"### Question:\n{message}\n\n"
                "### Answer:"
            )

            llm = get_llm(temperature=0.2)
            try:
                for chunk in llm.stream(prompt):
                    content = chunk.content if hasattr(chunk, "content") else str(chunk)
                    if isinstance(content, list):
                        content = " ".join([p.get("text", "") for p in content if isinstance(p, dict)])
                    if content:
                        full_tokens.append(content)
                        yield {"type": "token", "content": content}
            except Exception:
                resp = llm.invoke(prompt)
                content = resp.content if hasattr(resp, "content") else str(resp)
                full_tokens.append(str(content))
                yield {"type": "token", "content": str(content)}

    elif intent == "sql":
        yield {"type": "status", "step": "Inspecting database schema..."}
        yield {"type": "status", "step": "Generating and validating SQL query..."}
        sql_res = sql_agent.answer_question(message)
        sql_query = sql_res.get("sql_query")
        sql_logs = sql_res.get("logs")

        if sql_query:
            yield {"type": "sql_query", "query": sql_query, "logs": sql_logs}

        yield {"type": "status", "step": "Formatting database insights..."}
        answer = sql_res.get("answer", "")
        words = answer.split(" ")
        for i, w in enumerate(words):
            token = w + (" " if i < len(words) - 1 else "")
            full_tokens.append(token)
            yield {"type": "token", "content": token}

    elif intent == "combined":
        yield {"type": "status", "step": "Querying both document knowledge base and database..."}
        rag_res = retrieval_service.ask(message)
        sql_res = sql_agent.answer_question(message)

        sources = rag_res.get("sources", [])
        if sources:
            yield {"type": "sources", "sources": sources}

        sql_query = sql_res.get("sql_query")
        sql_logs = sql_res.get("logs")
        if sql_query:
            yield {"type": "sql_query", "query": sql_query, "logs": sql_logs}

        yield {"type": "status", "step": "Synthesizing unified response with AI..."}

        synthesis_prompt = (
            "You are an enterprise AI data assistant. Synthesize a single comprehensive, "
            "coherent response answering all parts of the user's question by combining the document context "
            "and database results below.\n\n"
            f"### User Question:\n{message}\n\n"
            f"### Document Findings:\n{rag_res.get('answer', 'N/A')}\n\n"
            f"### Database Analytics:\n{sql_res.get('answer', 'N/A')}\n\n"
            f"Executed SQL: {sql_res.get('sql_query', 'N/A')}\n\n"
            "### Final Combined Answer:"
        )

        llm = get_llm(temperature=0.2)
        try:
            for chunk in llm.stream(synthesis_prompt):
                content = chunk.content if hasattr(chunk, "content") else str(chunk)
                if isinstance(content, list):
                    content = " ".join([p.get("text", "") for p in content if isinstance(p, dict)])
                if content:
                    full_tokens.append(content)
                    yield {"type": "token", "content": content}
        except Exception:
            resp = llm.invoke(synthesis_prompt)
            content = resp.content if hasattr(resp, "content") else str(resp)
            full_tokens.append(str(content))
            yield {"type": "token", "content": str(content)}

    final_answer_str = "".join(full_tokens).strip()

    # Save to session memory
    session_memory_store[session_id].append({"role": "user", "content": message})
    session_memory_store[session_id].append({"role": "assistant", "content": final_answer_str})

    yield {
        "type": "done",
        "session_id": session_id,
        "intent": intent,
        "final_answer": final_answer_str,
        "sources": sources,
        "sql_query": sql_query,
        "sql_logs": sql_logs
    }
