from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    """LangGraph agent state representing conversational context and execution nodes."""
    session_id: str
    messages: List[Dict[str, str]]
    question: str
    intent: Optional[str]            # 'rag', 'sql', or 'combined'
    rag_result: Optional[Dict[str, Any]]
    sql_result: Optional[Dict[str, Any]]
    final_answer: Optional[str]
    sources: List[str]
    sql_logs: Optional[Dict[str, Any]]
