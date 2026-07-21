"""Grafana HTTP client for investigation evidence."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urljoin

import httpx
from loguru import logger

from app.models.investigation import ObservabilityFinding
from app.services.grafana_settings_service import GrafanaConnection

MAX_FINDINGS = 12
QUERY_TIMEOUT = 20.0


class GrafanaError(Exception):
    """Raised when Grafana requests fail."""


class GrafanaClient:
    """Fetch Grafana dashboards and annotations as investigation evidence."""

    def __init__(self, connection: GrafanaConnection) -> None:
        self.connection = connection

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.connection.api_token:
            headers["Authorization"] = f"Bearer {self.connection.api_token}"
        return headers

    async def test_connection(self) -> dict[str, Any]:
        health_url = urljoin(self.connection.url + "/", "api/health")
        async with httpx.AsyncClient(timeout=QUERY_TIMEOUT, verify=False) as client:
            response = await client.get(health_url, headers=self._headers())
            if response.status_code >= 400:
                raise GrafanaError(
                    f"Grafana health check failed ({response.status_code}): {response.text[:200]}"
                )
            org_name = None
            version = None
            try:
                org_resp = await client.get(
                    urljoin(self.connection.url + "/", "api/org"),
                    headers=self._headers(),
                )
                if org_resp.status_code < 400:
                    org_name = (org_resp.json() or {}).get("name")
            except Exception:  # noqa: BLE001
                pass
            try:
                data = response.json()
                version = data.get("version") if isinstance(data, dict) else None
            except Exception:  # noqa: BLE001
                pass
            return {"version": version, "org_name": org_name}

    async def collect_findings(
        self,
        *,
        cluster_id: str,
        namespace: str | None = None,
        agent_type: str = "kubernetes",
        search_hints: list[str] | None = None,
    ) -> list[ObservabilityFinding]:
        findings: list[ObservabilityFinding] = []
        search_queries = self._search_queries(
            cluster_id=cluster_id,
            namespace=namespace,
            agent_type=agent_type,
            search_hints=search_hints,
        )

        seen_uids: set[str] = set()
        try:
            for query in search_queries:
                dashboards = await self.search_dashboards(query)
                for dash in dashboards[:5]:
                    uid = str(dash.get("uid") or "")
                    if uid and uid in seen_uids:
                        continue
                    if uid:
                        seen_uids.add(uid)
                    title = dash.get("title") or uid or "Dashboard"
                    url = dash.get("url") or ""
                    detail = f"Dashboard matched search ({query!r}): {title}"
                    if uid:
                        detail += f" (uid={uid})"
                    if url:
                        detail += f" path={url}"
                    findings.append(
                        ObservabilityFinding(
                            source="grafana",
                            title=f"Dashboard: {title}",
                            severity="low",
                            detail=detail,
                            query=query,
                            timestamp=None,
                        )
                    )
                    if len(findings) >= 5:
                        break
                if len(findings) >= 5:
                    break
        except Exception as exc:  # noqa: BLE001
            logger.debug("Grafana dashboard search failed | error={}", exc)

        try:
            now = int(time.time() * 1000)
            from_ms = now - 60 * 60 * 1000
            annotations = await self.get_annotations(from_ms=from_ms, to_ms=now)
            for ann in annotations[:8]:
                text = ann.get("text") or ann.get("title") or "Annotation"
                tags = ann.get("tags") or []
                tag_str = ", ".join(str(t) for t in tags[:6])
                ts = ann.get("time")
                timestamp = None
                if isinstance(ts, (int, float)):
                    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts / 1000))
                findings.append(
                    ObservabilityFinding(
                        source="grafana",
                        title="Annotation",
                        severity="medium",
                        detail=f"{text}" + (f" | tags=[{tag_str}]" if tag_str else ""),
                        query=None,
                        timestamp=timestamp,
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Grafana annotations fetch failed | error={}", exc)

        return findings[:MAX_FINDINGS]

    @staticmethod
    def _search_queries(
        *,
        cluster_id: str,
        namespace: str | None,
        agent_type: str,
        search_hints: list[str] | None,
    ) -> list[str]:
        queries: list[str] = []
        if cluster_id.strip():
            queries.append(cluster_id.strip())
        if namespace and namespace.strip():
            queries.append(namespace.strip())
        for hint in search_hints or []:
            if hint and hint.strip():
                queries.append(hint.strip())

        if agent_type == "aws":
            queries.extend(
                [
                    "EC2 Agent CPU Stress",
                    "alloy",
                    "CPU",
                    "aws",
                    "ec2",
                ]
            )
        else:
            queries.extend(["kubernetes", "k8s", "pods"])

        # Deduplicate while preserving order
        seen: set[str] = set()
        ordered: list[str] = []
        for item in queries:
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(item)
        return ordered[:6] or ["kubernetes"]

    async def search_dashboards(self, query: str) -> list[dict]:
        url = urljoin(self.connection.url + "/", "api/search")
        async with httpx.AsyncClient(timeout=QUERY_TIMEOUT, verify=False) as client:
            response = await client.get(
                url,
                params={"type": "dash-db", "query": query, "limit": 10},
                headers=self._headers(),
            )
            if response.status_code >= 400:
                raise GrafanaError(
                    f"Grafana search failed ({response.status_code}): {response.text[:200]}"
                )
            data = response.json()
            return data if isinstance(data, list) else []

    async def get_dashboard(self, dashboard_uid: str) -> dict:
        url = urljoin(self.connection.url + "/", f"api/dashboards/uid/{dashboard_uid}")
        async with httpx.AsyncClient(timeout=QUERY_TIMEOUT, verify=False) as client:
            response = await client.get(url, headers=self._headers())
            if response.status_code >= 400:
                raise GrafanaError(
                    f"Grafana dashboard fetch failed ({response.status_code}): {response.text[:200]}"
                )
            return response.json()

    async def get_annotations(self, *, from_ms: int, to_ms: int) -> list[dict]:
        url = urljoin(self.connection.url + "/", "api/annotations")
        async with httpx.AsyncClient(timeout=QUERY_TIMEOUT, verify=False) as client:
            response = await client.get(
                url,
                params={"from": from_ms, "to": to_ms, "limit": 20},
                headers=self._headers(),
            )
            if response.status_code >= 400:
                raise GrafanaError(
                    f"Grafana annotations failed ({response.status_code}): {response.text[:200]}"
                )
            data = response.json()
            return data if isinstance(data, list) else []
