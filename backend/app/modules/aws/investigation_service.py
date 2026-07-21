"""AWS investigation orchestration service."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from uuid import UUID

from loguru import logger

from app.core.errors import sanitize_error_message
from app.models.investigation import ObservabilityResult
from app.modules.aws.client import AwsClientFactory
from app.modules.aws.collectors import (
    AwsCloudTrailCollector,
    AwsCloudWatchCollector,
    AwsConfigCollector,
    AwsDeploymentCorrelationCollector,
)
from app.modules.aws.discovery import (
    AwsAccountDiscovery,
    AwsAutoScalingDiscovery,
    AwsEc2Discovery,
    AwsLambdaDiscovery,
    AwsLoadBalancerDiscovery,
    AwsS3Discovery,
    AwsSecurityGroupDiscovery,
    AwsVpcDiscovery,
)
from app.modules.aws.errors import AwsCredentialsError, AwsError
from app.modules.aws.models import (
    AwsAccountInfo,
    AwsCloudTrailResult,
    AwsCloudWatchResult,
    AwsConfigResult,
    AwsDeploymentCorrelationResult,
    AwsInvestigationContext,
    AwsInvestigationRequest,
    AwsInvestigationResponse,
    AwsResourceDiscoveryResult,
    AwsTopologyResult,
)
from app.modules.aws.ai.root_cause_analyzer import AwsRootCauseAnalyzer
from app.modules.aws.investigation_scope import discovery_scope
from app.modules.aws.topology.builder import AwsTopologyBuilder
from app.observability.collector import ObservabilityCollector

ProgressCallback = Callable[[str, int], Awaitable[None] | None]

AWS_STEP_PROGRESS = {
    "Account Discovery": 6,
    "EC2 Discovery": 14,
    "Lambda Discovery": 22,
    "S3 Discovery": 28,
    "Network Discovery": 34,
    "Security Groups": 42,
    "Load Balancers": 50,
    "Topology": 58,
    "CloudWatch": 66,
    "CloudTrail": 74,
    "AWS Config": 82,
    "Observability": 90,
    "AI Diagnosis": 100,
}


class _AwsScopedCollectors:
    """Discovery/collectors bound to one AwsClientFactory (hub or assumed)."""

    def __init__(self, factory: AwsClientFactory) -> None:
        self.factory = factory
        self.account_discovery = AwsAccountDiscovery(factory)
        self.ec2_discovery = AwsEc2Discovery(factory)
        self.lambda_discovery = AwsLambdaDiscovery(factory)
        self.s3_discovery = AwsS3Discovery(factory)
        self.vpc_discovery = AwsVpcDiscovery(factory)
        self.security_group_discovery = AwsSecurityGroupDiscovery(factory)
        self.load_balancer_discovery = AwsLoadBalancerDiscovery(factory)
        self.autoscaling_discovery = AwsAutoScalingDiscovery(factory)
        self.cloudwatch_collector = AwsCloudWatchCollector(factory)
        self.cloudtrail_collector = AwsCloudTrailCollector(factory)
        self.config_collector = AwsConfigCollector(factory)
        self.deployment_correlation_collector = AwsDeploymentCorrelationCollector()
        self.topology_builder = AwsTopologyBuilder()


class AWSInvestigationService:
    """Collect structured AWS investigation evidence and optional AI diagnosis."""

    def __init__(self) -> None:
        self.account_discovery = AwsAccountDiscovery()
        self.root_cause_analyzer = AwsRootCauseAnalyzer()
        self.observability_collector = ObservabilityCollector()

    async def _report_progress(
        self,
        callback: ProgressCallback | None,
        step: str,
    ) -> None:
        if callback is None:
            return
        progress = AWS_STEP_PROGRESS.get(step, 0)
        result = callback(step, progress)
        if result is not None:
            await result

    async def list_accounts(
        self,
        region: str | None = None,
        user_id: str | UUID | None = None,
    ) -> list:
        target_region = region or "us-east-1"
        return await self.account_discovery.list_accounts(target_region, user_id=user_id)

    async def list_regions(
        self,
        account_id: str,
        region: str | None = None,
        user_id: str | UUID | None = None,
    ) -> list:
        target_region = region or "us-east-1"
        return await self.account_discovery.list_regions(
            account_id,
            target_region,
            user_id=user_id,
        )

    async def discover_topology(
        self,
        account_id: str,
        region: str,
        user_id: str | UUID | None = None,
    ) -> AwsTopologyResult:
        """Discover infrastructure resources and build a topology graph for a region."""
        factory = await self.account_discovery.resolve_factory(
            account_id,
            region,
            user_id=user_id,
        )
        scoped = _AwsScopedCollectors(factory)
        account = await scoped.account_discovery.discover_account(region)
        if account.account_id != account_id:
            raise AwsCredentialsError(
                f"Resolved credentials are for account {account.account_id}, "
                f"expected {account_id}."
            )

        instances, ebs_volumes, elastic_ips = await scoped.ec2_discovery.discover(region)
        lambda_functions = await scoped.lambda_discovery.discover(region)
        s3_buckets = await scoped.s3_discovery.discover(region)
        vpcs = await scoped.vpc_discovery.discover(region)

        instance_security_map = {
            instance.instance_id: instance.security_groups for instance in instances
        }
        security_groups = await scoped.security_group_discovery.discover(
            region,
            instance_security_map,
        )
        load_balancers, target_groups = await scoped.load_balancer_discovery.discover(region)
        auto_scaling_groups = await scoped.autoscaling_discovery.discover(region)

        resources = AwsResourceDiscoveryResult(
            ec2_instances=instances,
            lambda_functions=lambda_functions,
            s3_buckets=s3_buckets,
            vpcs=vpcs,
            security_groups=security_groups,
            load_balancers=load_balancers,
            target_groups=target_groups,
            auto_scaling_groups=auto_scaling_groups,
            ebs_volumes=ebs_volumes,
            elastic_ips=elastic_ips,
        )

        topology = scoped.topology_builder.build(resources, region)
        logger.info(
            "AWS topology discovered | account={} region={} nodes={} relationships={}",
            account_id,
            region,
            len(topology.nodes),
            len(topology.relationships),
        )
        return topology

    async def investigate(
        self,
        request: AwsInvestigationRequest,
        on_progress: ProgressCallback | None = None,
        user_id: str | None = None,
    ) -> AwsInvestigationResponse:
        notes: list[str] = []
        try:
            await self._report_progress(on_progress, "Account Discovery")
            factory = await self.account_discovery.resolve_factory(
                request.account_id,
                request.region,
                user_id=user_id,
            )
            scoped = _AwsScopedCollectors(factory)
            account = await scoped.account_discovery.discover_account(request.region)
            if account.account_id != request.account_id:
                raise AwsCredentialsError(
                    f"Resolved credentials are for account {account.account_id}, "
                    f"expected {request.account_id}."
                )
            if factory.assumed_account_id:
                notes.append(
                    f"Using STS AssumeRole credentials for account {request.account_id}."
                )

            scope = discovery_scope(request.issue_type)

            instances: list = []
            ebs_volumes: list = []
            elastic_ips: list = []
            if "ec2" in scope:
                await self._report_progress(on_progress, "EC2 Discovery")
                instances, ebs_volumes, elastic_ips = await scoped.ec2_discovery.discover(
                    request.region
                )
            else:
                notes.append(
                    f"Skipped EC2 discovery for focused troubleshooting mode: {request.issue_type}."
                )

            lambda_functions: list = []
            if "lambda" in scope:
                await self._report_progress(on_progress, "Lambda Discovery")
                lambda_functions = await scoped.lambda_discovery.discover(request.region)
            else:
                notes.append(
                    f"Skipped Lambda discovery for focused troubleshooting mode: {request.issue_type}."
                )

            s3_buckets: list = []
            if "s3" in scope:
                await self._report_progress(on_progress, "S3 Discovery")
                s3_buckets = await scoped.s3_discovery.discover(request.region)
            else:
                notes.append(
                    f"Skipped S3 discovery for focused troubleshooting mode: {request.issue_type}."
                )

            vpcs: list = []
            if "network" in scope:
                await self._report_progress(on_progress, "Network Discovery")
                vpcs = await scoped.vpc_discovery.discover(request.region)

            security_groups: list = []
            if "security_groups" in scope:
                instance_security_map = {
                    instance.instance_id: instance.security_groups for instance in instances
                }
                await self._report_progress(on_progress, "Security Groups")
                security_groups = await scoped.security_group_discovery.discover(
                    request.region,
                    instance_security_map,
                )

            load_balancers: list = []
            target_groups: list = []
            auto_scaling_groups: list = []
            if "load_balancers" in scope:
                await self._report_progress(on_progress, "Load Balancers")
                load_balancers, target_groups = await scoped.load_balancer_discovery.discover(
                    request.region
                )
                auto_scaling_groups = await scoped.autoscaling_discovery.discover(request.region)

            resources = AwsResourceDiscoveryResult(
                ec2_instances=instances,
                lambda_functions=lambda_functions,
                s3_buckets=s3_buckets,
                vpcs=vpcs,
                security_groups=security_groups,
                load_balancers=load_balancers,
                target_groups=target_groups,
                auto_scaling_groups=auto_scaling_groups,
                ebs_volumes=ebs_volumes,
                elastic_ips=elastic_ips,
            )

            await self._report_progress(on_progress, "Topology")
            topology = scoped.topology_builder.build(resources, request.region)
            await self._report_progress(on_progress, "CloudWatch")
            cloudwatch = await scoped.cloudwatch_collector.collect(
                request.region,
                instances,
                window=request.cloudwatch_window,
                lambda_functions=lambda_functions,
            )
            await self._report_progress(on_progress, "CloudTrail")
            cloudtrail = (
                await scoped.cloudtrail_collector.collect(
                    request.region,
                    instances=instances,
                    security_groups=security_groups,
                    cloudwatch_window=request.cloudwatch_window,
                )
                if instances or security_groups
                else AwsCloudTrailResult(collected=False, lookback_hours=24)
            )
            await self._report_progress(on_progress, "AWS Config")
            aws_config = (
                await scoped.config_collector.collect(request.region, instances)
                if instances
                else AwsConfigResult(enabled=False)
            )
            deployment_correlation = await scoped.deployment_correlation_collector.collect()

            await self._report_progress(on_progress, "Observability")
            search_hints = [
                request.account_id,
                request.region,
                *[inst.instance_id for inst in instances[:8] if getattr(inst, "instance_id", None)],
                *[
                    (inst.name or "")
                    for inst in instances[:8]
                    if getattr(inst, "name", None)
                ],
            ]
            observability = await self.observability_collector.collect(
                request.account_id or "",
                user_id=user_id,
                agent_type="aws",
                search_hints=[hint for hint in search_hints if hint],
            )

            investigation = AwsInvestigationContext(
                account_id=request.account_id,
                region=request.region,
                collected_at=datetime.now(timezone.utc).isoformat(),
                issue_type=request.issue_type,
                query=request.query,
                resource_counts={
                    "ec2_instances": len(instances),
                    "lambda_functions": len(lambda_functions),
                    "s3_buckets": len(s3_buckets),
                    "vpcs": len(vpcs),
                    "security_groups": len(security_groups),
                    "load_balancers": len(load_balancers),
                    "target_groups": len(target_groups),
                    "auto_scaling_groups": len(auto_scaling_groups),
                    "ebs_volumes": len(ebs_volumes),
                    "elastic_ips": len(elastic_ips),
                    "topology_nodes": len(topology.nodes),
                    "topology_relationships": len(topology.relationships),
                    "observability_findings": len(observability.findings),
                },
                notes=notes,
            )

            logger.info(
                "AWS investigation completed | account={} region={} instances={} relationships={} obs_findings={}",
                request.account_id,
                request.region,
                len(instances),
                len(topology.relationships),
                len(observability.findings),
            )

            response = AwsInvestigationResponse(
                status="success",
                account=account,
                resources=resources,
                topology=topology,
                cloudwatch=cloudwatch,
                cloudtrail=cloudtrail,
                aws_config=aws_config,
                deployment_correlation=deployment_correlation,
                observability=observability,
                investigation=investigation,
            )

            if request.include_ai:
                await self._report_progress(on_progress, "AI Diagnosis")
                logger.info(
                    "Running AWS AI diagnosis | account={} region={}",
                    request.account_id,
                    request.region,
                )
                diagnosis_payload = response.model_dump(mode="json")
                if user_id:
                    from app.services.mcp_enrichment_service import mcp_enrichment_service

                    diagnosis_payload = await mcp_enrichment_service.enrich(
                        diagnosis_payload,
                        user_id,
                        agent_type="aws",
                    )
                if user_id and getattr(request, "include_rag", False):
                    from app.services.rag_service import rag_service

                    diagnosis_payload = await rag_service.enrich(
                        diagnosis_payload,
                        user_id,
                        agent_type="aws",
                    )
                diagnosis = await self.root_cause_analyzer.analyze(diagnosis_payload)
                response.diagnosis = diagnosis
                if diagnosis.llm_error:
                    response.status = "partial_success"

            return response
        except AwsCredentialsError as exc:
            return self._error_response(request, sanitize_error_message(str(exc)))
        except AwsError as exc:
            return self._error_response(request, sanitize_error_message(str(exc)))
        except Exception as exc:
            logger.exception("AWS investigation failed")
            return self._error_response(request, sanitize_error_message(str(exc)))

    def _error_response(self, request: AwsInvestigationRequest, error: str) -> AwsInvestigationResponse:
        return AwsInvestigationResponse(
            status="error",
            account=AwsAccountInfo(
                account_id=request.account_id,
                account_name=None,
                enabled_regions=[],
                credential_source="unknown",
            ),
            resources=AwsResourceDiscoveryResult(),
            topology=AwsTopologyResult(),
            cloudwatch=AwsCloudWatchResult(collected=False, window=request.cloudwatch_window),
            cloudtrail=AwsCloudTrailResult(collected=False),
            aws_config=AwsConfigResult(enabled=False, error=error),
            deployment_correlation=AwsDeploymentCorrelationResult(),
            observability=ObservabilityResult(),
            investigation=AwsInvestigationContext(
                account_id=request.account_id,
                region=request.region,
                collected_at=datetime.now(timezone.utc).isoformat(),
                notes=[error],
            ),
            error=error,
        )
