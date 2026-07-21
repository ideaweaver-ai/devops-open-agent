"""Observability collector — Prometheus and Grafana evidence for investigations."""

from __future__ import annotations

import asyncio
from typing import Any, Literal
from uuid import UUID

from loguru import logger

from app.db.session import SessionLocal
from app.models.investigation import (
    IntegrationStatus,
    ObservabilityFinding,
    ObservabilityResult,
)
from app.observability.grafana import GrafanaClient, GrafanaError
from app.observability.prometheus import PrometheusClient, PrometheusError
from app.services.grafana_settings_service import GrafanaSettingsService
from app.services.prometheus_settings_service import PrometheusSettingsService

AgentType = Literal["kubernetes", "aws", "all"]


class ObservabilityCollector:
    """Collect metrics/logs annotations from configured observability backends."""

    def __init__(
        self,
        prometheus_settings: PrometheusSettingsService | None = None,
        grafana_settings: GrafanaSettingsService | None = None,
    ) -> None:
        self.prometheus_settings = prometheus_settings or PrometheusSettingsService()
        self.grafana_settings = grafana_settings or GrafanaSettingsService()

    async def collect(
        self,
        cluster_id: str,
        *,
        user_id: str | None = None,
        namespace: str | None = None,
        pod_names: list[str] | None = None,
        agent_type: AgentType = "kubernetes",
        search_hints: list[str] | None = None,
    ) -> ObservabilityResult:
        uid = self._parse_user_id(user_id)
        context = {
            "cluster_id": cluster_id,
            "namespace": namespace,
            "pod_names": pod_names or [],
            "agent_type": agent_type,
            "search_hints": search_hints or [],
        }

        (prom_status, prom_findings), (graf_status, graf_findings) = await asyncio.gather(
            self._collect_prometheus(uid, context),
            self._collect_grafana(uid, context),
        )

        findings = [*prom_findings, *graf_findings]
        any_enabled = prom_status.enabled or graf_status.enabled
        summary = None
        if findings:
            by_source: dict[str, int] = {}
            for item in findings:
                by_source[item.source] = by_source.get(item.source, 0) + 1
            parts = [f"{src}={count}" for src, count in sorted(by_source.items())]
            summary = f"Collected {len(findings)} observability finding(s) ({', '.join(parts)})."
        elif any_enabled:
            summary = "Observability integrations are enabled but returned no matching findings."

        return ObservabilityResult(
            enabled=any_enabled or bool(findings),
            prometheus=prom_status,
            grafana=graf_status,
            loki=IntegrationStatus(enabled=False),
            opentelemetry=IntegrationStatus(enabled=False),
            findings=findings,
            summary=summary,
        )

    async def _collect_prometheus(
        self,
        user_id: UUID | None,
        context: dict[str, Any],
    ) -> tuple[IntegrationStatus, list[ObservabilityFinding]]:
        try:
            async with SessionLocal() as session:
                # Enabled integrations apply to all agent types (K8s + AWS).
                connection = await self.prometheus_settings.resolve_connection(
                    session,
                    user_id,
                    require_enabled=True,
                    require_kubernetes=False,
                )
            if connection is None:
                return IntegrationStatus(enabled=False), []
            client = PrometheusClient(connection)
            findings = await client.collect_findings(
                cluster_id=context["cluster_id"],
                namespace=context.get("namespace"),
                pod_names=context.get("pod_names") or [],
                agent_type=context.get("agent_type") or "kubernetes",
            )
            return IntegrationStatus(enabled=True), findings
        except PrometheusError as exc:
            logger.warning("Prometheus collection failed | error={}", exc)
            return IntegrationStatus(enabled=True, error=str(exc)[:300]), []
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected Prometheus collection error")
            return IntegrationStatus(enabled=True, error=str(exc)[:300]), []

    async def _collect_grafana(
        self,
        user_id: UUID | None,
        context: dict[str, Any],
    ) -> tuple[IntegrationStatus, list[ObservabilityFinding]]:
        try:
            async with SessionLocal() as session:
                connection = await self.grafana_settings.resolve_connection(
                    session,
                    user_id,
                    require_enabled=True,
                    require_kubernetes=False,
                )
            if connection is None:
                return IntegrationStatus(enabled=False), []
            client = GrafanaClient(connection)
            findings = await client.collect_findings(
                cluster_id=context["cluster_id"],
                namespace=context.get("namespace"),
                agent_type=context.get("agent_type") or "kubernetes",
                search_hints=context.get("search_hints") or [],
            )
            return IntegrationStatus(enabled=True), findings
        except GrafanaError as exc:
            logger.warning("Grafana collection failed | error={}", exc)
            return IntegrationStatus(enabled=True, error=str(exc)[:300]), []
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected Grafana collection error")
            return IntegrationStatus(enabled=True, error=str(exc)[:300]), []


    @staticmethod
    def _parse_user_id(user_id: str | None) -> UUID | None:
        if not user_id:
            return None
        try:
            return UUID(str(user_id))
        except (TypeError, ValueError):
            return None
