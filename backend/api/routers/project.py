"""Rotas de perguntas sobre o projeto (Jev)."""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from api.auth import current_user_id
from api.container import get_project_knowledge_service

router = APIRouter()


class ProjectAskRequest(BaseModel):
    question: str


@router.post("/api/project/ask")
async def project_ask(req: ProjectAskRequest, _user_id: Optional[str] = Depends(current_user_id)):
    question = (req.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Pergunta vazia.")
    if len(question) > 500:
        raise HTTPException(status_code=400, detail="Pergunta muito longa (máximo 500 caracteres).")
    service = get_project_knowledge_service()
    if not service.typesafe.is_configured:
        raise HTTPException(status_code=503, detail="Jev não configurado (TYPESAFE_API_KEY ausente).")
    from adapters.typesafe_adapter import Noul, Choice
    try:
        result = await service.judge(question, {
            "coberto": Noul(instructions=(
                "A entrada do usuário pergunta sobre algo que o projeto (`projeto`) "
                "implementa ou registra no histórico de criação?"
            )),
            "area": Choice(
                instructions="Sobre qual área do projeto é a pergunta?",
                criteria={"backend": None, "frontend": None, "historico": None, "fora_do_projeto": None},
            ),
        })
    except Exception as e:
        logging.getLogger(__name__).exception("Falha ao consultar o Jev")
        raise HTTPException(status_code=502, detail=f"Falha ao consultar o Jev: {e}")
    return {
        "coberto": result.nouls["coberto"].noul,
        "area": result.choices["area"].choice,
    }
