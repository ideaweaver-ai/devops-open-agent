"""OpenAI LLM provider."""

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


class OpenAIProvider(BaseLLMProvider):
    """OpenAI chat completions provider."""

    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(
        self,
        api_key: str = "",
        model: str = "gpt-4o-mini",
        timeout: float = 120.0,
    ) -> None:
        self.api_key = api_key
        self.model = model or "gpt-4o-mini"
        self.timeout = timeout

    async def generate(self, messages: list[dict], temperature: float = 0.1) -> str:
        if not self.api_key:
            raise LLMAuthenticationError("OPENAI_API_KEY is not configured")

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        logger.info("Calling OpenAI provider | model={}", self.model)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("OpenAI request timed out") from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"OpenAI request failed: {exc}") from exc

        if response.status_code == 401:
            raise LLMAuthenticationError("OpenAI authentication failed")
        if response.status_code == 429:
            raise LLMRateLimitError("OpenAI rate limit exceeded")
        if response.status_code >= 400:
            raise LLMProviderError(f"OpenAI API error ({response.status_code}): {response.text}")

        data = response.json()
        usage = data.get("usage") or {}
        UsageTracker.record(
            provider="openai",
            model=self.model,
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
            total_tokens=int(usage.get("total_tokens") or 0),
        )
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMMalformedResponseError("OpenAI returned a malformed response") from exc
