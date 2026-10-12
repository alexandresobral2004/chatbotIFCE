"""PostgreSQL adapter for ChatRepositoryPort using asyncpg."""

import asyncpg
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from ports.chat_port import ChatRepositoryPort, ChatMessageRecord


class PostgresChatAdapter(ChatRepositoryPort):
    """Concrete implementation of ChatRepositoryPort backed by asyncpg + PostgreSQL."""

    def __init__(self, connection_string: str):
        self._dsn = connection_string
        self._pool: Optional[asyncpg.Pool] = None

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                dsn=self._dsn,
                min_size=1,
                max_size=5,
                command_timeout=30,
            )
            # Run migration to add feedback and new columns if they don't exist
            async with self._pool.acquire() as conn:
                await conn.execute("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS feedback VARCHAR(10);")
                await conn.execute("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS processing_time_ms INTEGER;")
                await conn.execute("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS rag_version VARCHAR(50);")
                await conn.execute("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS model_version VARCHAR(50);")
        return self._pool

    async def get_history(self, session_id: str, limit: int = 100) -> List[ChatMessageRecord]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT message_id, session_id, role, content, timestamp,
                       is_streaming, status, feedback, processing_time_ms,
                       rag_version, model_version
                FROM chat_messages
                WHERE session_id = $1
                ORDER BY timestamp ASC
                LIMIT $2
                """,
                session_id,
                limit,
            )
        return [
            ChatMessageRecord(
                id=str(r["message_id"]),
                session_id=str(r["session_id"]),
                role=r["role"],
                content=r["content"],
                timestamp=r["timestamp"].isoformat(),
                is_streaming=r["is_streaming"],
                status=r["status"],
                feedback=r.get("feedback"),
                processing_time_ms=r.get("processing_time_ms"),
                rag_version=r.get("rag_version"),
                model_version=r.get("model_version"),
            )
            for r in rows
        ]

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
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            # Ensure session exists
            await conn.execute(
                """
                INSERT INTO chat_sessions (session_id, user_id, updated_at)
                VALUES ($1, NULL, $2)
                ON CONFLICT (session_id) DO UPDATE SET updated_at = $2
                """,
                session_id,
                datetime.now(timezone.utc).replace(tzinfo=None),
            )

            # Insert the message
            message_id = await conn.fetchval(
                """
                INSERT INTO chat_messages (
                    session_id, role, content, is_streaming, status,
                    processing_time_ms, rag_version, model_version
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING message_id
                """,
                session_id,
                role,
                content,
                is_streaming,
                status,
                processing_time_ms,
                rag_version,
                model_version,
            )

        return ChatMessageRecord(
            id=str(message_id),
            session_id=session_id,
            role=role,
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
            is_streaming=is_streaming,
            status=status,
            processing_time_ms=processing_time_ms,
            rag_version=rag_version,
            model_version=model_version,
        )

    async def save_message_feedback(self, message_id: str, feedback: Optional[str]) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE chat_messages SET feedback = $1 WHERE message_id = $2",
                feedback,
                uuid.UUID(message_id) if len(message_id) == 36 else message_id,
            )

    async def clear_history(self, session_id: str) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM chat_messages WHERE session_id = $1",
                session_id,
            )

    async def claim_session(self, session_id: str, user_id: str) -> bool:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO chat_sessions (session_id, user_id) VALUES ($1, $2) ON CONFLICT (session_id) DO NOTHING",
                uuid.UUID(session_id), uuid.UUID(user_id),
            )
            owner = await conn.fetchval("SELECT user_id FROM chat_sessions WHERE session_id = $1", uuid.UUID(session_id))
        return owner is not None and str(owner) == user_id

    async def message_belongs_to(self, message_id: str, user_id: str) -> bool:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            owner = await conn.fetchval(
                "SELECT s.user_id FROM chat_messages m JOIN chat_sessions s ON s.session_id = m.session_id WHERE m.message_id = $1",
                uuid.UUID(message_id),
            )
        return owner is not None and str(owner) == user_id
