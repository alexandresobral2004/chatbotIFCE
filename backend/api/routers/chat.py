"""Rotas do chat (streaming e feedback)."""
import json
import uuid
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from api.auth import current_user_id
from api.container import _postgres_chat_adapter, get_chat_agent
from core.chat_agent import ChatAgent

router = APIRouter()


class ChatRequest(BaseModel):
    """Pydantic model for chat request body."""
    user_message: str


class FeedbackRequest(BaseModel):
    """Pydantic model for message feedback."""
    feedback: Optional[str] = None


def _as_uuid(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except ValueError:
        raise HTTPException(status_code=400, detail="Identificador inválido.")


async def _ensure_session_access(session_id: str, user_id: Optional[str]) -> None:
    """Sessão é de quem a criou: outro usuário recebe 403. Sem auth (dev local) não há dono."""
    session_id = _as_uuid(session_id)
    if user_id is not None and not await _postgres_chat_adapter.claim_session(session_id, user_id):
        raise HTTPException(status_code=403, detail="Esta conversa pertence a outro usuário.")


# --- Endpoint: Streaming Chat with SSE ---
@router.post("/chat/{session_id}")
async def chat_stream(
    session_id: str,
    request: ChatRequest,
    chat_agent: ChatAgent = Depends(get_chat_agent),
    _user_id: Optional[str] = Depends(current_user_id),
) -> StreamingResponse:
    """POST /chat/{session_id} - Process a message through RAG pipeline with SSE streaming."""

    await _ensure_session_access(session_id, _user_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        async for payload in chat_agent.stream_events(session_id, request.user_message):
            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


# --- Endpoint: Save Message Feedback ---
@router.post("/chat/message/{message_id}/feedback")
async def save_feedback(
    message_id: str,
    request: FeedbackRequest,
    _user_id: Optional[str] = Depends(current_user_id),
):
    if _user_id is not None and not await _postgres_chat_adapter.message_belongs_to(_as_uuid(message_id), _user_id):
        raise HTTPException(status_code=403, detail="Esta mensagem pertence a outro usuário.")
    await _postgres_chat_adapter.save_message_feedback(message_id, request.feedback)
    return {"status": "ok"}
