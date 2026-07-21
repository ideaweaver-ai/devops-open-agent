"""Investigation service orchestrating Kubernetes evidence collection."""

from collections.abc import Awaitable, Callable

from loguru import logger

from app.core.errors import sanitize_error_message
from app.deployments.correlation import DeploymentCorrelationCollector
from app.graph.topology_builder import TopologyBuilder
from app.kubernetes.cluster_discovery import ClusterDiscovery
from app.kubernetes.cluster_manager import ClusterManager
from app.kubernetes.deployment_inspector import DeploymentInspector
from app.kubernetes.events_analyzer import EventsAnalyzer
from app.kubernetes.executor import KubectlExecutor
from app.kubernetes.logs_collector import LogsCollector
from app.kubernetes.network_inspector import NetworkInspector
from app.kubernetes.pod_inspector import PodInspector
from app.kubernetes.resource_discovery import ResourceDiscovery
from app.models.diagnosis import InvestigationRequest
from app.models.investigation import (
    ClusterInfo,
    DeploymentCorrelationResult,
    DeploymentInspectionResult,
    EventsAnalysisResult,
    InvestigationDetails,
    InvestigationResponse,
    LogsCollectionResult,
    NetworkInspectionResult,
    ObservabilityResult,
    PodInspectionResult,
    ResourceDiscoveryResult,
    TopologyResult,
)
from app.models.investigation_job import INVESTIGATION_STEPS
from app.observability.collector import ObservabilityCollector

ProgressCallback = Callable[[str, int], Awaitable[None] | None]


class InvestigationService:
    """Orchestrate the Kubernetes Investigation Engine."""

    STEP_PROGRESS = {
        "Cluster Discovery": 11,
        "Resource Discovery": 22,
        "Pod Inspection": 33,
        "Log Collection": 44,
        "Event Analysis": 55,
        "Deployment Inspection": 66,
        "Network Inspection": 77,
        "Topology Extraction": 88,
        "AI Diagnosis": 100,
    }

    def __init__(self, cluster_manager: ClusterManager | None = None) -> None:
        self.cluster_manager = cluster_manager or ClusterManager()
        self.observability_collector = ObservabilityCollector()
        self.deployment_correlation_collector = DeploymentCorrelationCollector()

    async def _report_progress(
        self,
        callback: ProgressCallback | None,
        step: str,
    ) -> None:
        if callback is None:
            return
        progress = self.STEP_PROGRESS.get(step, 0)
        result = callback(step, progress)
        if result is not None:
            await result

    async def investigate(
        self,
        request: InvestigationRequest,
        on_progress: ProgressCallback | None = None,
        user_id: str | None = None,
    ) -> InvestigationResponse:
        cluster_config = self.cluster_manager.resolve(request.cluster_id)
        executor = KubectlExecutor(
            kubeconfig_path=cluster_config.kubeconfig_path,
            context=cluster_config.context,
        )

        logger.info(
            "Starting investigation | cluster_id={} context={}",
            request.cluster_id,
            cluster_config.context,
        )

        await self._report_progress(on_progress, "Cluster Discovery")
        cluster_info, cluster_error = ClusterDiscovery(
            executor, cluster_id=request.cluster_id
        ).discover()
        if cluster_error:
            return self._error_response(
                cluster_info=cluster_info,
                message=sanitize_error_message(cluster_error),
            )

        await self._report_progress(on_progress, "Resource Discovery")
        resources, cache = ResourceDiscovery(executor).discover(namespace=request.namespace)

        await self._report_progress(on_progress, "Pod Inspection")
        pod_inspection = PodInspector(executor).inspect_pods(cache.pods)

        await self._report_progress(on_progress, "Log Collection")
        logs = LogsCollector(executor).collect(pod_inspection.problematic_pods)

        await self._report_progress(on_progress, "Event Analysis")
        events = EventsAnalyzer(executor).analyze_events(cache.events)

        await self._report_progress(on_progress, "Deployment Inspection")
        deployment_inspection = DeploymentInspector(executor).inspect_deployments(cache.deployments)

        await self._report_progress(on_progress, "Network Inspection")
        network_inspection = NetworkInspector(executor).inspect_from_cache(
            cache.services,
            cache.endpoints,
            cache.pods,
            cache.ingresses,
        )

        await self._report_progress(on_progress, "Topology Extraction")
        topology = TopologyBuilder(executor).build(resources, endpoints_raw=cache.endpoints)
        pod_names = [pod.name for pod in pod_inspection.problematic_pods]
        observability = await self.observability_collector.collect(
            request.cluster_id or "",
            user_id=user_id,
            namespace=request.namespace,
            pod_names=pod_names,
            agent_type="kubernetes",
        )
        deployment_correlation = await self.deployment_correlation_collector.collect(
            request.cluster_id
        )

        investigation = InvestigationDetails(
            pods=pod_inspection,
            logs=logs,
            events=events,
            deployments=deployment_inspection,
            network=network_inspection,
        )

        logger.info(
            "Investigation complete | cluster_id={} pods={} problematic_pods={} relationships={}",
            request.cluster_id,
            pod_inspection.total_pods,
            len(pod_inspection.problematic_pods),
            len(topology.relationships),
        )

        return InvestigationResponse(
            status="success",
            cluster=cluster_info,
            resources=resources,
            topology=topology,
            observability=observability,
            deployments=deployment_correlation,
            investigation=investigation,
        )

    @classmethod
    def get_steps(cls, include_ai: bool) -> list[str]:
        if include_ai:
            return INVESTIGATION_STEPS
        return [step for step in INVESTIGATION_STEPS if step != "AI Diagnosis"]

    def _error_response(
        self,
        cluster_info: ClusterInfo,
        message: str,
    ) -> InvestigationResponse:
        return InvestigationResponse(
            status="error",
            cluster=cluster_info,
            resources=ResourceDiscoveryResult(),
            topology=TopologyResult(),
            observability=ObservabilityResult(),
            deployments=DeploymentCorrelationResult(),
            investigation=InvestigationDetails(
                pods=PodInspectionResult(healthy=True, total_pods=0, problematic_pods=[]),
                logs=LogsCollectionResult(collected=False, pod_count=0, logs=[]),
                events=EventsAnalysisResult(total_events=0, findings=[], summary=[]),
                deployments=DeploymentInspectionResult(
                    healthy=True, deployments_checked=0, issues=[]
                ),
                network=NetworkInspectionResult(healthy=True, services_checked=0, issues=[]),
            ),
            error=message,
        )
