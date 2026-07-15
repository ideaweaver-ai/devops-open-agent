"""In-memory store for Security Scanning jobs."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any


class SecurityScanStore:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._jobs: dict[str, dict[str, Any]] = {}

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    async def create(
        self,
        scan_type: str,
        target: str,
        user_id: str | None = None,
    ) -> str:
        scan_id = str(uuid.uuid4())
        now = self.utc_now()
        record: dict[str, Any] = {
            "scan_id": scan_id,
            "agent_type": "security",
            "scan_type": scan_type,
            "target": target,
            "status": "queued",
            "current_step": "queued",
            "progress_percentage": 0,
            "user_id": user_id,
            "result": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        async with self._lock:
            self._jobs[scan_id] = record
        return scan_id

    async def get(self, scan_id: str) -> dict[str, Any] | None:
        async with self._lock:
            record = self._jobs.get(scan_id)
            return None if record is None else dict(record)

    async def list_all(self) -> list[dict[str, Any]]:
        async with self._lock:
            items = sorted(
                self._jobs.values(),
                key=lambda r: r.get("created_at", ""),
                reverse=True,
            )
            return [dict(r) for r in items]

    async def update(
        self,
        scan_id: str,
        *,
        status: str | None = None,
        current_step: str | None = None,
        progress_percentage: int | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        async with self._lock:
            record = self._jobs.get(scan_id)
            if record is None:
                return
            if status is not None:
                record["status"] = status
            if current_step is not None:
                record["current_step"] = current_step
            if progress_percentage is not None:
                record["progress_percentage"] = progress_percentage
            if result is not None:
                record["result"] = result
            if error is not None:
                record["error"] = error
            record["updated_at"] = self.utc_now()


_store: SecurityScanStore | None = None


def get_security_scan_store() -> SecurityScanStore:
    global _store
    if _store is None:
        _store = SecurityScanStore()
    return _store
