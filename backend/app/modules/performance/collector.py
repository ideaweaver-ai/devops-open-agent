"""SSH-based Linux performance metric collector.

Uses OpenSSH BatchMode so only passwordless auth is accepted. Callers must
configure SSH keys / agent on the host running the backend.
"""

from __future__ import annotations

import asyncio
import shlex
import subprocess
from dataclasses import dataclass

from loguru import logger

# Single remote script: keep output bounded for LLM context.
REMOTE_COLLECT_SCRIPT = r"""
set +e
echo '=== HOST ==='
hostname -f 2>/dev/null || hostname
uname -a 2>/dev/null || true
echo
echo '=== UPTIME / LOAD ==='
uptime 2>/dev/null || true
echo
echo '=== CPU COUNT ==='
nproc 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || true
echo
echo '=== MEMORY ==='
free -h 2>/dev/null || true
echo
echo '=== DISK USAGE ==='
df -hT 2>/dev/null | head -n 40 || true
echo
echo '=== TOP CPU PROCESSES ==='
ps aux --sort=-%cpu 2>/dev/null | head -n 21 || ps aux 2>/dev/null | head -n 21 || true
echo
echo '=== TOP MEMORY PROCESSES ==='
ps aux --sort=-%mem 2>/dev/null | head -n 21 || true
echo
echo '=== NETWORK SUMMARY (ss) ==='
ss -s 2>/dev/null || true
echo
echo '=== PRESSURE STALL INFO (if available) ==='
for f in /proc/pressure/cpu /proc/pressure/io /proc/pressure/memory; do
  if [ -r "$f" ]; then
    echo "-- $f"
    cat "$f" 2>/dev/null || true
  fi
done
true
"""


@dataclass
class HostCollectionResult:
    host: str
    success: bool
    evidence: str = ""
    error: str | None = None


class PerformanceCollector:
    """Collect Linux performance evidence over SSH."""

    def __init__(self, connect_timeout_seconds: int = 10, command_timeout_seconds: int = 45) -> None:
        self.connect_timeout_seconds = connect_timeout_seconds
        self.command_timeout_seconds = command_timeout_seconds

    async def collect(self, host: str) -> HostCollectionResult:
        return await asyncio.to_thread(self._collect_sync, host)

    def _collect_sync(self, host: str) -> HostCollectionResult:
        target = host.strip()
        if not target:
            return HostCollectionResult(host=host, success=False, error="Empty hostname")

        # Pass remote script on stdin so we avoid nested quoting issues.
        ssh_cmd = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "UserKnownHostsFile=/tmp/devops-open-agent-known-hosts",
            "-o",
            f"ConnectTimeout={self.connect_timeout_seconds}",
            "-o",
            "LogLevel=ERROR",
            target,
            "bash -s",
        ]

        try:
            completed = subprocess.run(
                ssh_cmd,
                input=REMOTE_COLLECT_SCRIPT,
                capture_output=True,
                text=True,
                timeout=self.command_timeout_seconds,
                check=False,
            )
        except FileNotFoundError:
            return HostCollectionResult(
                host=target,
                success=False,
                error="ssh client not found on the backend host. Install OpenSSH client.",
            )
        except subprocess.TimeoutExpired:
            return HostCollectionResult(
                host=target,
                success=False,
                error=f"SSH timed out after {self.command_timeout_seconds}s for {target}",
            )
        except Exception as exc:  # noqa: BLE001 — surface unexpected errors to the UI
            logger.warning("SSH collection failed | host={} error={}", target, exc)
            return HostCollectionResult(host=target, success=False, error=str(exc))

        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()

        if completed.returncode != 0:
            hint = stderr or f"ssh exited with code {completed.returncode}"
            if "Permission denied" in hint or "Authentication failed" in hint:
                hint = (
                    f"Passwordless SSH authentication failed for {shlex.quote(target)}. "
                    "Configure key-based SSH from the machine running DevOps Open Agent, "
                    "then retry."
                )
            elif "Connection refused" in hint or "No route to host" in hint:
                hint = f"Could not reach {target}: {stderr or 'connection failed'}"
            return HostCollectionResult(host=target, success=False, error=hint, evidence=stdout)

        if not stdout:
            return HostCollectionResult(
                host=target,
                success=False,
                error="SSH succeeded but no metrics were returned",
            )

        # Cap evidence size for LLM context
        max_chars = 24_000
        evidence = stdout if len(stdout) <= max_chars else stdout[:max_chars] + "\n... [truncated]"
        return HostCollectionResult(host=target, success=True, evidence=evidence)
