import re
from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END
from app.agents.base_agent import AgentState
from app.services.core_services.retrieval_service import retrieval_service
from app.agents.retriever_agent import sql_agent
from app.llms.llm_factory import get_llm

# In-memory session store for conversation history
session_memory_store: Dict[str, List[Dict[str, str]]] = {}

def classify_intent(state: AgentState) -> Dict[str, Any]:
    """Classifies user query into 'rag' (documents), 'sql' (database), or 'combined' (both)."""
    question = state["question"]
    history = state.get("messages", [])

    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in history[-4:]]) if history else "None"

    prompt = (
        "You are an intelligent query router for an enterprise GenAI assistant.\n"
        "Classify the user's inquiry into exactly one of three categories:\n"
        "- 'sql': Inquiries about numerical data, orders, revenue, customer accounts, sales figures, product stock, or database tables.\n"
        "- 'rag': Inquiries about company policies, leave/PTO, SLAs, security guidelines, onboarding, employee manuals, or documentation.\n"
        "- 'combined': Inquiries that explicitly ask for BOTH policy/documentation information AND numerical database/order metrics.\n\n"
        f"### Recent Conversation History:\n{history_text}\n\n"
        f"### User Question:\n{question}\n\n"
        "Respond with ONLY one lowercase word: 'sql', 'rag', or 'combined'."
    )

    llm = get_llm(temperature=0.0)
    try:
        response = llm.invoke(prompt)
        text_resp = response.content if hasattr(response, "content") else str(response)
        if isinstance(text_resp, list):
            text_resp = " ".join([p.get("text", "") for p in text_resp if isinstance(p, dict)])
        clean_intent = text_resp.strip().lower()

        if "combined" in clean_intent:
            intent = "combined"
        elif "sql" in clean_intent:
            intent = "sql"
        elif "rag" in clean_intent:
            intent = "rag"
        else:
            # Fallback heuristic
            sql_keywords = ["order", "revenue", "customer", "sale", "price", "count", "top", "sum", "avg", "spend"]
            doc_keywords = ["policy", "leave", "pto", "sla", "rule", "conduct", "handbook", "guideline", "security"]
            has_sql = any(k in question.lower() for k in sql_keywords)
            has_doc = any(k in question.lower() for k in doc_keywords)
            if has_sql and has_doc:
                intent = "combined"
            elif has_sql:
                intent = "sql"
            else:
                intent = "rag"
    except Exception:
        intent = "rag"

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


def route_decision(state: AgentState) -> str:
    """Routing condition for conditional edge."""
    intent = state.get("intent", "rag")
    if intent == "sql":
        return "sql_agent"
    elif intent == "combined":
        return "combined_agent"
    return "rag_agent"


# Build the LangGraph State Machine
workflow = StateGraph(AgentState)

workflow.add_node("classifier", classify_intent)
workflow.add_node("rag_agent", rag_node)
workflow.add_node("sql_agent", sql_node)
workflow.add_node("combined_agent", combined_node)

workflow.add_edge(START, "classifier")
workflow.add_conditional_edges(
    "classifier",
    route_decision,
    {
        "rag_agent": "rag_agent",
        "sql_agent": "sql_agent",
        "combined_agent": "combined_agent"
    }
)
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
