"""System readiness checks for production-style validation."""

from app.ai.llm_factory import ALLOWED_PROVIDERS, LLMProviderFactory
from app.core.config import Settings, get_settings
from app.kubernetes.kubeconfig_service import KubeconfigService
from app.storage.factory import get_investigation_store


class ReadinessService:
    """Validate core dependencies required for investigations."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.kubeconfig_service = KubeconfigService(self.settings)

    async def check(self) -> dict[str, bool]:
        kubectl_ok = self.kubeconfig_service.kubectl_available()
        kubeconfig_ok = self.kubeconfig_service.has_kubeconfig()
        cluster_reachable = (
            self.kubeconfig_service.cluster_reachable()
            if kubectl_ok and kubeconfig_ok
            else False
        )
        database_ok = await self._check_database()
        llm_ok = self._check_llm_provider()
        return {
            "kubectl": kubectl_ok,
            "kubeconfig": kubeconfig_ok,
            "cluster_reachable": cluster_reachable,
            "llm_provider": llm_ok,
            "database": database_ok,
        }

    async def _check_database(self) -> bool:
        try:
            store = get_investigation_store()
            await store.list_history(limit=1)
            return True
        except Exception:
            return False

    def _check_llm_provider(self) -> bool:
        provider_name = self.settings.llm_provider.lower()
        if provider_name not in ALLOWED_PROVIDERS:
            return False

        if provider_name == "ollama":
            return bool(self.settings.ollama_model)

        if provider_name == "openai":
            return bool(self.settings.openai_api_key and self.settings.openai_model)
        if provider_name == "anthropic":
            return bool(self.settings.anthropic_api_key and self.settings.anthropic_model)
        if provider_name == "openrouter":
            return bool(self.settings.openrouter_api_key and self.settings.openrouter_model)
        if provider_name == "gemini":
            return bool(self.settings.gemini_api_key and self.settings.gemini_model)
        if provider_name == "bedrock":
            region = (
                self.settings.bedrock_region.strip()
                or self.settings.aws_default_region.strip()
            )
            return bool(self.settings.bedrock_model.strip() and region)

        try:
            LLMProviderFactory.create(settings=self.settings)
            return True
        except Exception:
            return False
