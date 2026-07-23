"""Orchestrate multi-host performance debugging jobs."""

from __future__ import annotations

import asyncio

from loguru import logger

from app.core.errors import sanitize_error_message
from app.ai.usage import UsageTracker
from app.modules.performance.ai.analyzer import PerformanceAnalyzer
from app.modules.performance.collector import PerformanceCollector
from app.modules.performance.store import PerformanceDebugStore, get_performance_debug_store
from app.services.llm_usage_service import persist_usage_session
from app.storage.factory import get_llm_usage_store


class PerformanceDebugService:
    """Collect metrics over SSH and analyze with the shared LLM."""

    MAX_PARALLEL_HOSTS = 5

    def __init__(
        self,
        store: PerformanceDebugStore | None = None,
        collector: PerformanceCollector | None = None,
        analyzer: PerformanceAnalyzer | None = None,
    ) -> None:
        self.store = store or get_performance_debug_store()
        self.collector = collector or PerformanceCollector()
        self.analyzer = analyzer or PerformanceAnalyzer()

    async def enqueue(self, hosts: list[str], user_id: str | None = None) -> str:
        return await self.store.create(hosts, user_id=user_id)

    async def process(self, debug_id: str) -> None:
        record = await self.store.get(debug_id)
        if record is None:
            logger.warning("Performance debug job missing | id={}", debug_id)
            return

        hosts = [item["host"] for item in record.get("hosts") or []]
        total = max(len(hosts), 1)
        user_id = record.get("user_id")
        usage_store = get_llm_usage_store()
        await usage_store.initialize()

        try:
            with UsageTracker.session(
                scope_type="performance",
                scope_id=debug_id,
                user_id=user_id,
                agent_type="performance",
                default_call_kind="performance_host",
            ) as usage_session:
                await self.store.update_job(
                    debug_id,
                    status="running",
                    current_step="collecting_metrics",
                    progress_percentage=5,
                )

                semaphore = asyncio.Semaphore(self.MAX_PARALLEL_HOSTS)
                completed_hosts = 0
                lock = asyncio.Lock()

                async def _handle_host(host: str) -> None:
                    nonlocal completed_hosts
                    async with semaphore:
                        await self.store.update_host(
                            debug_id,
                            host,
                            status="collecting",
                            message="Collecting metrics over SSH",
                            error=None,
                        )
                        collection = await self.collector.collect(host)
                        if not collection.success:
                            await self.store.update_host(
                                debug_id,
                                host,
                                status="failed",
                                message="Collection failed",
                                evidence=collection.evidence or None,
                                error=collection.error or "Unknown collection error",
                            )
                        else:
                            await self.store.update_host(
                                debug_id,
                                host,
                                status="analyzing",
                                message="Running AI analysis",
                                evidence=collection.evidence,
                                error=None,
                            )
                            try:
                                with UsageTracker.call_kind("performance_host"):
                                    analysis = await self.analyzer.analyze_host(
                                        host, collection.evidence
                                    )
                                await self.store.update_host(
                                    debug_id,
                                    host,
                                    status="completed",
                                    message="Analysis complete",
                                    analysis=analysis.get("analysis_markdown"),
                                    summary=analysis.get("summary"),
                                    severity=analysis.get("severity"),
                                    error=None,
                                )
                            except Exception as exc:  # noqa: BLE001
                                await self.store.update_host(
                                    debug_id,
                                    host,
                                    status="failed",
                                    message="AI analysis failed",
                                    evidence=collection.evidence,
                                    error=sanitize_error_message(str(exc)),
                                )

                        async with lock:
                            completed_hosts += 1
                            # Collection+analysis spans most of the bar; reserve room for fleet summary.
                            pct = 5 + int((completed_hosts / total) * 85)
                            await self.store.update_job(
                                debug_id,
                                current_step=f"processed_{completed_hosts}_of_{total}",
                                progress_percentage=min(pct, 90),
                            )

                await asyncio.gather(*[_handle_host(host) for host in hosts])

                await self.store.update_job(
                    debug_id,
                    current_step="summarizing",
                    progress_percentage=92,
                )

                latest = await self.store.get(debug_id)
                host_rows = (latest or {}).get("hosts") or []
                summaries = [
                    {
                        "host": row["host"],
                        "severity": row.get("severity") or "",
                        "summary": row.get("summary") or "",
                        "error": row.get("error") or "",
                    }
                    for row in host_rows
                ]
                with UsageTracker.call_kind("performance_summary"):
                    overall = await self.analyzer.summarize_fleet(summaries)

                any_success = any(row.get("status") == "completed" for row in host_rows)
                final_status = "completed" if any_success else "failed"
                await persist_usage_session(usage_store, usage_session)
                await self.store.update_job(
                    debug_id,
                    status=final_status,
                    current_step="completed" if final_status == "completed" else "failed",
                    progress_percentage=100,
                    overall_summary=overall,
                    error=None
                    if any_success
                    else "All hosts failed collection or analysis. Check passwordless SSH connectivity.",
                )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Performance debug job failed | id={}", debug_id)
            await self.store.update_job(
                debug_id,
                status="failed",
                current_step="failed",
                progress_percentage=100,
                error=sanitize_error_message(str(exc)),
            )
