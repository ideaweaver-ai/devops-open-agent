"""Helpers for listing AWS Bedrock text models."""

from __future__ import annotations

import asyncio
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from loguru import logger


async def list_bedrock_text_models(
    *,
    region: str,
    aws_profile: str = "",
) -> list[dict[str, Any]]:
    """Return Bedrock foundation models that support TEXT output."""

    def _list() -> list[dict[str, Any]]:
        session_kwargs: dict[str, Any] = {}
        if aws_profile.strip():
            session_kwargs["profile_name"] = aws_profile.strip()
        session = boto3.Session(**session_kwargs)
        client = session.client("bedrock", region_name=region)
        response = client.list_foundation_models(byOutputModality="TEXT")
        summaries = response.get("modelSummaries") or []
        models: list[dict[str, Any]] = []
        for item in summaries:
            model_id = item.get("modelId")
            if not model_id:
                continue
            models.append(
                {
                    "model_id": model_id,
                    "model_name": item.get("modelName"),
                    "provider_name": item.get("providerName"),
                    "input_modalities": item.get("inputModalities") or [],
                    "output_modalities": item.get("outputModalities") or [],
                    "inference_types": item.get("inferenceTypesSupported") or [],
                    "response_streaming": bool(item.get("responseStreamingSupported")),
                }
            )
        models.sort(key=lambda row: str(row.get("model_id") or ""))
        return models

    try:
        return await asyncio.to_thread(_list)
    except (ClientError, BotoCoreError) as exc:
        logger.warning("Failed to list Bedrock models | region={} error={}", region, exc)
        raise
