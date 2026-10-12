"""Port interface for chat history persistence (PostgreSQL).

This port is agnostic to the underlying database implementation.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel


class ChatMessageRecord(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    timestamp: str
    is_streaming: bool = False
    status: str = "idle"
    feedback: Optional[str] = None
    processing_time_ms: Optional[int] = None
    rag_version: Optional[str] = None
    model_version: Optional[str] = None


class ChatRepositoryPort(ABC):
    """Abstract interface for persisting and retrieving chat messages."""

    @abstractmethod
    async def get_history(self, session_id: str, limit: int = 100) -> List[ChatMessageRecord]:
        """Retrieve all messages for a given session, ordered by timestamp.

        Args:
            session_id: Unique session identifier.
            limit: Maximum number of messages to return (most recent first).

        Returns:
            List of ChatMessageRecord objects.
        """
        ...

    @abstractmethod
    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        is_streaming: bool = False,
        status: str = "idle",
        processing_time_ms: Optional[int] = None,
        rag_version: Optional[str] = None,
        model_version: Optional[str] = None,
    ) -> ChatMessageRecord:
        """Persist a single message to the session.

        Args:
            session_id: Unique session identifier.
            role: "user" or "assistant".
            content: The text content of the message.
            is_streaming: Whether the message is still being streamed.
            status: Optional status string (e.g. "sending", "sent", "error").
            processing_time_ms: Optional processing time in milliseconds.
            rag_version: Optional RAG configuration version.
            model_version: Optional LLM model version used.

        Returns:
            The created ChatMessageRecord.
        """
        ...

    @abstractmethod
    async def save_message_feedback(self, message_id: str, feedback: Optional[str]) -> None:
        """Save user feedback (like/dislike) for a message.

        Args:
            message_id: Unique message identifier.
            feedback: "like", "dislike", or None.
        """
        ...

    @abstractmethod
    async def clear_history(self, session_id: str) -> None:
        """Delete all messages for a given session.

        Args:
            session_id: Unique session identifier.
        """
        ...

    @abstractmethod
    async def claim_session(self, session_id: str, user_id: str) -> bool:
        """Vincula a sessão ao usuário se ela for nova; True se a sessão é (ou passou a ser) dele.

        Sessões de outro usuário ou sem dono (legadas) devolvem False.
        """
        ...

    @abstractmethod
    async def message_belongs_to(self, message_id: str, user_id: str) -> bool:
        """True se a mensagem pertence a uma sessão do usuário."""
        ...
