"""Ollama LLM provider."""

import httpx
from loguru import logger

from app.ai.providers.base import BaseLLMProvider
from app.ai.providers.exceptions import (
    LLMMalformedResponseError,
    LLMProviderError,
    LLMTimeoutError,
)
from app.ai.usage import UsageTracker


class OllamaProvider(BaseLLMProvider):
    """Local Ollama chat API provider."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1",
        timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model or "llama3.1"
        self.timeout = timeout

    async def generate(self, messages: list[dict], temperature: float = 0.1) -> str:
        if not self.model:
            raise LLMProviderError("OLLAMA_MODEL is not configured")

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature},
        }

        logger.info("Calling Ollama provider | model={} base_url={}", self.model, self.base_url)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("Ollama request timed out") from exc
        except httpx.ConnectError as exc:
            raise LLMProviderError(
                f"Unable to connect to Ollama at {self.base_url}. Is Ollama running?"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Ollama request failed: {exc}") from exc

        if response.status_code >= 400:
            raise LLMProviderError(f"Ollama API error ({response.status_code}): {response.text}")

        data = response.json()
        UsageTracker.record(
            provider="ollama",
            model=self.model,
            input_tokens=int(data.get("prompt_eval_count") or 0),
            output_tokens=int(data.get("eval_count") or 0),
        )
        try:
            return data["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise LLMMalformedResponseError("Ollama returned a malformed response") from exc
