"""Qdrant vector database (RAG) integration request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class QdrantIntegrationSettings(BaseModel):
    enabled: bool = False
    url: str = Field(
        default="",
        description="Qdrant endpoint, e.g. http://qdrant:6333 or https://<cluster>.qdrant.io",
    )
    api_key: str | None = Field(
        default=None,
        description="Set to update the Qdrant API key; omit or null to keep existing value.",
    )
    collection: str | None = Field(
        default=None,
        description="Optional collection name override. Defaults to the instance collection.",
    )
    use_kubernetes: bool = True
    use_aws: bool = True
    use_cloud_cost: bool = True
    use_performance: bool = True
    use_security: bool = True


class QdrantIntegrationResponse(BaseModel):
    enabled: bool
    url: str
    api_key_configured: bool
    api_key_preview: str | None = None
    collection: str
    use_kubernetes: bool
    use_aws: bool
    use_cloud_cost: bool
    use_performance: bool
    use_security: bool
    instance_url_configured: bool
    embedding_provider: str
    embedding_model: str


class QdrantTestResponse(BaseModel):
    status: str
    message: str
    collection: str
    vector_count: int | None = None
    embedding_provider: str | None = None
    embedding_dimension: int | None = None
