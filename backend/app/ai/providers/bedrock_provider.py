"""AWS Bedrock LLM provider (Converse API)."""

from __future__ import annotations

import asyncio
from typing import Any

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError
from loguru import logger

from app.ai.providers.base import BaseLLMProvider
from app.ai.providers.exceptions import (
    LLMAuthenticationError,
    LLMMalformedResponseError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)


class BedrockProvider(BaseLLMProvider):
    """Invoke Bedrock foundation / inference-profile models via Converse."""

    def __init__(
        self,
        model: str = "anthropic.claude-3-5-sonnet-20241022-v2:0",
        region: str = "us-west-2",
        aws_profile: str = "",
        timeout: float = 120.0,
        max_tokens: int = 8192,
    ) -> None:
        self.model = (model or "").strip()
        self.region = (region or "us-west-2").strip()
        self.aws_profile = (aws_profile or "").strip()
        self.timeout = timeout
        self.max_tokens = max_tokens

    def _client(self):
        session_kwargs: dict[str, Any] = {}
        if self.aws_profile:
            session_kwargs["profile_name"] = self.aws_profile
        session = boto3.Session(**session_kwargs)
        return session.client(
            "bedrock-runtime",
            region_name=self.region,
            config=BotoConfig(
                read_timeout=int(self.timeout),
                connect_timeout=min(20, int(self.timeout)),
                retries={"max_attempts": 2, "mode": "standard"},
            ),
        )

    async def generate(self, messages: list[dict], temperature: float = 0.1) -> str:
        if not self.model:
            raise LLMProviderError("BEDROCK_MODEL is not configured")
        if not self.region:
            raise LLMProviderError("BEDROCK_REGION / AWS_DEFAULT_REGION is not configured")

        system_parts: list[str] = []
        converse_messages: list[dict[str, Any]] = []
        for message in messages:
            role = message.get("role", "user")
            content = str(message.get("content") or "")
            if role == "system":
                if content.strip():
                    system_parts.append(content)
                continue
            if role not in {"user", "assistant"}:
                role = "user"
            converse_messages.append(
                {
                    "role": role,
                    "content": [{"text": content}],
                }
            )

        if not converse_messages:
            raise LLMProviderError("Bedrock request has no user/assistant messages")

        # Converse requires the conversation to start with a user turn.
        if converse_messages[0]["role"] != "user":
            converse_messages.insert(
                0,
                {"role": "user", "content": [{"text": "Continue."}]},
            )

        kwargs: dict[str, Any] = {
            "modelId": self.model,
            "messages": converse_messages,
            "inferenceConfig": {
                "temperature": float(temperature),
                "maxTokens": int(self.max_tokens),
            },
        }
        if system_parts:
            kwargs["system"] = [{"text": "\n\n".join(system_parts)}]

        logger.info(
            "Calling Bedrock provider | model={} region={}",
            self.model,
            self.region,
        )

        try:
            response = await asyncio.to_thread(self._converse, kwargs)
        except ClientError as exc:
            raise self._map_client_error(exc) from exc
        except BotoCoreError as exc:
            message = str(exc)
            if "timeout" in message.lower() or "timed out" in message.lower():
                raise LLMTimeoutError("Bedrock request timed out") from exc
            raise LLMProviderError(f"Bedrock request failed: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise LLMProviderError(f"Bedrock request failed: {exc}") from exc

        return self._extract_text(response)

    def _converse(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        client = self._client()
        return client.converse(**kwargs)

    @staticmethod
    def _extract_text(response: dict[str, Any]) -> str:
        try:
            content = response["output"]["message"]["content"]
            parts = [
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("text")
            ]
            text = "".join(parts).strip()
            if not text:
                raise LLMMalformedResponseError("Bedrock returned empty content")
            return text
        except (KeyError, TypeError) as exc:
            raise LLMMalformedResponseError("Bedrock returned a malformed response") from exc

    @staticmethod
    def _map_client_error(exc: ClientError) -> LLMProviderError:
        error = exc.response.get("Error") or {}
        code = str(error.get("Code") or "")
        message = str(error.get("Message") or exc)
        status = int((exc.response.get("ResponseMetadata") or {}).get("HTTPStatusCode") or 0)

        if code in {
            "UnrecognizedClientException",
            "InvalidSignatureException",
            "AccessDeniedException",
            "UnauthorizedOperation",
        } or status == 401:
            return LLMAuthenticationError(f"Bedrock authentication/authorization failed: {message}")
        if code in {"ThrottlingException", "TooManyRequestsException"} or status == 429:
            return LLMRateLimitError(f"Bedrock rate limit exceeded: {message}")
        if code in {"ModelTimeoutException"} or "timeout" in message.lower():
            return LLMTimeoutError(f"Bedrock request timed out: {message}")
        return LLMProviderError(f"Bedrock API error ({code or status}): {message}")
