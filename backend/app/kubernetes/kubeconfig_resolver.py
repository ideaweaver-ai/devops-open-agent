"""Prepare kubeconfig for Docker and local Kubernetes access."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import yaml
from loguru import logger

LOCAL_API_HOSTS = {"127.0.0.1", "localhost", "::1"}
DEFAULT_DOCKER_API_HOST = "host.docker.internal"


def is_running_in_docker() -> bool:
    return Path("/.dockerenv").exists()


def get_api_host_rewrite(explicit_rewrite: str = "") -> str:
    if explicit_rewrite:
        return explicit_rewrite
    if is_running_in_docker():
        return DEFAULT_DOCKER_API_HOST
    return ""


def get_source_kubeconfig_path(configured_path: str = "") -> str | None:
    if configured_path and Path(configured_path).exists():
        return configured_path
    env_path = os.environ.get("KUBECONFIG", "").strip()
    if env_path:
        first_path = env_path.split(os.pathsep)[0]
        if Path(first_path).exists():
            return first_path
    default_path = Path.home() / ".kube" / "config"
    if default_path.exists():
        return str(default_path)
    if configured_path:
        return configured_path
    return None


def _rewrite_server_url(server: str, rewrite_host: str) -> str:
    parsed = urlparse(server)
    if parsed.hostname not in LOCAL_API_HOSTS:
        return server
    port = parsed.port
    netloc = f"{rewrite_host}:{port}" if port else rewrite_host
    return urlunparse(parsed._replace(netloc=netloc))


def _output_is_fresh(source: Path, output_path: Path) -> bool:
    if not output_path.exists():
        return False
    try:
        return source.stat().st_mtime <= output_path.stat().st_mtime
    except OSError:
        return False


def prepare_kubeconfig(
    configured_path: str = "",
    api_host_rewrite: str = "",
    output_dir: str = "data",
) -> str | None:
    """Return a kubeconfig path, rewriting localhost API servers when needed."""
    source_path = get_source_kubeconfig_path(configured_path)
    if not source_path or not Path(source_path).exists():
        return source_path

    rewrite_host = get_api_host_rewrite(api_host_rewrite)
    if not rewrite_host:
        return source_path

    source = Path(source_path)
    output_path = Path(output_dir) / "kubeconfig.docker.yaml"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if _output_is_fresh(source, output_path):
        return str(output_path)

    with source.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    rewritten = False
    for cluster in config.get("clusters", []) or []:
        cluster_info = cluster.get("cluster") or {}
        server = cluster_info.get("server")
        if not server:
            continue
        new_server = _rewrite_server_url(server, rewrite_host)
        if new_server != server:
            cluster_info["server"] = new_server
            cluster_info.pop("certificate-authority-data", None)
            cluster_info["insecure-skip-tls-verify"] = True
            rewritten = True

    if not rewritten:
        return source_path

    with output_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, default_flow_style=False)

    logger.info(
        "Prepared Docker-compatible kubeconfig | source={} output={} rewrite_host={}",
        source_path,
        output_path,
        rewrite_host,
    )
    return str(output_path)


class KubeconfigResolver:
    """Kubeconfig resolution for executors."""

    def __init__(self, configured_path: str = "", api_host_rewrite: str = "", output_dir: str = "data") -> None:
        self.configured_path = configured_path
        self.api_host_rewrite = api_host_rewrite
        self.output_dir = output_dir

    def resolve(self) -> str | None:
        return prepare_kubeconfig(
            configured_path=self.configured_path,
            api_host_rewrite=self.api_host_rewrite,
            output_dir=self.output_dir,
        )
