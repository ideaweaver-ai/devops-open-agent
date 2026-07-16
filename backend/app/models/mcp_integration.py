"""MCP integration request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class McpIntegrationSettings(BaseModel):
    enabled: bool = False
    server_url: str = ""
    api_key: str | None = Field(
        default=None,
        description="Set to update API key; omit or null to keep existing value.",
    )
    use_kubernetes: bool = True
    use_aws: bool = True
    use_cloud_cost: bool = True
    use_pr_reviewer: bool = True
    use_performance: bool = True
    use_security: bool = True


class McpWhitelistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    server_url: str = Field(min_length=1, max_length=512)


class McpBlacklistCreate(BaseModel):
    server_url: str = Field(min_length=1, max_length=512)


class McpWhitelistEntry(BaseModel):
    id: str
    name: str
    server_url: str


class McpBlacklistEntry(BaseModel):
    id: str
    server_url: str


class McpOfficialServer(BaseModel):
    id: str
    name: str
    server_url: str
    description: str
    docs_url: str
    auth_hint: str
    category: str


class McpIntegrationResponse(BaseModel):
    enabled: bool
    server_url: str
    api_key_configured: bool
    api_key_preview: str | None = None
    use_kubernetes: bool
    use_aws: bool
    use_cloud_cost: bool
    use_pr_reviewer: bool
    use_performance: bool
    use_security: bool
    instance_server_configured: bool
    instance_url_restrictions_enabled: bool
    instance_allowed_urls: list[str] = Field(default_factory=list)
    official_servers: list[McpOfficialServer] = Field(default_factory=list)
    whitelist: list[McpWhitelistEntry] = Field(default_factory=list)
    blacklist: list[McpBlacklistEntry] = Field(default_factory=list)


class McpTestResponse(BaseModel):
    status: str
    message: str
    tool_count: int = 0
    resource_count: int = 0
    tools: list[str] = Field(default_factory=list)


class McpAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class McpToolCallRecord(BaseModel):
    tool_name: str
    arguments: dict = Field(default_factory=dict)
    result_summary: str = ""


class McpAskResponse(BaseModel):
    answer: str
    tools_used: list[McpToolCallRecord] = Field(default_factory=list)
