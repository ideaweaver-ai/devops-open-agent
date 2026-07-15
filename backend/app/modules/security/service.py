"""Orchestrate Trivy security scans with optional AI analysis."""

from __future__ import annotations

from loguru import logger

from app.modules.security.ai.analyzer import SecurityAnalyzer
from app.modules.security.models import ScanType, SecurityScanRequest
from app.modules.security.scanner import TrivyScanner
from app.modules.security.store import SecurityScanStore, get_security_scan_store


def _safe_error(exc: Exception) -> str:
    """Return a trimmed but honest error string for Trivy failures."""
    msg = str(exc).strip()
    if len(msg) > 600:
        msg = msg[:600] + "…"
    return msg


class SecurityScanService:
    def __init__(
        self,
        store: SecurityScanStore | None = None,
        scanner: TrivyScanner | None = None,
        analyzer: SecurityAnalyzer | None = None,
    ) -> None:
        self.store = store or get_security_scan_store()
        self.scanner = scanner or TrivyScanner()
        self.analyzer = analyzer or SecurityAnalyzer()

    async def enqueue(
        self,
        request: SecurityScanRequest,
        user_id: str | None = None,
    ) -> str:
        target = (
            request.image_name
            if request.scan_type == ScanType.IMAGE
            else f"cluster (namespace={request.namespace or 'all'})"
        )
        return await self.store.create(
            scan_type=request.scan_type.value,
            target=target or "unknown",
            user_id=user_id,
        )

    async def process(self, scan_id: str, request: SecurityScanRequest) -> None:
        record = await self.store.get(scan_id)
        if record is None:
            logger.warning("Security scan job missing | id={}", scan_id)
            return

        try:
            await self.store.update(
                scan_id,
                status="running",
                current_step="scanning",
                progress_percentage=10,
            )

            if request.scan_type == ScanType.IMAGE:
                if not request.image_name:
                    raise ValueError("image_name is required for image scans")
                scan_results = await self.scanner.scan_image(
                    request.image_name,
                    severity_filter=request.severity_filter,
                )
            else:
                scan_results = await self.scanner.scan_kubernetes(
                    namespace=request.namespace,
                    context=request.context,
                    severity_filter=request.severity_filter,
                )

            await self.store.update(
                scan_id,
                current_step="scan_complete",
                progress_percentage=60,
            )

            ai_analysis = None
            llm_provider = None
            llm_error = None

            if request.include_ai:
                await self.store.update(
                    scan_id,
                    current_step="ai_analysis",
                    progress_percentage=65,
                )
                try:
                    analysis = await self.analyzer.analyze_scan(
                        scan_results,
                        request.scan_type.value,
                    )
                    ai_analysis = analysis.get("ai_analysis")
                    llm_provider = analysis.get("llm_provider")
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Security AI analysis failed | scan_id={}", scan_id)
                    llm_error = _safe_error(exc)

            result = {
                **scan_results,
                "ai_analysis": ai_analysis,
                "llm_provider": llm_provider,
                "llm_error": llm_error,
            }

            await self.store.update(
                scan_id,
                status="completed",
                current_step="completed",
                progress_percentage=100,
                result=result,
            )

        except Exception as exc:  # noqa: BLE001
            logger.exception("Security scan failed | scan_id={}", scan_id)
            await self.store.update(
                scan_id,
                status="failed",
                current_step="failed",
                progress_percentage=100,
                error=_safe_error(exc),
            )
