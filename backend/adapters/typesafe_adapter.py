import os
from typing import Any, Dict, Mapping, Optional

from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul, Score, SystemOneResponse

from ports.judge_port import JudgePort, YesNoQuestion


TYPESAFE_API_KEY = os.getenv("TYPESAFE_API_KEY", "")
TYPESAFE_MODEL = os.getenv("TYPESAFE_MODEL", "jev-latest")

__all__ = ["TypeSafeAdapter", "Choice", "Noul", "Score"]


class TypeSafeAdapter(JudgePort):
    """Adapter para o Jev (TypeSafe System One).

    O Jev devolve julgamentos tipados (Noul = probabilidade de "sim", Choice = uma opcao
    de um conjunto, Score = posicao em niveis ordenados), nao texto gerado. O codigo
    decide o fluxo; o Jev fornece o julgamento semantico.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or TYPESAFE_API_KEY
        self.model = model or TYPESAFE_MODEL
        self._client: Optional[AsyncTypeSafeClient] = None
        self._is_configured = bool(self.api_key)

    @property
    def is_configured(self) -> bool:
        return self._is_configured

    def _get_client(self) -> AsyncTypeSafeClient:
        if self._client is None:
            self._client = AsyncTypeSafeClient(api_key=self.api_key, model=self.model)
        return self._client

    async def close(self):
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def judge(
        self,
        state: Any,
        questions: Mapping[str, "Noul | Choice | Score"],
    ) -> SystemOneResponse:
        """Avalia `state` contra varias perguntas tipadas em uma unica chamada.

        Perguntas independentes sobre o mesmo estado devem ir juntas: rodam em paralelo.
        Acesse os resultados por `response.nouls[id].noul`, `response.choices[id].choice`
        e `response.scores[id].score`.
        """
        if not self._is_configured:
            raise RuntimeError("TYPESAFE_API_KEY nao configurada.")
        return await self._get_client().system_one(state, questions)

    async def probabilities(self, state: Any, questions: Mapping[str, YesNoQuestion]) -> Dict[str, float]:
        """Implementa JudgePort: traduz YesNoQuestion para Noul e devolve só as probabilidades."""
        sdk_questions = {}
        for qid, q in questions.items():
            criteria = {k: v for k, v in (("true", q.if_true), ("false", q.if_false)) if v}
            sdk_questions[qid] = Noul(instructions=q.instructions, criteria=criteria) if criteria else Noul(instructions=q.instructions)
        response = await self.judge(state, sdk_questions)
        return {qid: response.nouls[qid].noul for qid in questions}
