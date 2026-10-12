"""Rotas de cadastro e login do chat."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import current_user_id, issue_token
from api.container import _auth_service, _user_adapter
from core.application.auth_service import AuthError

router = APIRouter()


class RegisterRequest(BaseModel):
    nome: str
    email: str
    senha: str


class LoginRequest(BaseModel):
    email: str
    senha: str


def _session(user) -> dict:
    return {"token": issue_token(user.id), "user": {"id": user.id, "nome": user.nome, "email": user.email}}


@router.post("/api/auth/register", status_code=201)
async def register(req: RegisterRequest):
    try:
        user = await _auth_service.register(req.nome, req.email, req.senha)
    except AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _session(user)


@router.post("/api/auth/login")
async def login(req: LoginRequest):
    try:
        user = await _auth_service.login(req.email, req.senha)
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return _session(user)


@router.get("/api/auth/me")
async def me(user_id: Optional[str] = Depends(current_user_id)):
    user = await _user_adapter.get_by_id(user_id) if user_id else None
    if user is None:
        raise HTTPException(status_code=401, detail="Sessão inválida.")
    return {"id": user.id, "nome": user.nome, "email": user.email}
