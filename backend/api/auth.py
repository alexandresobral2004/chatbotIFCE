"""Autenticação do chat: valida o JWT (HS256) emitido pelo sistema principal.

O sistema principal assina um token curto com o segredo compartilhado CHAT_JWT_SECRET (claim `sub` = id do usuário).
Em desenvolvimento local, CHAT_AUTH_REQUIRED=false libera o acesso sem token.
"""
import os
import time
from typing import Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False)


def _auth_required() -> bool:
    return os.getenv("CHAT_AUTH_REQUIRED", "true").lower() != "false"


def current_user_id(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)) -> Optional[str]:
    """Devolve o id do usuário do token; 401 se faltar ou for inválido (a menos que a auth esteja desligada)."""
    if not _auth_required():
        return None
    secret = os.getenv("CHAT_JWT_SECRET", "")
    if not secret:
        raise HTTPException(status_code=500, detail="CHAT_JWT_SECRET não configurado.")
    if credentials is None:
        raise HTTPException(status_code=401, detail="Token ausente.")
    try:
        payload = jwt.decode(credentials.credentials, secret, algorithms=["HS256"], options={"require": ["exp", "sub"]})
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    return str(payload["sub"])


TOKEN_TTL_SECONDS = int(os.getenv("CHAT_TOKEN_TTL_SECONDS", str(8 * 3600)))


def issue_token(user_id: str) -> str:
    """Emite o JWT de acesso (mesmo formato aceito por current_user_id)."""
    secret = os.getenv("CHAT_JWT_SECRET", "")
    if not secret:
        raise HTTPException(status_code=500, detail="CHAT_JWT_SECRET não configurado.")
    return jwt.encode({"sub": user_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS}, secret, algorithm="HS256")
