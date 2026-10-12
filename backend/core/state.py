from typing import TypedDict, Optional, Any

# ---------------------------------------------------------------------------
# State Definition
# ---------------------------------------------------------------------------

class AgentState(TypedDict, total=False):
    """Full state held by the LangGraph agent."""

    session_id: str
    user_message: str
    chat_history: list[dict]  # each entry: {id, role, content, timestamp}
    optimized_query: Optional[str]
    retrieved_docs: list[dict]  # each entry: {id, content, score, metadata}
    is_relevant: bool
    is_injection: bool
    is_greeting: bool
    is_hallucination: bool
    refusal_reason: Optional[str]
    final_response: Optional[str]
    abnt_references: list[str]  # References formatted according to ABNT NBR 6023
    _vector_repository: Any
    _llm_provider: Any
    _validator_llm: Any
    _judge: Any
    _route: Optional[str]
