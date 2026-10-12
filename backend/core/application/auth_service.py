"""Cadastro e login: regras de senha e e-mail. Não conhece banco nem HTTP (só a porta de usuários)."""
import base64
import hashlib
import hmac
import os
import re
from typing import Optional

from ports.user_port import EmailAlreadyRegistered, UserRecord, UserRepositoryPort

MIN_PASSWORD_LENGTH = 8
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_N, _R, _P = 2**14, 8, 1


class AuthError(Exception):
    """Erro de regra de negócio; a mensagem é segura para mostrar ao usuário."""


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_b64, digest_b64 = stored.split("$")
        salt, expected = base64.b64decode(salt_b64), base64.b64decode(digest_b64)
    except ValueError:
        return False
    actual = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return hmac.compare_digest(actual, expected)


class AuthService:
    def __init__(self, users: UserRepositoryPort):
        self._users = users

    async def register(self, nome: str, email: str, senha: str) -> UserRecord:
        nome, email = nome.strip(), email.strip().lower()
        if not nome:
            raise AuthError("Informe o nome.")
        if not _EMAIL.match(email):
            raise AuthError("E-mail inválido.")
        if len(senha) < MIN_PASSWORD_LENGTH:
            raise AuthError(f"A senha precisa ter pelo menos {MIN_PASSWORD_LENGTH} caracteres.")
        try:
            return await self._users.create(nome, email, hash_password(senha))
        except EmailAlreadyRegistered:
            raise AuthError("Este e-mail já está cadastrado.")

    async def login(self, email: str, senha: str) -> UserRecord:
        user: Optional[UserRecord] = await self._users.get_by_email(email.strip().lower())
        # Mesma mensagem para e-mail inexistente e senha errada: não revela quais e-mails existem.
        if user is None or not verify_password(senha, user.senha_hash):
            raise AuthError("E-mail ou senha incorretos.")
        return user
