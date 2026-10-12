import os
import httpx
from typing import List, Dict, Any, Optional, AsyncGenerator
import json
from core.observability import track_llm_usage


DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEEPSEEK_EMBEDDING_MODEL = os.getenv("DEEPSEEK_EMBEDDING_MODEL", "text-embedding-3-small")


class DeepSeekAdapter:
    """Adapter for DeepSeek API - OpenAI compatible."""

    def __init__(self, api_key: str = None, model: str = None, base_url: str = None, usage_adapter=None):
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.model = model or DEEPSEEK_MODEL
        self.base_url = (base_url or DEEPSEEK_BASE_URL).rstrip("/")
        self.usage_adapter = usage_adapter
        self._client: Optional[httpx.AsyncClient] = None
        self._is_configured = bool(self.api_key)

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=120.0,
                headers=headers,
            )
        return self._client

    async def close(self):
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def list_models(self) -> List[str]:
        client = self._get_client()
        try:
            response = await client.get("/models")
            response.raise_for_status()
            data = response.json()
            return [m.get("id", m) if isinstance(m, dict) else m for m in data.get("data", [])]
        except Exception:
            return [self.model]

    @track_llm_usage(provider="deepseek", endpoint_name="chat")
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        payload = {
            "model": model or self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }
        if stream:
            async with client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        data = line[5:].strip()
                        if not data or data == "[DONE]":
                            if data == "[DONE]":
                                break
                            continue
                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk and chunk["choices"]:
                                delta = chunk["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            continue
        else:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            yield data["choices"][0]["message"]["content"]

    @track_llm_usage(provider="deepseek", endpoint_name="embed")
    async def embed(self, text: str, model: Optional[str] = None) -> List[float]:
        client = self._get_client()
        payload = {
            "model": model or DEEPSEEK_EMBEDDING_MODEL,
            "input": text,
        }
        response = await client.post("/embeddings", json=payload)
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]

    @track_llm_usage(provider="deepseek", endpoint_name="embed_batch")
    async def embed_batch(self, texts: List[str], model: Optional[str] = None) -> List[List[float]]:
        client = self._get_client()
        payload = {
            "model": model or DEEPSEEK_EMBEDDING_MODEL,
            "input": texts,
        }
        response = await client.post("/embeddings", json=payload)
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]
