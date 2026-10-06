from typing import TypedDict, List, Dict, Any, Optional, Annotated


def add_messages(
    existing: Optional[List[Dict[str, str]]],
    new: Optional[List[Dict[str, str]]]
) -> List[Dict[str, str]]:
    """Safely merges conversational turns into thread state across multi-turn interactions."""
    left = list(existing) if existing else []
    right = list(new) if new else []
    return left + right


class AgentState(TypedDict):
    """LangGraph agent state representing conversational context and execution nodes."""
    session_id: str
    messages: Annotated[List[Dict[str, str]], add_messages]
    question: str
    intent: Optional[str]            # 'general', 'rag', 'sql', or 'combined'
    rag_result: Optional[Dict[str, Any]]
    sql_result: Optional[Dict[str, Any]]
    final_answer: Optional[str]
    sources: List[str]
    sql_logs: Optional[Dict[str, Any]]
