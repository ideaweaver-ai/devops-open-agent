"""SQLite investigation storage implementation."""

import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Any

from loguru import logger

from app.storage.base import BaseInvestigationStore


class SQLiteInvestigationStore(BaseInvestigationStore):
    """SQLite-backed investigation store with PostgreSQL migration path."""

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
                CREATE TABLE IF NOT EXISTS investigations (
                    id TEXT PRIMARY KEY,
                    cluster_id TEXT NOT NULL,
                    include_ai INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL,
                    current_step TEXT,
                    progress_percentage INTEGER NOT NULL DEFAULT 0,
                    root_cause TEXT,
                    confidence INTEGER,
                    result_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.commit()
            self._ensure_schema(connection)
        logger.info("SQLite investigation store initialized | path={}", self.database_path)

    def _ensure_schema(self, connection: sqlite3.Connection) -> None:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(investigations)").fetchall()
        }
        if "agent_type" not in columns:
            connection.execute(
                "ALTER TABLE investigations ADD COLUMN agent_type TEXT NOT NULL DEFAULT 'kubernetes'"
            )
            connection.commit()
        if "user_id" not in columns:
            connection.execute("ALTER TABLE investigations ADD COLUMN user_id TEXT")
            connection.commit()
        for column, ddl in (
            ("llm_input_tokens", "INTEGER NOT NULL DEFAULT 0"),
            ("llm_output_tokens", "INTEGER NOT NULL DEFAULT 0"),
            ("llm_estimated_cost_usd", "REAL"),
            ("llm_call_count", "INTEGER NOT NULL DEFAULT 0"),
            ("request_json", "TEXT"),
        ):
            if column not in columns:
                connection.execute(
                    f"ALTER TABLE investigations ADD COLUMN {column} {ddl}"
                )
                connection.commit()

    async def create(
        self,
        investigation_id: str,
        cluster_id: str,
        include_ai: bool,
        agent_type: str = "kubernetes",
        user_id: str | None = None,
        request_payload: dict[str, Any] | None = None,
    ) -> None:
        await asyncio.to_thread(
            self._create_sync,
            investigation_id,
            cluster_id,
            include_ai,
            agent_type,
            user_id,
            request_payload,
        )

    def _create_sync(
        self,
        investigation_id: str,
        cluster_id: str,
        include_ai: bool,
        agent_type: str = "kubernetes",
        user_id: str | None = None,
        request_payload: dict[str, Any] | None = None,
    ) -> None:
        now = self.utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO investigations (
                    id, cluster_id, agent_type, include_ai, status, current_step,
                    progress_percentage, user_id, request_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    investigation_id,
                    cluster_id,
                    agent_type,
                    int(include_ai),
                    "running",
                    "Cluster Discovery",
                    0,
                    user_id,
                    json.dumps(request_payload) if request_payload is not None else None,
                    now,
                    now,
                ),
            )
            connection.commit()

    async def update_progress(
        self,
        investigation_id: str,
        *,
        status: str,
        current_step: str | None = None,
        progress_percentage: int = 0,
    ) -> None:
        await asyncio.to_thread(
            self._update_progress_sync,
            investigation_id,
            status,
            current_step,
            progress_percentage,
        )

    def _update_progress_sync(
        self,
        investigation_id: str,
        status: str,
        current_step: str | None,
        progress_percentage: int,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE investigations
                SET status = ?, current_step = ?, progress_percentage = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    current_step,
                    progress_percentage,
                    self.utc_now(),
                    investigation_id,
                ),
            )
            connection.commit()

    async def complete(
        self,
        investigation_id: str,
        *,
        status: str,
        result: dict[str, Any],
        root_cause: str | None = None,
        confidence: int | None = None,
    ) -> None:
        await asyncio.to_thread(
            self._complete_sync,
            investigation_id,
            status,
            result,
            root_cause,
            confidence,
        )

    def _complete_sync(
        self,
        investigation_id: str,
        status: str,
        result: dict[str, Any],
        root_cause: str | None,
        confidence: int | None,
    ) -> None:
        usage = result.get("llm_usage") if isinstance(result, dict) else None
        usage = usage if isinstance(usage, dict) else {}
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE investigations
                SET status = ?, current_step = ?, progress_percentage = ?,
                    root_cause = ?, confidence = ?, result_json = ?, error = NULL,
                    llm_input_tokens = ?, llm_output_tokens = ?,
                    llm_estimated_cost_usd = ?, llm_call_count = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    "Completed",
                    100,
                    root_cause,
                    confidence,
                    json.dumps(result),
                    int(usage.get("input_tokens") or 0),
                    int(usage.get("output_tokens") or 0),
                    usage.get("estimated_usd"),
                    int(usage.get("call_count") or 0),
                    self.utc_now(),
                    investigation_id,
                ),
            )
            connection.commit()

    async def fail(
        self,
        investigation_id: str,
        *,
        error: str,
        result: dict[str, Any] | None = None,
    ) -> None:
        await asyncio.to_thread(self._fail_sync, investigation_id, error, result)

    def _fail_sync(
        self,
        investigation_id: str,
        error: str,
        result: dict[str, Any] | None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE investigations
                SET status = ?, error = ?, result_json = ?, progress_percentage = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    "failed",
                    error,
                    json.dumps(result) if result else None,
                    100,
                    self.utc_now(),
                    investigation_id,
                ),
            )
            connection.commit()

    async def fail_orphaned_running(
        self,
        *,
        error: str = (
            "Investigation interrupted by server restart. "
            "Please re-run the investigation."
        ),
    ) -> int:
        return await asyncio.to_thread(self._fail_orphaned_running_sync, error)

    def _fail_orphaned_running_sync(self, error: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE investigations
                SET status = ?, error = ?, progress_percentage = ?, updated_at = ?
                WHERE status = ?
                """,
                ("failed", error, 100, self.utc_now(), "running"),
            )
            connection.commit()
            return int(cursor.rowcount or 0)

    async def get_status(self, investigation_id: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._get_status_sync, investigation_id)

    def _get_status_sync(self, investigation_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM investigations WHERE id = ?",
                (investigation_id,),
            ).fetchone()
            return dict(row) if row else None

    async def get_result(self, investigation_id: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._get_result_sync, investigation_id)

    def _get_result_sync(self, investigation_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM investigations WHERE id = ?",
                (investigation_id,),
            ).fetchone()
            if not row:
                return None
            data = dict(row)
            if data.get("result_json"):
                data["result"] = json.loads(data["result_json"])
            return data

    async def list_history(
        self,
        limit: int = 50,
        agent_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_history_sync, limit, agent_type)

    def _list_history_sync(
        self,
        limit: int,
        agent_type: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._connect() as connection:
            if agent_type:
                rows = connection.execute(
                    """
                    SELECT id, cluster_id, agent_type, status, created_at, root_cause, confidence,
                           llm_input_tokens, llm_output_tokens, llm_estimated_cost_usd, llm_call_count
                    FROM investigations
                    WHERE agent_type = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (agent_type, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT id, cluster_id, agent_type, status, created_at, root_cause, confidence,
                           llm_input_tokens, llm_output_tokens, llm_estimated_cost_usd, llm_call_count
                    FROM investigations
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            return [dict(row) for row in rows]
