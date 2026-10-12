from typing import Optional

import asyncpg

from ports.user_port import EmailAlreadyRegistered, UserRecord, UserRepositoryPort


class PostgresUserAdapter(UserRepositoryPort):
    def __init__(self, connection_string: str):
        self._dsn = connection_string
        self._pool: Optional[asyncpg.Pool] = None

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(dsn=self._dsn, min_size=1, max_size=5, command_timeout=30)
            await self._create_table()
        return self._pool

    async def _create_table(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    nome VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    senha_hash TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)

    @staticmethod
    def _record(row) -> Optional[UserRecord]:
        return UserRecord(str(row["id"]), row["nome"], row["email"], row["senha_hash"]) if row else None

    async def create(self, nome: str, email: str, senha_hash: str) -> UserRecord:
        pool = await self._get_pool()
        try:
            row = await pool.fetchrow(
                "INSERT INTO chat_users (nome, email, senha_hash) VALUES ($1, $2, $3) RETURNING *",
                nome, email, senha_hash,
            )
        except asyncpg.UniqueViolationError:
            raise EmailAlreadyRegistered(email)
        return self._record(row)

    async def get_by_email(self, email: str) -> Optional[UserRecord]:
        pool = await self._get_pool()
        return self._record(await pool.fetchrow("SELECT * FROM chat_users WHERE email = $1", email))

    async def get_by_id(self, user_id: str) -> Optional[UserRecord]:
        pool = await self._get_pool()
        return self._record(await pool.fetchrow("SELECT * FROM chat_users WHERE id = $1::uuid", user_id))
