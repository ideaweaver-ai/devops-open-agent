"""Anthropic LLM provider."""

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


class AnthropicProvider(BaseLLMProvider):
    """Anthropic messages API provider."""

    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(
        self,
        api_key: str = "",
        model: str = "claude-3-5-sonnet-latest",
        timeout: float = 120.0,
    ) -> None:
        self.api_key = api_key
        self.model = model or "claude-3-5-sonnet-latest"
        self.timeout = timeout

    async def generate(self, messages: list[dict], temperature: float = 0.1) -> str:
        if not self.api_key:
            raise LLMAuthenticationError("ANTHROPIC_API_KEY is not configured")

        system_prompt = ""
        chat_messages: list[dict] = []
        for message in messages:
            if message.get("role") == "system":
                system_prompt = message.get("content", "")
            else:
                chat_messages.append(
                    {"role": message.get("role", "user"), "content": message.get("content", "")}
                )

        payload = {
            "model": self.model,
            "max_tokens": 8192,
            "temperature": temperature,
            "system": system_prompt,
            "messages": chat_messages,
        }

        logger.info("Calling Anthropic provider | model={}", self.model)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.API_URL,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("Anthropic request timed out") from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Anthropic request failed: {exc}") from exc

        if response.status_code == 401:
            raise LLMAuthenticationError("Anthropic authentication failed")
        if response.status_code == 429:
            raise LLMRateLimitError("Anthropic rate limit exceeded")
        if response.status_code >= 400:
            raise LLMProviderError(
                f"Anthropic API error ({response.status_code}): {response.text}"
            )

        data = response.json()
        usage = data.get("usage") or {}
        UsageTracker.record(
            provider="anthropic",
            model=self.model,
            input_tokens=int(usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
        )
        try:
            content_blocks = data["content"]
            text_parts = [
                block.get("text", "")
                for block in content_blocks
                if block.get("type") == "text"
            ]
            return "".join(text_parts)
        except (KeyError, TypeError) as exc:
            raise LLMMalformedResponseError("Anthropic returned a malformed response") from exc
