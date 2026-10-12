import json
from pathlib import Path
from typing import Any, Dict, Mapping

KNOWLEDGE_PATH = Path(__file__).resolve().parent.parent / "project_knowledge.json"


def load_project_knowledge() -> Dict[str, Any]:
    """Retrato do projeto gerado por scripts/build_project_knowledge.py."""
    return json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))


class ProjectKnowledgeService:
    """Faz o Jev julgar perguntas usando o retrato do projeto como contexto.

    O Jev nao guarda memoria entre chamadas: o conhecimento do projeto viaja no `state`
    de cada requisicao, junto com a pergunta do usuario.
    """

    def __init__(self, typesafe_adapter):
        self.typesafe = typesafe_adapter
        self.knowledge = load_project_knowledge()

    async def judge(self, user_input: str, questions: Mapping[str, Any]):
        state = {"projeto": self.knowledge, "entrada_do_usuario": user_input}
        return await self.typesafe.judge(state, questions)
