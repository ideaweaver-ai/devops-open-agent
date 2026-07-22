from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "development"
    service_name: str = "devops-open-agent"
    version: str = "0.1.0"

    llm_provider: str = "openai"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-latest"

    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"

    gemini_api_key: str = ""

    # AWS Bedrock (uses default AWS credential chain / AWS_PROFILE)
    bedrock_model: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    bedrock_region: str = ""
    bedrock_aws_profile: str = ""

    gemini_model: str = "gemini-2.0-flash"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    llm_timeout: int = 120

    # LLM-as-a-Judge (optional separate model for diagnosis verification)
    judge_llm_provider: str = Field(
        default="",
        description="LLM provider for the judge. Falls back to llm_provider when empty.",
    )
    judge_openai_model: str = ""
    judge_anthropic_model: str = ""
    judge_openrouter_model: str = ""
    judge_gemini_model: str = ""
    judge_bedrock_model: str = ""
    judge_ollama_model: str = ""

    kubeconfig_path: str = ""

    kube_api_host_rewrite: str = ""

    aws_profile: str = ""
    aws_default_region: str = "us-east-1"

    # Observability evidence (optional instance-level defaults)
    prometheus_instance_url: str = Field(
        default="",
        description="Instance-level Prometheus endpoint used as a fallback for all users.",
    )
    prometheus_instance_bearer_token: str = ""
    prometheus_instance_basic_auth_user: str = ""
    prometheus_instance_basic_auth_password: str = ""
    grafana_instance_url: str = Field(
        default="",
        description="Instance-level Grafana endpoint used as a fallback for all users.",
    )
    grafana_instance_api_token: str = ""


    log_level: str = "INFO"

    multi_cluster_enabled: bool = True
    topology_graph_enabled: bool = False
    memory_enabled: bool = False

    cors_origins_raw: str = Field(default="", validation_alias="CORS_ORIGINS")

    database_path: str = "data/investigations.db"

    postgres_url: str = "postgresql+asyncpg://kda:kda@localhost:5432/kda"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    seed_default_admin: bool = True
    default_admin_email: str = "admin"
    default_admin_password: str = ""

    github_token: str = ""
    github_webhook_secret: str = ""
    github_api_base_url: str = "https://api.github.com"
    github_app_id: str = ""
    github_private_key: str = ""
    github_installation_id: str = ""

    # Slack notifications (optional instance-level defaults)
    slack_bot_token: str = ""
    slack_instance_webhook_url: str = ""
    slack_notification_cooldown_minutes: int = Field(
        default=60,
        description="Minimum minutes between Slack alerts per user (reduces alert fatigue)",
    )

    # PagerDuty notifications (optional instance-level defaults)
    pagerduty_instance_routing_key: str = ""
    pagerduty_notification_cooldown_minutes: int = Field(
        default=60,
        description="Minimum minutes between PagerDuty alerts per user (reduces alert fatigue)",
    )

    # Microsoft Teams notifications (optional instance-level defaults)
    teams_instance_webhook_url: str = ""
    teams_notification_cooldown_minutes: int = Field(
        default=60,
        description="Minimum minutes between Teams alerts per user (reduces alert fatigue)",
    )

    # Qdrant vector database / RAG (optional instance-level defaults)
    qdrant_instance_url: str = Field(
        default="",
        description="Instance-level Qdrant endpoint used as a fallback for all users.",
    )
    qdrant_instance_api_key: str = ""
    qdrant_collection: str = Field(
        default="devops_open_agent_investigations",
        description="Qdrant collection where investigation vectors are stored.",
    )
    rag_embedding_provider: str = Field(
        default="",
        description=(
            "Embedding provider for RAG: openai, gemini, or ollama. "
            "Defaults to the configured LLM provider when it supports embeddings."
        ),
    )
    rag_embedding_model: str = Field(
        default="",
        description="Embedding model override. Defaults to a sensible model per provider.",
    )
    rag_max_results: int = Field(
        default=4,
        description="Maximum number of past investigations retrieved for RAG context.",
    )

    # MCP integrations (optional instance-level defaults)
    mcp_instance_server_url: str = ""
    mcp_instance_api_key: str = ""
    mcp_allowed_server_urls: str = Field(
        default="",
        description=(
            "Comma-separated MCP server URLs or host patterns allowed for all users. "
            "When set, only matching URLs can be saved or connected."
        ),
    )

    public_app_url: str = Field(
        default="http://localhost:3000",
        description="Public frontend URL for links in notification messages",
    )

    @property
    def cors_origins(self) -> list[str]:
        if not self.cors_origins_raw.strip():
            return list(_DEFAULT_CORS_ORIGINS)
        parsed = [
            item.strip()
            for item in self.cors_origins_raw.split(",")
            if item.strip()
        ]
        return parsed or list(_DEFAULT_CORS_ORIGINS)


@lru_cache
def get_settings() -> Settings:
    return Settings()
