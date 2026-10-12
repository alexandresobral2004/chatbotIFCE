"""Port interface for the vector store (pgvector / document retrieval).

This port is agnostic to the underlying vector database implementation.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel


class RetrievedChunk(BaseModel):
    id: str
    content: str
    metadata: dict
    score: float


class VectorRepositoryPort(ABC):
    """Abstract interface for semantic document search."""

    @abstractmethod
    async def search_similar_chunks(
        self,
        query: str,
        limit: int = 5,
        threshold: float = 0.7,
    ) -> List[str]:
        """Search for document chunks most similar to the given query text.

        This method handles:
        1. Converting the query string to a vector embedding (using the injected
           embeddings provider).
        2. Running a similarity search against the vector store.
        3. Returning only the raw content strings of the top-K results.

        Args:
            query: The user's query as a plain string.
            limit: Maximum number of chunks to return.
            threshold: Minimum similarity score (0.0–1.0) required to include a result.

        Returns:
            List of content strings (one per matching chunk) ordered by relevance.
        """
        ...

    @abstractmethod
    async def upsert_chunk(
        self,
        content: str,
        metadata: Optional[dict] = None,
    ) -> str:
        """Insert or update a document chunk with its vector embedding.

        Args:
            content: The text content of the chunk.
            metadata: Optional arbitrary metadata (e.g. source, page number).

        Returns:
            The identifier of the upserted chunk.
        """
        ...

    @abstractmethod
    async def delete_chunk(self, chunk_id: str) -> None:
        """Remove a chunk from the vector store.

        Args:
            chunk_id: The identifier of the chunk to delete.
        """
        ...
