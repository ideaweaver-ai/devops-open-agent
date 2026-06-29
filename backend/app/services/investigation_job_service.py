"""Async investigation job orchestration with progress tracking."""

import uuid

from loguru import logger

from app.core.errors import sanitize_error_message
from app.models.diagnosis import InvestigationRequest
from app.models.investigation import InvestigationResponse
from app.modules.aws.investigation_service import AWSInvestigationService
from app.modules.aws.models import AwsInvestigationRequest, AwsInvestigationResponse
from app.modules.cloud_cost_detector.services.investigation_service import CloudCostInvestigationService
from app.modules.cloud_cost_detector.models.schemas import CloudCostInvestigationResponse
from app.notifications.pagerduty_notification_service import pagerduty_notification_service
from app.notifications.slack_notification_service import slack_notification_service
from app.services.diagnosis_service import DiagnosisService
from app.services.investigation_service import InvestigationService
from app.storage.base import BaseInvestigationStore
from app.storage.factory import get_investigation_store


class InvestigationJobService:
    """Manage background investigations with persisted progress and history."""

    def __init__(
        self,
        investigation_service: InvestigationService | None = None,
        aws_investigation_service: AWSInvestigationService | None = None,
        diagnosis_service: DiagnosisService | None = None,
        store: BaseInvestigationStore | None = None,
    ) -> None:
        self.investigation_service = investigation_service or InvestigationService()
        self.aws_investigation_service = aws_investigation_service or AWSInvestigationService()
        self.cloud_cost_investigation_service = CloudCostInvestigationService()
        self.diagnosis_service = diagnosis_service or DiagnosisService()
        self.store = store or get_investigation_store()

    async def initialize(self) -> None:
        await self.store.initialize()

    async def start_investigation(
        self,
        request: InvestigationRequest,
        user_id: str | None = None,
    ) -> str:
        investigation_id = str(uuid.uuid4())
        scope_id = (
            f"{request.account_id}/{request.region}"
            if request.agent_type in {"aws", "cloud_cost"}
            else (request.cluster_id or "unknown")
        )
        await self.store.create(
            investigation_id,
            scope_id,
            request.include_ai,
            agent_type=request.agent_type,
            user_id=user_id,
        )
        return investigation_id

    async def run_investigation(
        self,
        investigation_id: str,
        request: InvestigationRequest,
    ) -> None:
        if request.agent_type == "aws":
            await self._run_aws_investigation(investigation_id, request)
            return
        if request.agent_type == "cloud_cost":
            await self._run_cloud_cost_investigation(investigation_id, request)
            return
        await self._run_kubernetes_investigation(investigation_id, request)

    async def _run_kubernetes_investigation(
        self,
        investigation_id: str,
        request: InvestigationRequest,
    ) -> None:
        async def on_progress(step: str, progress_percentage: int) -> None:
            await self.store.update_progress(
                investigation_id,
                status="running",
                current_step=step,
                progress_percentage=progress_percentage,
            )

        try:
            response = await self.investigation_service.investigate(
                request,
                on_progress=on_progress,
            )

            if request.include_ai and response.status == "success":
                await self.store.update_progress(
                    investigation_id,
                    status="running",
                    current_step="AI Diagnosis",
                    progress_percentage=95,
                )
                diagnosis = await self.diagnosis_service.diagnose(response)
                response.diagnosis = diagnosis
                if diagnosis.llm_error:
                    response.status = "partial_success"
                await self.store.complete(
                    investigation_id,
                    status=response.status,
                    result=response.model_dump(mode="json"),
                    root_cause=diagnosis.root_cause,
                    confidence=diagnosis.confidence_score,
                )
                await self._notify_integrations(
                    investigation_id,
                    agent_type="kubernetes",
                    scope_label=request.cluster_id or "unknown",
                    diagnosis=diagnosis,
                )
                return

            if response.status == "error":
                await self.store.fail(
                    investigation_id,
                    error=sanitize_error_message(response.error or "Investigation failed"),
                    result=response.model_dump(mode="json"),
                )
                return

            await self.store.complete(
                investigation_id,
                status=response.status,
                result=response.model_dump(mode="json"),
                root_cause=None,
                confidence=None,
            )
        except Exception as exc:
            logger.exception("Investigation job failed | id={}", investigation_id)
            await self.store.fail(
                investigation_id,
                error=sanitize_error_message(str(exc)),
            )

    async def _run_aws_investigation(
        self,
        investigation_id: str,
        request: InvestigationRequest,
    ) -> None:
        async def on_progress(step: str, progress_percentage: int) -> None:
            await self.store.update_progress(
                investigation_id,
                status="running",
                current_step=step,
                progress_percentage=progress_percentage,
            )

        aws_request = AwsInvestigationRequest(
            account_id=request.account_id or "",
            region=request.region or "",
            cloudwatch_window=request.cloudwatch_window,  # type: ignore[arg-type]
            issue_type=request.issue_type,  # type: ignore[arg-type]
            query=request.query,
            include_ai=request.include_ai,
        )

        try:
            response = await self.aws_investigation_service.investigate(
                aws_request,
                on_progress=on_progress,
            )

            if response.status == "error":
                await self.store.fail(
                    investigation_id,
                    error=sanitize_error_message(response.error or "AWS investigation failed"),
                    result=response.model_dump(mode="json"),
                )
                return

            diagnosis = response.diagnosis
            await self.store.complete(
                investigation_id,
                status=response.status,
                result=response.model_dump(mode="json"),
                root_cause=diagnosis.root_cause if diagnosis else None,
                confidence=diagnosis.confidence_score if diagnosis else None,
            )
            if diagnosis:
                await self._notify_integrations(
                    investigation_id,
                    agent_type="aws",
                    scope_label=f"{request.account_id}/{request.region}",
                    diagnosis=diagnosis,
                )
        except Exception as exc:
            logger.exception("AWS investigation job failed | id={}", investigation_id)
            await self.store.fail(
                investigation_id,
                error=sanitize_error_message(str(exc)),
            )

    async def _run_cloud_cost_investigation(
        self,
        investigation_id: str,
        request: InvestigationRequest,
    ) -> None:
        async def on_progress(step: str, progress_percentage: int) -> None:
            await self.store.update_progress(
                investigation_id,
                status="running",
                current_step=step,
                progress_percentage=progress_percentage,
            )

        try:
            response = await self.cloud_cost_investigation_service.investigate(
                account_id=request.account_id or "",
                region=request.region or "",
                include_ai=request.include_ai,
                on_progress=on_progress,
            )

            if response.status == "error":
                await self.store.fail(
                    investigation_id,
                    error=sanitize_error_message(response.error or "Cloud cost analysis failed"),
                    result=response.model_dump(mode="json"),
                )
                return

            diagnosis = response.diagnosis
            await self.store.complete(
                investigation_id,
                status=response.status,
                result=response.model_dump(mode="json"),
                root_cause=diagnosis.root_cause if diagnosis else None,
                confidence=diagnosis.confidence_score if diagnosis else None,
            )
            if diagnosis:
                await self._notify_integrations(
                    investigation_id,
                    agent_type="cloud_cost",
                    scope_label=f"{request.account_id}/{request.region}",
                    diagnosis=diagnosis,
                )
        except Exception as exc:
            logger.exception("Cloud cost investigation job failed | id={}", investigation_id)
            await self.store.fail(
                investigation_id,
                error=sanitize_error_message(str(exc)),
            )

    async def get_status(self, investigation_id: str) -> dict | None:
        return await self.store.get_status(investigation_id)

    async def get_result(self, investigation_id: str) -> dict | None:
        return await self.store.get_result(investigation_id)

    async def list_history(
        self,
        limit: int = 50,
        agent_type: str | None = None,
    ) -> list[dict]:
        return await self.store.list_history(limit=limit, agent_type=agent_type)

    @staticmethod
    def parse_kubernetes_result(record: dict) -> InvestigationResponse | None:
        result = record.get("result")
        if not result:
            return None
        return InvestigationResponse.model_validate(result)

    @staticmethod
    def parse_aws_result(record: dict) -> AwsInvestigationResponse | None:
        result = record.get("result")
        if not result:
            return None
        return AwsInvestigationResponse.model_validate(result)

    @staticmethod
    def parse_cloud_cost_result(record: dict) -> CloudCostInvestigationResponse | None:
        result = record.get("result")
        if not result:
            return None
        return CloudCostInvestigationResponse.model_validate(result)

    @staticmethod
    def parse_result(record: dict) -> InvestigationResponse | None:
        return InvestigationJobService.parse_kubernetes_result(record)

    async def _notify_integrations(
        self,
        investigation_id: str,
        agent_type: str,
        scope_label: str,
        diagnosis,
    ) -> None:
        record = await self.store.get_status(investigation_id)
        user_id = record.get("user_id") if record else None
        slack_notification_service.schedule_investigation_notification(
            investigation_id=investigation_id,
            agent_type=agent_type,
            scope_label=scope_label,
            diagnosis=diagnosis,
            user_id=user_id,
        )
        pagerduty_notification_service.schedule_investigation_notification(
            investigation_id=investigation_id,
            agent_type=agent_type,
            scope_label=scope_label,
            diagnosis=diagnosis,
            user_id=user_id,
        )
