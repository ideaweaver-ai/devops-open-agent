"""In-memory store for Performance Debugging jobs (v1 — no history UI)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any


class PerformanceDebugStore:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._jobs: dict[str, dict[str, Any]] = {}

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    async def create(self, hosts: list[str], user_id: str | None = None) -> str:
        debug_id = str(uuid.uuid4())
        now = self.utc_now()
        record: dict[str, Any] = {
            "debug_id": debug_id,
            "agent_type": "performance",
            "status": "queued",
            "current_step": "queued",
            "progress_percentage": 0,
            "user_id": user_id,
            "hosts": [
                {
                    "host": host,
                    "status": "pending",
                    "message": None,
                    "evidence": None,
                    "analysis": None,
                    "summary": None,
                    "severity": None,
                    "error": None,
                }
                for host in hosts
            ],
            "overall_summary": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        async with self._lock:
            self._jobs[debug_id] = record
        return debug_id

    async def get(self, debug_id: str) -> dict[str, Any] | None:
        async with self._lock:
            record = self._jobs.get(debug_id)
            return None if record is None else dict(record)

    async def update_job(
        self,
        debug_id: str,
        *,
        status: str | None = None,
        current_step: str | None = None,
        progress_percentage: int | None = None,
        overall_summary: str | None = None,
        error: str | None = None,
    ) -> None:
        async with self._lock:
            record = self._jobs.get(debug_id)
            if record is None:
                return
            if status is not None:
                record["status"] = status
            if current_step is not None:
                record["current_step"] = current_step
            if progress_percentage is not None:
                record["progress_percentage"] = progress_percentage
            if overall_summary is not None:
                record["overall_summary"] = overall_summary
            if error is not None:
                record["error"] = error
            record["updated_at"] = self.utc_now()

    async def update_host(self, debug_id: str, host: str, **fields: Any) -> None:
        async with self._lock:
            record = self._jobs.get(debug_id)
            if record is None:
                return
            for item in record["hosts"]:
                if item["host"] == host:
                    item.update(fields)
                    break
            record["updated_at"] = self.utc_now()


_store: PerformanceDebugStore | None = None


def get_performance_debug_store() -> PerformanceDebugStore:
    global _store
    if _store is None:
        _store = PerformanceDebugStore()
    return _store
