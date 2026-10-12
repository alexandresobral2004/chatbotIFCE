import asyncpg
from typing import List, Dict, Any, Optional
import uuid
import datetime

from ports.usage_log_port import UsageLogPort


class PostgresUsageAdapter(UsageLogPort):
    def __init__(self, dsn: str):
        self.dsn = dsn

    async def initialize(self):
        conn = await asyncpg.connect(self.dsn)
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_usage_logs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id VARCHAR(50),
                    provider VARCHAR(50),
                    model VARCHAR(100),
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    total_cost NUMERIC(10, 6),
                    latency_ms INTEGER,
                    endpoint VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # nexus_users.id is a short string (e.g. "root", "1", or a uuid4 string),
            # not a UUID column type — widen user_id on tables created before this.
            await conn.execute("""
                ALTER TABLE llm_usage_logs ALTER COLUMN user_id TYPE VARCHAR(50) USING user_id::text
            """)
        finally:
            await conn.close()

    async def log_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        total_cost: float,
        latency_ms: int,
        user_id: Optional[str] = None,
        endpoint: Optional[str] = None
    ) -> str:
        conn = await asyncpg.connect(self.dsn)
        try:
            log_id = uuid.uuid4()
            await conn.execute("""
                INSERT INTO llm_usage_logs 
                (id, user_id, provider, model, input_tokens, output_tokens, total_cost, latency_ms, endpoint)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, log_id, user_id, provider, model, input_tokens, output_tokens, total_cost, latency_ms, endpoint)
            return str(log_id)
        finally:
            await conn.close()

    async def get_usage_summary(self, days: int = 30, user_id: Optional[str] = None) -> Dict[str, Any]:
        conn = await asyncpg.connect(self.dsn)
        try:
            user_filter = "AND user_id = $1" if user_id else ""
            args = [user_id] if user_id else []
            record = await conn.fetchrow(f"""
                SELECT
                    COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                    COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                    COALESCE(SUM(total_cost), 0) as total_cost_usd,
                    COUNT(id) as total_requests
                FROM llm_usage_logs
                WHERE created_at >= NOW() - INTERVAL '{days} days'
                {user_filter};
            """, *args)
            return dict(record) if record else {
                "total_input_tokens": 0, "total_output_tokens": 0, "total_cost_usd": 0, "total_requests": 0
            }
        finally:
            await conn.close()

    async def get_usage_by_provider(self, days: int = 30, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = await asyncpg.connect(self.dsn)
        try:
            user_filter = "AND user_id = $1" if user_id else ""
            args = [user_id] if user_id else []
            records = await conn.fetch(f"""
                SELECT
                    DATE(created_at) as date,
                    provider,
                    COALESCE(SUM(input_tokens), 0) as total_input,
                    COALESCE(SUM(output_tokens), 0) as total_output,
                    COUNT(id) as requests,
                    COALESCE(SUM(total_cost), 0) as cost
                FROM llm_usage_logs
                WHERE created_at >= NOW() - INTERVAL '{days} days'
                {user_filter}
                GROUP BY DATE(created_at), provider
                ORDER BY DATE(created_at) DESC, provider;
            """, *args)
            return [dict(r) for r in records]
        finally:
            await conn.close()

    async def attribute_unassigned_usage(self, user_id: str) -> int:
        """Backfill: assign every usage log with no user_id (rows logged before
        attribution existed) to the given user. Returns how many rows changed."""
        conn = await asyncpg.connect(self.dsn)
        try:
            result = await conn.execute(
                "UPDATE llm_usage_logs SET user_id = $1 WHERE user_id IS NULL", user_id
            )
            # asyncpg returns e.g. "UPDATE 20"
            return int(result.split(" ")[-1])
        finally:
            await conn.close()

    async def get_usage_by_user(self, days: int = 30) -> List[Dict[str, Any]]:
        """Per-user cost breakdown, joined with nexus_users for display (nome/email)."""
        conn = await asyncpg.connect(self.dsn)
        try:
            records = await conn.fetch(f"""
                SELECT
                    l.user_id as user_id,
                    u.nome as nome,
                    u.email as email,
                    COALESCE(SUM(l.input_tokens), 0) as total_input,
                    COALESCE(SUM(l.output_tokens), 0) as total_output,
                    COUNT(l.id) as requests,
                    COALESCE(SUM(l.total_cost), 0) as cost
                FROM llm_usage_logs l
                LEFT JOIN nexus_users u ON u.id = l.user_id
                WHERE l.created_at >= NOW() - INTERVAL '{days} days'
                GROUP BY l.user_id, u.nome, u.email
                ORDER BY cost DESC;
            """)
            return [dict(r) for r in records]
        finally:
            await conn.close()
