from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional


@dataclass(frozen=True)
class YesNoQuestion:
    """Pergunta de sim/não no vocabulário do negócio. Não conhece nenhum fornecedor de IA."""

    instructions: str
    if_true: Optional[str] = None   # o que significa responder "sim"
    if_false: Optional[str] = None  # o que significa responder "não"


class JudgePort(ABC):
    """Julgador de perguntas de sim/não sobre um estado (texto ou estrutura).

    A aplicação depende só desta porta; o fornecedor (hoje o Jev, da TypeSafe) fica num adapter.
    """

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """False quando o fornecedor não está pronto (ex.: sem chave); quem chama volta ao plano B."""

    @abstractmethod
    async def probabilities(self, state: Any, questions: Mapping[str, YesNoQuestion]) -> Dict[str, float]:
        """Probabilidade (0 a 1) de resposta "sim" para cada pergunta, com as mesmas chaves de entrada.

        Perguntas independentes sobre o mesmo estado devem ir juntas: são avaliadas em uma só chamada.
        """
