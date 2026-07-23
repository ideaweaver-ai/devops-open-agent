"""Text embedding client for RAG.

Reuses the platform's allowed providers (openai, gemini, ollama) to turn
investigation text into vectors. Anthropic and OpenRouter do not offer a
first-party embeddings API, so they fall back to a configured provider.
"""

from __future__ import annotations

import httpx
from loguru import logger

from app.ai.usage import UsageTracker
from app.core.config import Settings, get_settings

_EMBEDDING_PROVIDERS = {"openai", "gemini", "ollama"}

_DEFAULT_MODELS = {
    "openai": "text-embedding-3-small",
    "gemini": "text-embedding-004",
    "ollama": "nomic-embed-text",
}


class EmbeddingError(Exception):
    """Raised when text embedding fails."""


def resolve_embedding_provider(settings: Settings) -> str:
    provider = (settings.rag_embedding_provider or "").strip().lower()
    if provider in _EMBEDDING_PROVIDERS:
        return provider

    llm_provider = (settings.llm_provider or "").strip().lower()
    if llm_provider in _EMBEDDING_PROVIDERS:
        return llm_provider
    if settings.openai_api_key.strip():
        return "openai"
    if settings.gemini_api_key.strip():
        return "gemini"
    return "ollama"


def resolve_embedding_model(settings: Settings, provider: str) -> str:
    override = (settings.rag_embedding_model or "").strip()
    if override:
        return override
    return _DEFAULT_MODELS.get(provider, _DEFAULT_MODELS["openai"])


class EmbeddingClient:
    """Generate embeddings using the configured provider."""

    def __init__(self, settings: Settings | None = None, timeout: float = 60.0) -> None:
        self.settings = settings or get_settings()
        self.provider = resolve_embedding_provider(self.settings)
        self.model = resolve_embedding_model(self.settings, self.provider)
        self.timeout = timeout

    async def embed(self, text: str) -> list[float]:
        cleaned = (text or "").strip()
        if not cleaned:
            raise EmbeddingError("Cannot embed empty text")

        if self.provider == "openai":
            return await self._embed_openai(cleaned)
        if self.provider == "gemini":
            return await self._embed_gemini(cleaned)
        if self.provider == "ollama":
            return await self._embed_ollama(cleaned)
        raise EmbeddingError(f"Unsupported embedding provider: {self.provider}")

    async def _embed_openai(self, text: str) -> list[float]:
        api_key = self.settings.openai_api_key.strip()
        if not api_key:
            raise EmbeddingError("OPENAI_API_KEY is required for OpenAI embeddings")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"model": self.model, "input": text},
                )
        except httpx.HTTPError as exc:
            raise EmbeddingError(f"OpenAI embeddings request failed: {exc}") from exc
        if response.status_code >= 400:
            raise EmbeddingError(
                f"OpenAI embeddings error ({response.status_code}): {response.text[:200]}"
            )
        try:
            payload = response.json()
            usage = payload.get("usage") or {}
            total = int(usage.get("total_tokens") or usage.get("prompt_tokens") or 0)
            if total <= 0:
                total = max(1, len(text) // 4)
            UsageTracker.record(
                provider="openai",
                model=self.model,
                input_tokens=total,
                output_tokens=0,
                total_tokens=total,
                call_kind="embedding",
            )
            return payload["data"][0]["embedding"]
        except (KeyError, IndexError, TypeError) as exc:
            raise EmbeddingError("OpenAI returned a malformed embeddings response") from exc

    async def _embed_gemini(self, text: str) -> list[float]:
        api_key = self.settings.gemini_api_key.strip()
        if not api_key:
            raise EmbeddingError("GEMINI_API_KEY is required for Gemini embeddings")
        model = self.model if self.model.startswith("models/") else f"models/{self.model}"
        url = f"https://generativelanguage.googleapis.com/v1beta/{model}:embedContent"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers={"x-goog-api-key": api_key},
                    json={"model": model, "content": {"parts": [{"text": text}]}},
                )
        except httpx.HTTPError as exc:
            raise EmbeddingError(f"Gemini embeddings request failed: {exc}") from exc
        if response.status_code >= 400:
            raise EmbeddingError(
                f"Gemini embeddings error ({response.status_code}): {response.text[:200]}"
            )
        try:
            payload = response.json()
            # Gemini embedContent often omits usage; estimate from input length.
            estimated = max(1, len(text) // 4)
            UsageTracker.record(
                provider="gemini",
                model=self.model,
                input_tokens=estimated,
                output_tokens=0,
                total_tokens=estimated,
                call_kind="embedding",
            )
            return payload["embedding"]["values"]
        except (KeyError, TypeError) as exc:
            raise EmbeddingError("Gemini returned a malformed embeddings response") from exc

    async def _embed_ollama(self, text: str) -> list[float]:
        base_url = self.settings.ollama_base_url.rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                )
        except httpx.HTTPError as exc:
            raise EmbeddingError(f"Ollama embeddings request failed: {exc}") from exc
        if response.status_code >= 400:
            raise EmbeddingError(
                f"Ollama embeddings error ({response.status_code}): {response.text[:200]}"
            )
        try:
            payload = response.json()
            embedding = payload["embedding"]
        except (KeyError, TypeError) as exc:
            raise EmbeddingError("Ollama returned a malformed embeddings response") from exc
        if not embedding:
            raise EmbeddingError(
                f"Ollama model '{self.model}' returned an empty embedding. "
                "Pull an embedding model (e.g. `ollama pull nomic-embed-text`)."
            )
        estimated = int(payload.get("prompt_eval_count") or max(1, len(text) // 4))
        UsageTracker.record(
            provider="ollama",
            model=self.model,
            input_tokens=estimated,
            output_tokens=0,
            total_tokens=estimated,
            call_kind="embedding",
        )
        return embedding
