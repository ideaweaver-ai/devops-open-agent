"""Abstract investigation storage interface."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class BaseInvestigationStore(ABC):
    """Storage abstraction for investigation jobs and history."""

    @abstractmethod
    async def initialize(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def create(
        self,
        investigation_id: str,
        cluster_id: str,
        include_ai: bool,
        agent_type: str = "kubernetes",
        user_id: str | None = None,
        request_payload: dict[str, Any] | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def update_progress(
        self,
        investigation_id: str,
        *,
        status: str,
        current_step: str | None = None,
        progress_percentage: int = 0,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def complete(
        self,
        investigation_id: str,
        *,
        status: str,
        result: dict[str, Any],
        root_cause: str | None = None,
        confidence: int | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def fail(
        self,
        investigation_id: str,
        *,
        error: str,
        result: dict[str, Any] | None = None,
    ) -> None:
        raise NotImplementedError

    async def fail_orphaned_running(
        self,
        *,
        error: str = (
            "Investigation interrupted by server restart. "
            "Please re-run the investigation."
        ),
    ) -> int:
        """Mark in-progress jobs as failed after a process restart. Default: no-op."""
        return 0

    @abstractmethod
    async def get_status(self, investigation_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    async def get_result(self, investigation_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    async def list_history(
        self,
        limit: int = 50,
        agent_type: str | None = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @staticmethod
    def utc_now() -> str:
        return datetime.utcnow().isoformat() + "Z"
