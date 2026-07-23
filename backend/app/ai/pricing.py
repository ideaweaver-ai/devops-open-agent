"""Estimate USD cost from provider token usage."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_settings

BUNDLED_PRICING_PATH = Path(__file__).with_name("pricing_table.json")


def bundled_pricing_path() -> Path:
    return BUNDLED_PRICING_PATH


def runtime_pricing_path() -> Path:
    settings = get_settings()
    db_path = Path(settings.database_path)
    return db_path.parent / "pricing_table.json"


def ensure_runtime_pricing_file() -> Path:
    """Seed data/pricing_table.json from the bundled default when missing."""
    runtime = runtime_pricing_path()
    runtime.parent.mkdir(parents=True, exist_ok=True)
    if not runtime.exists():
        bundled = bundled_pricing_path()
        if bundled.exists():
            runtime.write_text(bundled.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            runtime.write_text("{}", encoding="utf-8")
    return runtime


@lru_cache(maxsize=1)
def _load_pricing_table() -> dict[str, Any]:
    path = ensure_runtime_pricing_file()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def clear_pricing_cache() -> None:
    _load_pricing_table.cache_clear()


def get_pricing_table() -> dict[str, Any]:
    return dict(_load_pricing_table())


def validate_pricing_table(table: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(table, dict):
        raise ValueError("Pricing table must be a JSON object keyed by provider.")
    cleaned: dict[str, Any] = {}
    for provider, models in table.items():
        if not isinstance(provider, str) or not provider.strip():
            raise ValueError("Provider keys must be non-empty strings.")
        if not isinstance(models, dict):
            raise ValueError(f"Provider '{provider}' must map to an object of models.")
        provider_models: dict[str, Any] = {}
        for model, rates in models.items():
            if not isinstance(model, str) or not model.strip():
                raise ValueError(f"Model keys under '{provider}' must be non-empty strings.")
            if not isinstance(rates, dict):
                raise ValueError(f"Rates for '{provider}/{model}' must be an object.")
            try:
                input_rate = float(rates.get("input_per_1m_usd") or 0.0)
                output_rate = float(rates.get("output_per_1m_usd") or 0.0)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Rates for '{provider}/{model}' must include numeric "
                    "input_per_1m_usd and output_per_1m_usd."
                ) from exc
            if input_rate < 0 or output_rate < 0:
                raise ValueError(f"Rates for '{provider}/{model}' cannot be negative.")
            provider_models[model.strip()] = {
                "input_per_1m_usd": input_rate,
                "output_per_1m_usd": output_rate,
            }
        cleaned[provider.strip().lower()] = provider_models
    return cleaned


def save_pricing_table(table: dict[str, Any]) -> dict[str, Any]:
    cleaned = validate_pricing_table(table)
    path = ensure_runtime_pricing_file()
    path.write_text(json.dumps(cleaned, indent=2) + "\n", encoding="utf-8")
    clear_pricing_cache()
    return cleaned


def reset_pricing_table() -> dict[str, Any]:
    bundled = bundled_pricing_path()
    try:
        payload = json.loads(bundled.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    return save_pricing_table(payload if isinstance(payload, dict) else {})


def normalize_model_id(provider: str, model: str) -> str:
    """Normalize model IDs for pricing lookup (Bedrock inference profiles, etc.)."""
    value = (model or "").strip()
    provider_name = (provider or "").strip().lower()
    if not value:
        return value

    if provider_name == "bedrock":
        # us.anthropic.claude-sonnet-4-6 → anthropic.claude-sonnet-4-6
        if value.startswith("us.") or value.startswith("eu.") or value.startswith("ap."):
            parts = value.split(".", 1)
            if len(parts) == 2:
                value = parts[1]
        # Strip ARN prefixes if present
        if "foundation-model/" in value:
            value = value.rsplit("/", 1)[-1]
        if "inference-profile/" in value:
            value = value.rsplit("/", 1)[-1]
            if value.startswith("us.") or value.startswith("eu.") or value.startswith("ap."):
                parts = value.split(".", 1)
                if len(parts) == 2:
                    value = parts[1]

    if provider_name == "gemini" and value.startswith("models/"):
        value = value.removeprefix("models/")

    return value


def estimate_cost_usd(
    provider: str,
    model: str,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> float | None:
    """Return estimated USD for the call, or None when the model is unknown.

    Ollama is always $0.00 when tokens are present.
    """
    provider_name = (provider or "").strip().lower()
    if provider_name == "ollama":
        return 0.0

    table = _load_pricing_table()
    provider_rates = table.get(provider_name) or {}
    if not isinstance(provider_rates, dict):
        return None

    normalized = normalize_model_id(provider_name, model)
    rates = provider_rates.get(normalized)
    if rates is None:
        # Fuzzy: match by suffix / containment for versioned IDs
        for key, value in provider_rates.items():
            if normalized.endswith(key) or key in normalized or normalized in key:
                rates = value
                break
    if not isinstance(rates, dict):
        return None

    try:
        input_rate = float(rates.get("input_per_1m_usd") or 0.0)
        output_rate = float(rates.get("output_per_1m_usd") or 0.0)
    except (TypeError, ValueError):
        return None

    cost = (max(0, input_tokens) / 1_000_000.0) * input_rate + (
        max(0, output_tokens) / 1_000_000.0
    ) * output_rate
    return round(cost, 8)
