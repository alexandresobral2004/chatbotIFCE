"""pgvector adapter for VectorRepositoryPort using asyncpg + pgvector + OpenAI embeddings."""

import asyncpg
import os
import uuid
from typing import List, Optional, Dict, Any

from ports.vector_port import VectorRepositoryPort, RetrievedChunk
from openai import AsyncOpenAI


class PgVectorAdapter(VectorRepositoryPort):
    """Concrete implementation of VectorRepositoryPort backed by pgvector + asyncpg."""

    def __init__(
        self,
        connection_string: str,
        openai_api_key: Optional[str] = None,
        openai_api_base: Optional[str] = None,
        embedding_model: str = "text-embedding-3-small",
        embedding_dim: int = 1536,
    ):
        self._dsn = connection_string
        self._pool: Optional[asyncpg.Pool] = None
        self._client = AsyncOpenAI(
            api_key=openai_api_key or os.getenv("OPENAI_API_KEY") or "dummy-key",
            base_url=openai_api_base or os.getenv("OPENAI_API_BASE"),
        )
        self._embedding_model = embedding_model
        self._embedding_dim = embedding_dim

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                dsn=self._dsn,
                min_size=1,
                max_size=5,
                command_timeout=30,
            )
        return self._pool

    async def _embed(self, text: str) -> List[float]:
        """Generate an embedding vector for the given text using OpenAI."""
        response = await self._client.embeddings.create(
            model=self._embedding_model,
            input=text,
        )
        return response.data[0].embedding

    @staticmethod
    def _vec_to_str(vec: List[float]) -> str:
        """asyncpg requires pgvector values as strings, not Python lists."""
        return "[" + ",".join(str(float(x)) for x in vec) + "]"

    async def search_similar_chunks(
        self,
        query: str,
        limit: int = 5,
        threshold: float = 0.7,
    ) -> List[str]:
        """Return the content strings of the top-K chunks closest to the query."""
        # 1. Embed the query
        query_vec = await self._embed(query)

        # 2. Search pgvector using cosine distance (<=>)
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT chunk_id, content, metadata,
                       1 - (embedding <=> $1) AS similarity
                FROM document_chunks
                WHERE 1 - (embedding <=> $1) >= $2
                ORDER BY embedding <=> $1
                LIMIT $3
                """,
                self._vec_to_str(query_vec),
                threshold,
                limit,
            )

        # 3. Return only content strings
        return [r["content"] for r in rows]

    async def upsert_chunk(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Insert or update a document chunk with its vector embedding."""
        vec = await self._embed(content)
        chunk_id = str(uuid.uuid4())

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO document_chunks (chunk_id, content, embedding, metadata)
                VALUES ($1, $2, $3, $4)
                """,
                chunk_id,
                content,
                self._vec_to_str(vec),
                metadata or {},
            )

        return chunk_id

    async def delete_chunk(self, chunk_id: str) -> None:
        """Remove a chunk from the vector store."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM document_chunks WHERE chunk_id = $1",
                chunk_id,
            )