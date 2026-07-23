"""Orchestrate GitHub PR DevOps review workflow."""

from __future__ import annotations

from loguru import logger

from app.core.errors import sanitize_error_message
from app.ai.usage import UsageTracker
from app.modules.pr_reviewer.ai.review_analyzer import PrReviewAnalyzer
from app.modules.pr_reviewer.ai.review_formatter import format_review_markdown
from app.modules.pr_reviewer.github.github_client import GitHubClient, GitHubClientError
from app.modules.pr_reviewer.models.schemas import PrWebhookPayload
from app.notifications.pagerduty_notification_service import pagerduty_notification_service
from app.notifications.slack_notification_service import slack_notification_service
from app.notifications.teams_notification_service import teams_notification_service
from app.services.llm_usage_service import persist_usage_session
from app.storage.factory import get_llm_usage_store, get_pr_review_store
from app.storage.pr_review_store import PrReviewStore


class PrReviewService:
    PROGRESS_STEPS = {
        "queued": (0, "queued"),
        "fetching_pr_files": (20, "fetching_pr_files"),
        "building_prompt": (40, "building_prompt"),
        "discovering_mcp": (50, "discovering_mcp"),
        "running_ai_review": (60, "running_ai_review"),
        "posting_github_comment": (80, "posting_github_comment"),
        "completed": (100, "completed"),
    }

    def __init__(
        self,
        store: PrReviewStore | None = None,
        github_client: GitHubClient | None = None,
        analyzer: PrReviewAnalyzer | None = None,
    ) -> None:
        self.store = store or get_pr_review_store()
        self.github_client = github_client or GitHubClient()
        self.analyzer = analyzer or PrReviewAnalyzer()

    async def start_review(
        self,
        owner: str,
        repo: str,
        pull_request_number: int,
        metadata: PrWebhookPayload | None = None,
    ) -> str:
        review_id = await self.store.create(owner, repo, pull_request_number)
        await self._run_review(review_id, owner, repo, pull_request_number, metadata)
        return review_id

    async def enqueue_review(
        self,
        owner: str,
        repo: str,
        pull_request_number: int,
        metadata: PrWebhookPayload | None = None,
        user_id: str | None = None,
    ) -> str:
        review_id = await self.store.create(owner, repo, pull_request_number, user_id=user_id)
        return review_id

    async def process_review(
        self,
        review_id: str,
        owner: str,
        repo: str,
        pull_request_number: int,
        metadata: PrWebhookPayload | None = None,
    ) -> None:
        await self._run_review(review_id, owner, repo, pull_request_number, metadata)

    async def _run_review(
        self,
        review_id: str,
        owner: str,
        repo: str,
        pull_request_number: int,
        metadata: PrWebhookPayload | None,
    ) -> None:
        try:
            pr = metadata
            if pr is None:
                await self._set_step(review_id, "fetching_pr_files")
                pull = await self.github_client.fetch_pull_request(owner, repo, pull_request_number)
                user = pull.get("user") or {}
                pr = PrWebhookPayload(
                    owner=owner,
                    repository=repo,
                    pull_request_number=pull_request_number,
                    pull_request_title=pull.get("title", ""),
                    pull_request_body=pull.get("body") or "",
                    pull_request_author=user.get("login", ""),
                    base_branch=(pull.get("base") or {}).get("ref", ""),
                    head_branch=(pull.get("head") or {}).get("ref", ""),
                    commit_sha=(pull.get("head") or {}).get("sha", ""),
                    action="manual",
                )
            else:
                await self._set_step(review_id, "fetching_pr_files")

            await self.store.update_progress(
                review_id,
                status="fetching_pr_files",
                current_step="fetching_pr_files",
                progress_percentage=20,
                metadata={
                    "pull_request_title": pr.pull_request_title,
                    "pull_request_author": pr.pull_request_author,
                    "base_branch": pr.base_branch,
                    "head_branch": pr.head_branch,
                    "commit_sha": pr.commit_sha,
                },
            )

            files = await self.github_client.fetch_pull_request_files(
                owner, repo, pull_request_number
            )
            usable_files = [file for file in files if not file.skipped and file.patch]
            if not files:
                raise GitHubClientError("No changed files found in pull request")
            if not usable_files:
                raise GitHubClientError("No patch data available for changed files")

            await self._set_step(review_id, "building_prompt")
            await self._set_step(review_id, "discovering_mcp")
            review_record = await self.store.get(review_id)
            user_id = (review_record or {}).get("user_id")
            from app.services.mcp_enrichment_service import mcp_enrichment_service

            enriched = await mcp_enrichment_service.enrich(
                {},
                user_id,
                agent_type="pr_reviewer",
            )
            mcp_context = enriched.get("mcp_enrichment") or None
            if mcp_context:
                await self.store.update_mcp_context(review_id, mcp_context)

            await self._set_step(review_id, "running_ai_review")
            usage_store = get_llm_usage_store()
            await usage_store.initialize()
            with UsageTracker.session(
                scope_type="pr_review",
                scope_id=review_id,
                user_id=user_id,
                agent_type="pr_reviewer",
                default_call_kind="pr_review",
            ) as usage_session:
                analysis = await self.analyzer.analyze(pr, usable_files, mcp_context=mcp_context)
                await persist_usage_session(usage_store, usage_session)
            review_markdown = format_review_markdown(analysis)

            await self._set_step(review_id, "posting_github_comment")
            comment_url = await self.github_client.post_issue_comment(
                owner,
                repo,
                pull_request_number,
                review_markdown,
            )

            await self.store.complete(
                review_id,
                review_markdown=review_markdown,
                review_json=analysis.model_dump(),
                overall_risk=analysis.overall_risk,
                findings_count=len(analysis.findings),
                final_recommendation=analysis.final_recommendation,
                github_comment_url=comment_url or None,
            )
            review_record = await self.store.get(review_id)
            slack_notification_service.schedule_pr_review_notification(
                review_id=review_id,
                owner=owner,
                repository=repo,
                pull_request_number=pull_request_number,
                pull_request_title=pr.pull_request_title,
                overall_risk=analysis.overall_risk,
                final_recommendation=analysis.final_recommendation,
                findings_count=len(analysis.findings),
                user_id=(review_record or {}).get("user_id"),
            )
            pagerduty_notification_service.schedule_pr_review_notification(
                review_id=review_id,
                owner=owner,
                repository=repo,
                pull_request_number=pull_request_number,
                pull_request_title=pr.pull_request_title,
                overall_risk=analysis.overall_risk,
                final_recommendation=analysis.final_recommendation,
                findings_count=len(analysis.findings),
                user_id=(review_record or {}).get("user_id"),
            )
            teams_notification_service.schedule_pr_review_notification(
                review_id=review_id,
                owner=owner,
                repository=repo,
                pull_request_number=pull_request_number,
                pull_request_title=pr.pull_request_title,
                overall_risk=analysis.overall_risk,
                final_recommendation=analysis.final_recommendation,
                findings_count=len(analysis.findings),
                user_id=(review_record or {}).get("user_id"),
            )
            logger.info(
                "PR review completed | review_id={} repo={}/{} pr={}",
                review_id,
                owner,
                repo,
                pull_request_number,
            )
        except GitHubClientError as exc:
            await self.store.fail(review_id, str(exc))
        except Exception as exc:
            logger.exception("PR review failed | review_id={}", review_id)
            await self.store.fail(review_id, sanitize_error_message(str(exc)))

    async def _set_step(self, review_id: str, step: str) -> None:
        progress, current_step = self.PROGRESS_STEPS.get(step, (0, step))
        await self.store.update_progress(
            review_id,
            status=step if step != "completed" else "completed",
            current_step=current_step,
            progress_percentage=progress,
        )
