from abc import ABC, abstractmethod
from typing import Optional


class UsageLogPort(ABC):
    """Registro de uso de LLM (tokens, custo, latência). O core só precisa de gravar."""

    @abstractmethod
    async def log_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        total_cost: float,
        latency_ms: int,
        user_id: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> str:
        """Grava um uso e devolve o id do registro."""
