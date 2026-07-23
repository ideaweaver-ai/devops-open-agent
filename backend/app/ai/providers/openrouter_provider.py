"""OpenRouter LLM provider."""

import httpx
from loguru import logger

from app.ai.providers.base import BaseLLMProvider
from app.ai.providers.exceptions import (
    LLMAuthenticationError,
    LLMMalformedResponseError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.ai.usage import UsageTracker


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter chat completions provider."""

    API_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        api_key: str = "",
        model: str = "openai/gpt-4o-mini",
        timeout: float = 120.0,
    ) -> None:
        self.api_key = api_key
        self.model = model or "openai/gpt-4o-mini"
        self.timeout = timeout

    async def generate(self, messages: list[dict], temperature: float = 0.1) -> str:
        if not self.api_key:
            raise LLMAuthenticationError("OPENROUTER_API_KEY is not configured")

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        logger.info("Calling OpenRouter provider | model={}", self.model)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/kubernetes-debugging-agent",
                        "X-Title": "Kubernetes Debugging Agent",
                    },
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("OpenRouter request timed out") from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"OpenRouter request failed: {exc}") from exc

        if response.status_code == 401:
            raise LLMAuthenticationError("OpenRouter authentication failed")
        if response.status_code == 429:
            raise LLMRateLimitError("OpenRouter rate limit exceeded")
        if response.status_code >= 400:
            raise LLMProviderError(
                f"OpenRouter API error ({response.status_code}): {response.text}"
            )

        data = response.json()
        usage = data.get("usage") or {}
        estimated = None
        if usage.get("cost") is not None:
            try:
                estimated = float(usage.get("cost"))
            except (TypeError, ValueError):
                estimated = None
        UsageTracker.record(
            provider="openrouter",
            model=self.model,
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
            total_tokens=int(usage.get("total_tokens") or 0),
            estimated_usd=estimated,
        )
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMMalformedResponseError("OpenRouter returned a malformed response") from exc
