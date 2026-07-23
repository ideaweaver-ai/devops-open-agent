"""SQLite persistence for structured audit events."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger


class AuditStore:
    """Store who did what (investigations, integrations, settings)."""

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
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    actor_user_id TEXT,
                    actor_email TEXT,
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT,
                    metadata_json TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_events(created_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_actor_created "
                "ON audit_events(actor_user_id, created_at)"
            )
            connection.commit()
        logger.info("Audit store initialized | path={}", self.database_path)

    async def record(
        self,
        *,
        actor_user_id: str | None,
        actor_email: str | None,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        event_id = str(uuid.uuid4())
        await asyncio.to_thread(
            self._record_sync,
            event_id,
            actor_user_id,
            actor_email,
            action,
            resource_type,
            resource_id,
            metadata,
        )
        return event_id

    def _record_sync(
        self,
        event_id: str,
        actor_user_id: str | None,
        actor_email: str | None,
        action: str,
        resource_type: str,
        resource_id: str | None,
        metadata: dict[str, Any] | None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_events (
                    id, created_at, actor_user_id, actor_email,
                    action, resource_type, resource_id, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    datetime.utcnow().isoformat() + "Z",
                    actor_user_id,
                    actor_email,
                    action,
                    resource_type,
                    resource_id,
                    json.dumps(metadata) if metadata else None,
                ),
            )
            connection.commit()

    async def list_events(
        self,
        *,
        actor_user_id: str | None = None,
        action: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(
            self._list_events_sync,
            actor_user_id,
            action,
            limit,
        )

    def _list_events_sync(
        self,
        actor_user_id: str | None,
        action: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if actor_user_id:
            clauses.append("actor_user_id = ?")
            params.append(actor_user_id)
        if action:
            clauses.append("action = ?")
            params.append(action)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"""
            SELECT * FROM audit_events
            {where}
            ORDER BY created_at DESC
            LIMIT ?
        """
        params.append(max(1, min(limit, 500)))
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            data = dict(row)
            raw_meta = data.pop("metadata_json", None)
            if raw_meta:
                try:
                    data["metadata"] = json.loads(raw_meta)
                except (TypeError, ValueError, json.JSONDecodeError):
                    data["metadata"] = None
            else:
                data["metadata"] = None
            results.append(data)
        return results
