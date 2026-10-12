import os
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import AsyncOpenAI
from core.observability import track_llm_usage

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_EMBEDDING_DIM = int(os.getenv("OPENAI_EMBEDDING_DIM", "1536"))


class OpenAIAdapter:
    """Adapter for OpenAI API with gpt-4o-mini and text-embedding-3-small."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        embedding_model: Optional[str] = None,
        usage_adapter=None,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.embedding_model = embedding_model or os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.usage_adapter = usage_adapter
        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY is not configured")
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def close(self):
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def list_models(self) -> List[str]:
        """List available OpenAI models."""
        client = self._get_client()
        try:
            response = await client.models.list()
            return [m.id for m in response.data if "gpt-4o" in m.id or "mini" in m.id or "embed" in m.id]
        except Exception:
            return [self.model, self.embedding_model]

    @track_llm_usage(provider="openai", endpoint_name="chat")
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stream: bool = False,
        reasoning_effort: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate chat completion with optional streaming.

        reasoning_effort only applies to reasoning models (gpt-5.x); response_format
        enables JSON mode / Structured Outputs.
        """
        client = self._get_client()
        target_model = model or self.model

        # Reasoning models (gpt-5.x) require max_completion_tokens and do not
        # support temperature (only the default value is accepted).
        is_reasoning = target_model.startswith("gpt-5")
        completion_kwargs: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
        }
        if response_format:
            completion_kwargs["response_format"] = response_format
        if is_reasoning:
            completion_kwargs["max_completion_tokens"] = max_tokens
            if reasoning_effort:
                completion_kwargs["reasoning_effort"] = reasoning_effort
        else:
            completion_kwargs["max_tokens"] = max_tokens
            completion_kwargs["temperature"] = temperature

        if stream:
            response_stream = await client.chat.completions.create(
                **completion_kwargs,
                stream=True,
            )
            async for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        else:
            response = await client.chat.completions.create(
                **completion_kwargs,
                stream=False,
            )
            yield response.choices[0].message.content or ""

    @track_llm_usage(provider="openai", endpoint_name="embed")
    async def embed(self, text: str, model: Optional[str] = None) -> List[float]:
        """Generate embedding vector for a single text."""
        client = self._get_client()
        target_model = model or self.embedding_model
        response = await client.embeddings.create(
            model=target_model,
            input=text,
        )
        return response.data[0].embedding

    @track_llm_usage(provider="openai", endpoint_name="embed_batch")
    async def embed_batch(self, texts: List[str], model: Optional[str] = None) -> List[List[float]]:
        """Generate embedding vectors for a batch of texts."""
        client = self._get_client()
        target_model = model or self.embedding_model
        response = await client.embeddings.create(
            model=target_model,
            input=texts,
        )
        return [item.embedding for item in response.data]
