"""Investigation storage factory."""

from functools import lru_cache

from app.core.config import get_settings
from app.storage.base import BaseInvestigationStore
from app.storage.audit_store import AuditStore
from app.storage.llm_usage_store import LlmUsageStore
from app.storage.pr_review_store import PrReviewStore
from app.storage.sqlite_store import SQLiteInvestigationStore


@lru_cache
def get_investigation_store() -> BaseInvestigationStore:
    settings = get_settings()
    return SQLiteInvestigationStore(database_path=settings.database_path)


@lru_cache
def get_pr_review_store() -> PrReviewStore:
    settings = get_settings()
    return PrReviewStore(database_path=settings.database_path)


@lru_cache
def get_llm_usage_store() -> LlmUsageStore:
    settings = get_settings()
    return LlmUsageStore(database_path=settings.database_path)


@lru_cache
def get_audit_store() -> AuditStore:
    settings = get_settings()
    return AuditStore(database_path=settings.database_path)
