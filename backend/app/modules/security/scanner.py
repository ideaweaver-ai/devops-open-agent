"""Trivy CLI wrapper for container image and Kubernetes scanning."""

from __future__ import annotations

import asyncio
import json
import pathlib
from typing import Any

from loguru import logger

from app.core.config import get_settings
from app.kubernetes.kubeconfig_resolver import prepare_kubeconfig
from app.modules.security.models import (
    MisconfigFinding,
    ScanType,
    VulnerabilityFinding,
)

TRIVY_TIMEOUT_SECONDS = 600
_trivy_lock = asyncio.Lock()


class TrivyScanner:
    """Thin async wrapper around the ``trivy`` CLI binary."""

    def _resolve_kubeconfig(self) -> str | None:
        settings = get_settings()
        return prepare_kubeconfig(
            configured_path=settings.kubeconfig_path,
            api_host_rewrite=settings.kube_api_host_rewrite,
            output_dir="data",
        )

    async def scan_image(
        self,
        image_name: str,
        severity_filter: list[str] | None = None,
    ) -> dict[str, Any]:
        cmd = [
            "trivy",
            "image",
            "--format",
            "json",
            "--timeout",
            "10m",
        ]
        if severity_filter:
            cmd += ["--severity", ",".join(severity_filter)]
        cmd.append(image_name)
        raw = await self._run(cmd)
        return self._parse_image_results(raw, image_name)

    async def scan_kubernetes(
        self,
        namespace: str | None = None,
        context: str | None = None,
        severity_filter: list[str] | None = None,
    ) -> dict[str, Any]:
        kubeconfig = self._resolve_kubeconfig()

        cmd = [
            "trivy",
            "k8s",
            "--format",
            "json",
            "--report",
            "all",
            "--timeout",
            "10m",
        ]
        if kubeconfig:
            cmd += ["--kubeconfig", kubeconfig]
        if severity_filter:
            cmd += ["--severity", ",".join(severity_filter)]
        if namespace:
            cmd += ["--include-namespaces", namespace]
        if context:
            cmd.append(context)
        raw = await self._run(cmd)
        return self._parse_k8s_results(raw, namespace)

    @staticmethod
    def _kill_orphan_trivy_procs() -> None:
        """Kill leftover ``trivy`` processes that may hold the flock on fanal.db."""
        import os
        import signal

        my_pid = os.getpid()
        proc_dir = pathlib.Path("/proc")
        if not proc_dir.exists():
            return
        for entry in proc_dir.iterdir():
            if not entry.name.isdigit():
                continue
            pid = int(entry.name)
            if pid == my_pid:
                continue
            try:
                cmdline = (entry / "cmdline").read_bytes()
                if b"trivy" in cmdline:
                    logger.warning("Killing orphan Trivy process | pid={}", pid)
                    os.kill(pid, signal.SIGKILL)
            except (OSError, PermissionError):
                pass

    async def _run(self, cmd: list[str]) -> dict[str, Any]:
        async with _trivy_lock:
            self._kill_orphan_trivy_procs()
            logger.info("Running Trivy | cmd={}", " ".join(cmd))
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=TRIVY_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                proc.kill()
                raise RuntimeError(
                    f"Trivy timed out after {TRIVY_TIMEOUT_SECONDS}s"
                ) from None

        stdout_text = stdout.decode(errors="replace")
        stderr_text = stderr.decode(errors="replace")

        if proc.returncode != 0:
            logger.warning(
                "Trivy exited with code {} | stderr={}",
                proc.returncode,
                stderr_text[:500],
            )

        if not stdout_text.strip():
            hint = ""
            stderr_lower = stderr_text.lower()
            if "unable to find the specified image" in stderr_lower or "no such image" in stderr_lower:
                hint = " (image not found — check the image name for typos and ensure it exists locally or on the registry)"
            elif "unauthorized" in stderr_lower:
                hint = " (authentication required — the registry may need credentials)"
            elif "unable to initialize a scan service" in stderr_lower:
                hint = " (Trivy could not start the scan — try running with --debug for details)"
            raise RuntimeError(
                f"Trivy scan failed (exit code {proc.returncode}){hint}. "
                f"stderr: {stderr_text[:500]}"
            )

        try:
            return json.loads(stdout_text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Trivy output is not valid JSON: {exc}. "
                f"First 500 chars: {stdout_text[:500]}"
            ) from exc

    def _parse_image_results(
        self,
        raw: dict[str, Any],
        image_name: str,
    ) -> dict[str, Any]:
        vulns: list[VulnerabilityFinding] = []
        misconfigs: list[MisconfigFinding] = []
        summary: dict[str, int] = {}

        for result in raw.get("Results") or []:
            for v in result.get("Vulnerabilities") or []:
                sev = v.get("Severity", "UNKNOWN")
                summary[sev] = summary.get(sev, 0) + 1
                vulns.append(
                    VulnerabilityFinding(
                        vulnerability_id=v.get("VulnerabilityID", ""),
                        pkg_name=v.get("PkgName", ""),
                        installed_version=v.get("InstalledVersion", ""),
                        fixed_version=v.get("FixedVersion"),
                        severity=sev,
                        title=v.get("Title", ""),
                        description=(v.get("Description") or "")[:500],
                    )
                )
            for m in result.get("Misconfigurations") or []:
                sev = m.get("Severity", "UNKNOWN")
                summary[f"misconfig_{sev}"] = summary.get(f"misconfig_{sev}", 0) + 1
                misconfigs.append(
                    MisconfigFinding(
                        id=m.get("ID", ""),
                        title=m.get("Title", ""),
                        description=(m.get("Description") or "")[:500],
                        severity=sev,
                        resolution=m.get("Resolution", ""),
                        resource=m.get("Resource"),
                    )
                )

        return {
            "scan_type": ScanType.IMAGE.value,
            "target": image_name,
            "vulnerabilities": [v.model_dump() for v in vulns],
            "misconfigurations": [m.model_dump() for m in misconfigs],
            "summary": summary,
        }

    def _parse_k8s_results(
        self,
        raw: dict[str, Any],
        namespace: str | None,
    ) -> dict[str, Any]:
        vulns: list[VulnerabilityFinding] = []
        misconfigs: list[MisconfigFinding] = []
        summary: dict[str, int] = {}

        resources = raw.get("Resources") or raw.get("Results") or []
        if isinstance(resources, dict):
            resources = [resources]

        for resource in resources:
            results = resource.get("Results") or []
            resource_name = resource.get("Namespace", "") + "/" + resource.get("Kind", "")
            for result in results:
                for v in result.get("Vulnerabilities") or []:
                    sev = v.get("Severity", "UNKNOWN")
                    summary[sev] = summary.get(sev, 0) + 1
                    vulns.append(
                        VulnerabilityFinding(
                            vulnerability_id=v.get("VulnerabilityID", ""),
                            pkg_name=v.get("PkgName", ""),
                            installed_version=v.get("InstalledVersion", ""),
                            fixed_version=v.get("FixedVersion"),
                            severity=sev,
                            title=v.get("Title", ""),
                            description=(v.get("Description") or "")[:500],
                        )
                    )
                for m in result.get("Misconfigurations") or []:
                    sev = m.get("Severity", "UNKNOWN")
                    summary[f"misconfig_{sev}"] = summary.get(f"misconfig_{sev}", 0) + 1
                    misconfigs.append(
                        MisconfigFinding(
                            id=m.get("ID", ""),
                            title=m.get("Title", ""),
                            description=(m.get("Description") or "")[:500],
                            severity=sev,
                            resolution=m.get("Resolution", ""),
                            resource=resource_name or m.get("Resource"),
                        )
                    )

        target = f"cluster (namespace={namespace})" if namespace else "cluster (all namespaces)"
        return {
            "scan_type": ScanType.KUBERNETES.value,
            "target": target,
            "vulnerabilities": [v.model_dump() for v in vulns],
            "misconfigurations": [m.model_dump() for m in misconfigs],
            "summary": summary,
        }
