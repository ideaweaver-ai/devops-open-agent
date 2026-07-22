"""LLM provider factory."""

from app.ai.providers.anthropic_provider import AnthropicProvider
from app.ai.providers.base import BaseLLMProvider
from app.ai.providers.bedrock_provider import BedrockProvider
from app.ai.providers.gemini_provider import GeminiProvider
from app.ai.providers.ollama_provider import OllamaProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.providers.openrouter_provider import OpenRouterProvider
from app.core.config import Settings, get_settings

ALLOWED_PROVIDERS = {"openai", "anthropic", "ollama", "openrouter", "gemini", "bedrock"}


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""

    _PROVIDERS: dict[str, type[BaseLLMProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "ollama": OllamaProvider,
        "openrouter": OpenRouterProvider,
        "gemini": GeminiProvider,
        "bedrock": BedrockProvider,
    }

    @classmethod
    def create(
        cls,
        provider_name: str | None = None,
        settings: Settings | None = None,
    ) -> BaseLLMProvider:
        settings = settings or get_settings()
        name = (provider_name or settings.llm_provider).lower()

        if name not in ALLOWED_PROVIDERS:
            allowed = ", ".join(sorted(ALLOWED_PROVIDERS))
            raise ValueError(
                f"Unsupported LLM provider '{name}'. Allowed values: {allowed}"
            )

        provider_cls = cls._PROVIDERS[name]
        timeout = float(settings.llm_timeout)

        if name == "openai":
            return provider_cls(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
                timeout=timeout,
            )
        if name == "anthropic":
            return provider_cls(
                api_key=settings.anthropic_api_key,
                model=settings.anthropic_model,
                timeout=timeout,
            )
        if name == "ollama":
            return provider_cls(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                timeout=timeout,
            )
        if name == "openrouter":
            return provider_cls(
                api_key=settings.openrouter_api_key,
                model=settings.openrouter_model,
                timeout=timeout,
            )
        if name == "gemini":
            return provider_cls(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
                timeout=timeout,
            )
        if name == "bedrock":
            region = (
                settings.bedrock_region.strip()
                or settings.aws_default_region.strip()
                or "us-west-2"
            )
            profile = settings.bedrock_aws_profile.strip() or settings.aws_profile.strip()
            return provider_cls(
                model=settings.bedrock_model,
                region=region,
                aws_profile=profile,
                timeout=timeout,
            )

        raise ValueError(f"Unsupported LLM provider: {name}")


# Backward-compatible alias
LLMFactory = LLMProviderFactory
