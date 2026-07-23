"""Google Gemini LLM provider."""

from __future__ import annotations

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


class GeminiProvider(BaseLLMProvider):
    """Google Generative Language API provider."""

    API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(
        self,
        api_key: str = "",
        model: str = "gemini-2.0-flash",
        timeout: float = 120.0,
    ) -> None:
        self.api_key = api_key
        self.model = model or "gemini-2.0-flash"
        self.timeout = timeout

    async def generate(self, messages: list[dict], temperature: float = 0.1) -> str:
        if not self.api_key:
            raise LLMAuthenticationError("GEMINI_API_KEY is not configured")

        system_instruction, contents = self._convert_messages(messages)
        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }
        if system_instruction is not None:
            payload["systemInstruction"] = system_instruction

        url = f"{self.API_BASE}/{self.model}:generateContent"
        logger.info("Calling Gemini provider | model={}", self.model)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": self.api_key,
                    },
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("Gemini request timed out") from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Gemini request failed: {exc}") from exc

        if response.status_code in {401, 403}:
            raise LLMAuthenticationError("Gemini authentication failed")
        if response.status_code == 429:
            raise LLMRateLimitError("Gemini rate limit exceeded")
        if response.status_code >= 400:
            raise LLMProviderError(
                f"Gemini API error ({response.status_code}): {response.text}"
            )

        data = response.json()
        usage = data.get("usageMetadata") or {}
        UsageTracker.record(
            provider="gemini",
            model=self.model,
            input_tokens=int(usage.get("promptTokenCount") or 0),
            output_tokens=int(usage.get("candidatesTokenCount") or 0),
            total_tokens=int(usage.get("totalTokenCount") or 0),
        )
        try:
            parts = data["candidates"][0]["content"]["parts"]
            text_parts = [part.get("text", "") for part in parts if part.get("text")]
            if not text_parts:
                raise KeyError("empty parts")
            return "".join(text_parts)
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMMalformedResponseError("Gemini returned a malformed response") from exc

    @staticmethod
    def _convert_messages(messages: list[dict]) -> tuple[dict | None, list[dict]]:
        system_instruction: dict | None = None
        contents: list[dict] = []

        for message in messages:
            role = message.get("role", "user")
            text = message.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": text}]}
                continue
            gemini_role = "model" if role == "assistant" else "user"
            contents.append({"role": gemini_role, "parts": [{"text": text}]})

        if not contents:
            contents = [{"role": "user", "parts": [{"text": ""}]}]

        return system_instruction, contents
