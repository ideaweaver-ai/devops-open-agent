"""SQLite persistence for LLM usage events and aggregates."""

from __future__ import annotations

import asyncio
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from app.ai.usage import UsageCall, UsageSession


class LlmUsageStore:
    """Store per-call LLM usage events for the Cost / Usage dashboard."""

    def __init__(self, database_path: str) -> None:
        self.database_path = database_path

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize_sync)

    def _connect(self) -> sqlite3.Connection:
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_sync(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS llm_usage_events (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    user_id TEXT,
                    scope_type TEXT NOT NULL,
                    scope_id TEXT NOT NULL,
                    agent_type TEXT,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    call_kind TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    total_tokens INTEGER NOT NULL DEFAULT 0,
                    estimated_usd REAL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_llm_usage_created_at ON llm_usage_events(created_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_llm_usage_user_created "
                "ON llm_usage_events(user_id, created_at)"
            )
            connection.commit()
        logger.info("LLM usage store initialized | path={}", self.database_path)

    async def record_session(self, session: UsageSession) -> None:
        await asyncio.to_thread(self._record_session_sync, session)

    def _record_session_sync(self, session: UsageSession) -> None:
        if not session.calls:
            return
        now = datetime.utcnow().isoformat() + "Z"
        rows = [
            (
                str(uuid.uuid4()),
                now,
                session.user_id,
                session.scope_type,
                session.scope_id,
                session.agent_type,
                call.provider,
                call.model,
                call.call_kind,
                call.input_tokens,
                call.output_tokens,
                call.total_tokens,
                call.estimated_usd,
            )
            for call in session.calls
        ]
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO llm_usage_events (
                    id, created_at, user_id, scope_type, scope_id, agent_type,
                    provider, model, call_kind, input_tokens, output_tokens,
                    total_tokens, estimated_usd
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            connection.commit()

    async def record_call(
        self,
        *,
        user_id: str | None,
        scope_type: str,
        scope_id: str,
        agent_type: str | None,
        call: UsageCall,
    ) -> None:
        session = UsageSession(
            scope_type=scope_type,
            scope_id=scope_id,
            user_id=user_id,
            agent_type=agent_type,
            calls=[call],
        )
        await self.record_session(session)

    async def summarize(
        self,
        *,
        user_id: str | None,
        date_from: str,
        date_to: str,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(self._summarize_sync, user_id, date_from, date_to)

    def _summarize_sync(
        self,
        user_id: str | None,
        date_from: str,
        date_to: str,
    ) -> dict[str, Any]:
        clauses = ["created_at >= ?", "created_at <= ?"]
        params: list[Any] = [date_from, date_to]
        if user_id:
            clauses.append("user_id = ?")
            params.append(user_id)
        where = " AND ".join(clauses)

        with self._connect() as connection:
            totals = connection.execute(
                f"""
                SELECT
                    COUNT(*) AS call_count,
                    COALESCE(SUM(input_tokens), 0) AS input_tokens,
                    COALESCE(SUM(output_tokens), 0) AS output_tokens,
                    COALESCE(SUM(total_tokens), 0) AS total_tokens,
                    COALESCE(SUM(estimated_usd), 0) AS estimated_usd
                FROM llm_usage_events
                WHERE {where}
                """,
                params,
            ).fetchone()

            by_day = connection.execute(
                f"""
                SELECT substr(created_at, 1, 10) AS day,
                       COUNT(*) AS call_count,
                       COALESCE(SUM(total_tokens), 0) AS total_tokens,
                       COALESCE(SUM(estimated_usd), 0) AS estimated_usd
                FROM llm_usage_events
                WHERE {where}
                GROUP BY day
                ORDER BY day ASC
                """,
                params,
            ).fetchall()

            by_agent = connection.execute(
                f"""
                SELECT COALESCE(agent_type, scope_type, 'unknown') AS agent_type,
                       COUNT(*) AS call_count,
                       COALESCE(SUM(total_tokens), 0) AS total_tokens,
                       COALESCE(SUM(estimated_usd), 0) AS estimated_usd
                FROM llm_usage_events
                WHERE {where}
                GROUP BY agent_type
                ORDER BY estimated_usd DESC, total_tokens DESC
                """,
                params,
            ).fetchall()

            by_provider = connection.execute(
                f"""
                SELECT provider,
                       COUNT(*) AS call_count,
                       COALESCE(SUM(total_tokens), 0) AS total_tokens,
                       COALESCE(SUM(estimated_usd), 0) AS estimated_usd
                FROM llm_usage_events
                WHERE {where}
                GROUP BY provider
                ORDER BY estimated_usd DESC, total_tokens DESC
                """,
                params,
            ).fetchall()

            by_call_kind = connection.execute(
                f"""
                SELECT call_kind,
                       COUNT(*) AS call_count,
                       COALESCE(SUM(total_tokens), 0) AS total_tokens,
                       COALESCE(SUM(estimated_usd), 0) AS estimated_usd
                FROM llm_usage_events
                WHERE {where}
                GROUP BY call_kind
                ORDER BY estimated_usd DESC, total_tokens DESC
                """,
                params,
            ).fetchall()

        def _row(row: sqlite3.Row) -> dict[str, Any]:
            return dict(row)

        return {
            "from": date_from,
            "to": date_to,
            "totals": {
                "call_count": int(totals["call_count"] or 0),
                "input_tokens": int(totals["input_tokens"] or 0),
                "output_tokens": int(totals["output_tokens"] or 0),
                "total_tokens": int(totals["total_tokens"] or 0),
                "estimated_usd": float(totals["estimated_usd"] or 0.0),
            },
            "by_day": [_row(r) for r in by_day],
            "by_agent": [_row(r) for r in by_agent],
            "by_provider": [_row(r) for r in by_provider],
            "by_call_kind": [_row(r) for r in by_call_kind],
        }

    async def list_events(
        self,
        *,
        user_id: str | None,
        date_from: str,
        date_to: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(
            self._list_events_sync,
            user_id,
            date_from,
            date_to,
            limit,
        )

    def _list_events_sync(
        self,
        user_id: str | None,
        date_from: str,
        date_to: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        clauses = ["created_at >= ?", "created_at <= ?"]
        params: list[Any] = [date_from, date_to]
        if user_id:
            clauses.append("user_id = ?")
            params.append(user_id)
        params.append(max(1, min(limit, 500)))
        where = " AND ".join(clauses)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT id, created_at, user_id, scope_type, scope_id, agent_type,
                       provider, model, call_kind, input_tokens, output_tokens,
                       total_tokens, estimated_usd
                FROM llm_usage_events
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
            return [dict(row) for row in rows]
