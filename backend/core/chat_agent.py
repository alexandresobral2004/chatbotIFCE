"""ChatAgent orchestration class.

This class implements the business logic for the RAG chat agent, coordinating
between the LangGraph state machine and the data access ports. It maintains
complete separation from database implementations and HTTP concerns.
"""

import asyncio
from typing import Optional, AsyncGenerator, Dict, Any, List
from datetime import datetime, timezone

from .state import AgentState
from .langgraph_flow import build_agent_graph


class ChatAgent:
    """High-level agent that processes user messages through the RAG pipeline."""

    def __init__(
        self,
        vector_repository,
        chat_repository,
        llm_provider,
        validator_llm=None,
        judge=None,
    ) -> None:
        self._vector_repository = vector_repository
        self._chat_repository = chat_repository
        self._llm_provider = llm_provider
        self._validator_llm = validator_llm or llm_provider
        self._judge = judge
        self._graph = build_agent_graph()

    async def process_message(self, session_id: str, user_message: str) -> dict:
        """Synchronous version for compatibility."""
        import time
        start_time = time.time()
        
        if not session_id or not user_message:
            raise ValueError("session_id and user_message must be non-empty strings")

        state: AgentState = {
            "session_id": session_id,
            "user_message": user_message,
            "chat_history": [],
            "optimized_query": None,
            "retrieved_docs": [],
            "is_relevant": False,
            "final_response": None,
            "abnt_references": [],
            "_vector_repository": self._vector_repository,
            "_chat_repository": self._chat_repository,
            "_llm_provider": self._llm_provider,
            "_validator_llm": self._validator_llm,
            "_judge": self._judge,
        }

        result = await self._graph.ainvoke(state)
        
        processing_time_ms = int((time.time() - start_time) * 1000)

        await self._chat_repository.save_message(
            session_id=session_id,
            role="user",
            content=user_message,
        )

        if result.get("final_response"):
            await self._chat_repository.save_message(
                session_id=session_id,
                role="assistant",
                content=result["final_response"],
                processing_time_ms=processing_time_ms,
                rag_version="1.0.0",
                model_version=getattr(self._llm_provider, "model", "unknown")
            )

        return {
            "final_response": result.get("final_response"),
            "session_id": result.get("session_id"),
            "retrieved_docs": result.get("retrieved_docs", []),
            "abnt_references": result.get("abnt_references", []),
            "is_relevant": result.get("is_relevant", False),
        }

    def _translate_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Translate LangGraph event to SSE-friendly payload."""
        event_type = event.get("event", "")

        # Node transition status mapping
        node_statuses = {
            "router": "Analisando intenção...",
            "optimizer": "Otimizando consulta acadêmica...",
            "retriever": "Buscando documentos científicos...",
            "grader": "Avaliando pertinência do contexto...",
            "generator": "Gerando resposta acadêmica...",
            "citation": "Formatando referências ABNT (NBR 6023)...",
        }

        if event_type == "on_chain_start":
            node_name = event.get("data", {}).get("node", "")
            if node_name:
                return {
                    "type": "status",
                    "status": node_statuses.get(node_name, "Processando..."),
                    "node": node_name,
                }
        elif event_type == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk:
                return {
                    "type": "token",
                    "content": chunk,
                }

        return None

    async def stream_events(
        self, session_id: str, user_message: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream events for SSE using astream (step-by-step)."""
        import time
        start_time = time.time()
        
        state: AgentState = {
            "session_id": session_id,
            "user_message": user_message,
            "chat_history": [],
            "optimized_query": None,
            "retrieved_docs": [],
            "is_relevant": False,
            "final_response": None,
            "_vector_repository": self._vector_repository,
            "_chat_repository": self._chat_repository,
            "_llm_provider": self._llm_provider,
            "_validator_llm": self._validator_llm,
            "_judge": self._judge,
        }

        try:
            result = await self._graph.ainvoke(state)

            yield {"type": "status", "status": "Gerando resposta...", "node": "generator"}

            final = result.get("final_response", "")
            for i in range(0, len(final), 20):
                yield {"type": "token", "content": final[i:i+20]}
                await asyncio.sleep(0.01)

            processing_time_ms = int((time.time() - start_time) * 1000)

            # Salva o histórico do usuário
            await self._chat_repository.save_message(
                session_id=session_id,
                role="user",
                content=user_message,
            )
            # Salva o histórico do assistant com os metadados
            await self._chat_repository.save_message(
                session_id=session_id,
                role="assistant",
                content=final,
                processing_time_ms=processing_time_ms,
                rag_version="1.0.0",
                model_version=getattr(self._llm_provider, "model", "unknown")
            )

        except Exception as e:
            yield {"type": "error", "error": str(e)}