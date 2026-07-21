"""Prometheus HTTP client for investigation evidence."""

from __future__ import annotations

import time
from typing import Any, Literal
from urllib.parse import urljoin

import httpx
from loguru import logger

from app.models.investigation import ObservabilityFinding
from app.services.prometheus_settings_service import PrometheusConnection

MAX_FINDINGS = 16
QUERY_TIMEOUT = 20.0

AgentType = Literal["kubernetes", "aws", "all"]


class PrometheusError(Exception):
    """Raised when Prometheus requests fail."""


class PrometheusClient:
    """Query Prometheus for Kubernetes and host/EC2-oriented signals."""

    def __init__(self, connection: PrometheusConnection) -> None:
        self.connection = connection

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.connection.bearer_token:
            headers["Authorization"] = f"Bearer {self.connection.bearer_token}"
        return headers

    def _auth(self) -> httpx.BasicAuth | None:
        user = self.connection.basic_auth_user
        password = self.connection.basic_auth_password
        if user and password:
            return httpx.BasicAuth(user, password)
        return None

    async def test_connection(self) -> dict[str, Any]:
        url = urljoin(self.connection.url + "/", "api/v1/status/buildinfo")
        async with httpx.AsyncClient(timeout=QUERY_TIMEOUT, verify=False) as client:
            response = await client.get(url, headers=self._headers(), auth=self._auth())
            if response.status_code >= 400:
                # Fallback for older Prometheus without buildinfo
                query_url = urljoin(self.connection.url + "/", "api/v1/query")
                response = await client.get(
                    query_url,
                    params={"query": "up"},
                    headers=self._headers(),
                    auth=self._auth(),
                )
            if response.status_code >= 400:
                raise PrometheusError(
                    f"Prometheus returned HTTP {response.status_code}: {response.text[:200]}"
                )
            data = response.json()
            version = None
            if isinstance(data, dict):
                version = (data.get("data") or {}).get("version")
            return {"version": version}

    async def collect_findings(
        self,
        *,
        cluster_id: str,
        namespace: str | None = None,
        pod_names: list[str] | None = None,
        agent_type: AgentType = "kubernetes",
    ) -> list[ObservabilityFinding]:
        queries = self._build_queries(
            cluster_id=cluster_id,
            namespace=namespace,
            pod_names=pod_names,
            agent_type=agent_type,
        )

        findings: list[ObservabilityFinding] = []
        for title, promql, severity in queries:
            if len(findings) >= MAX_FINDINGS:
                break
            try:
                results = await self.query(promql)
                detail = self._summarize_vector(results, title)
                if detail:
                    findings.append(
                        ObservabilityFinding(
                            source="prometheus",
                            title=title,
                            severity=severity,
                            detail=detail,
                            query=promql,
                            timestamp=None,
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "Prometheus query skipped | title={} cluster={} agent_type={} error={}",
                    title,
                    cluster_id,
                    agent_type,
                    exc,
                )
        return findings

    def _build_queries(
        self,
        *,
        cluster_id: str,
        namespace: str | None,
        pod_names: list[str] | None,
        agent_type: AgentType,
    ) -> list[tuple[str, str, str]]:
        _ = cluster_id  # reserved for future label scoping
        queries: list[tuple[str, str, str]] = []

        # Host / Alloy / node-exporter signals (EC2 stress, bare metal, agents)
        if agent_type in {"aws", "all", "kubernetes"}:
            queries.extend(
                [
                    (
                        "Host CPU busy % (top)",
                        (
                            "topk(5, 100 - (avg by (instance) "
                            '(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100))'
                        ),
                        "low",
                    ),
                    (
                        "Hosts with high CPU (>70%)",
                        (
                            "(100 - (avg by (instance) "
                            '(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)) > 70'
                        ),
                        "high",
                    ),
                    (
                        "Host load average (1m)",
                        "topk(5, node_load1)",
                        "low",
                    ),
                    (
                        "Hosts with elevated load (>1)",
                        "node_load1 > 1",
                        "medium",
                    ),
                    (
                        "Host memory available (bytes)",
                        "topk(5, node_memory_MemAvailable_bytes)",
                        "low",
                    ),
                    (
                        "Hosts with low memory (<15% available)",
                        (
                            "(node_memory_MemAvailable_bytes / "
                            "node_memory_MemTotal_bytes) < 0.15"
                        ),
                        "high",
                    ),
                    (
                        "Scrape targets down",
                        "up == 0",
                        "high",
                    ),
                ]
            )

        if agent_type in {"kubernetes", "all"}:
            ns = (namespace or "").strip()
            ns_filter = f',namespace="{ns}"' if ns else ""
            queries.extend(
                [
                    (
                        "Pod restarts (1h)",
                        f'increase(kube_pod_container_status_restarts_total{{job=~".*"{ns_filter}}}[1h]) > 0',
                        "medium",
                    ),
                    (
                        "OOM kills (1h)",
                        f'increase(kube_pod_container_status_last_terminated_reason{{reason="OOMKilled"{ns_filter}}}[1h]) > 0',
                        "high",
                    ),
                    (
                        "Container CPU usage",
                        f'topk(5, rate(container_cpu_usage_seconds_total{{container!="",container!="POD"{ns_filter}}}[5m]))',
                        "low",
                    ),
                    (
                        "Container memory working set",
                        f'topk(5, container_memory_working_set_bytes{{container!="",container!="POD"{ns_filter}}})',
                        "low",
                    ),
                ]
            )
            if pod_names:
                for pod in pod_names[:5]:
                    safe_pod = pod.replace('"', "")
                    pod_ns = f',namespace="{ns}"' if ns else ""
                    queries.append(
                        (
                            f"Restarts for pod {safe_pod}",
                            f'increase(kube_pod_container_status_restarts_total{{pod="{safe_pod}"{pod_ns}}}[1h])',
                            "medium",
                        )
                    )

        return queries

    async def query(self, promql: str) -> dict[str, Any]:
        url = urljoin(self.connection.url + "/", "api/v1/query")
        async with httpx.AsyncClient(timeout=QUERY_TIMEOUT, verify=False) as client:
            response = await client.get(
                url,
                params={"query": promql, "time": str(time.time())},
                headers=self._headers(),
                auth=self._auth(),
            )
            if response.status_code >= 400:
                raise PrometheusError(
                    f"Prometheus query failed ({response.status_code}): {response.text[:200]}"
                )
            payload = response.json()
            if payload.get("status") != "success":
                raise PrometheusError(f"Prometheus query error: {payload.get('error')}")
            return payload.get("data") or {}

    async def query_range(
        self,
        promql: str,
        start: str,
        end: str,
        step: str,
    ) -> dict[str, Any]:
        url = urljoin(self.connection.url + "/", "api/v1/query_range")
        async with httpx.AsyncClient(timeout=QUERY_TIMEOUT, verify=False) as client:
            response = await client.get(
                url,
                params={"query": promql, "start": start, "end": end, "step": step},
                headers=self._headers(),
                auth=self._auth(),
            )
            if response.status_code >= 400:
                raise PrometheusError(
                    f"Prometheus query_range failed ({response.status_code}): {response.text[:200]}"
                )
            payload = response.json()
            if payload.get("status") != "success":
                raise PrometheusError(f"Prometheus query_range error: {payload.get('error')}")
            return payload.get("data") or {}

    @staticmethod
    def _summarize_vector(data: dict[str, Any], title: str) -> str | None:
        result_type = data.get("resultType")
        results = data.get("result") or []
        if not results:
            return None
        lines: list[str] = []
        for item in results[:5]:
            metric = item.get("metric") or {}
            labels = ", ".join(
                f"{k}={v}"
                for k, v in metric.items()
                if k not in {"__name__", "job"} and v
            )
            value = None
            if result_type == "vector" and item.get("value"):
                value = item["value"][1] if len(item["value"]) > 1 else item["value"][0]
            elif result_type == "matrix" and item.get("values"):
                value = item["values"][-1][1]
            label_part = f" ({labels})" if labels else ""
            lines.append(f"{title}{label_part}: {value}")
        return "; ".join(lines) if lines else None
