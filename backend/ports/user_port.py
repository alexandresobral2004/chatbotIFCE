"""Porta de persistência de usuários do chat."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class UserRecord:
    id: str
    nome: str
    email: str
    senha_hash: str


class EmailAlreadyRegistered(Exception):
    pass


class UserRepositoryPort(ABC):
    @abstractmethod
    async def create(self, nome: str, email: str, senha_hash: str) -> UserRecord:
        """Cria o usuário; levanta EmailAlreadyRegistered se o e-mail já existir."""

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[UserRecord]: ...

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[UserRecord]: ...
