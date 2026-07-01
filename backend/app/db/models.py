"""SQLAlchemy models for authentication and integrations."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class UserSlackIntegration(Base):
    __tablename__ = "user_slack_integrations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    delivery_method: Mapped[str] = mapped_column(String(32), nullable=False, default="webhook")
    webhook_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    channel: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notify_kubernetes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_aws: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_cloud_cost: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_pr_reviewer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SlackNotificationCooldown(Base):
    __tablename__ = "slack_notification_cooldowns"

    scope_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    last_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserPagerDutyIntegration(Base):
    __tablename__ = "user_pagerduty_integrations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    routing_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notification_cooldown_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )
    notify_kubernetes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_aws: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_cloud_cost: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_pr_reviewer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class PagerDutyNotificationCooldown(Base):
    __tablename__ = "pagerduty_notification_cooldowns"

    scope_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    last_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserTeamsIntegration(Base):
    __tablename__ = "user_teams_integrations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    webhook_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notify_kubernetes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_aws: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_cloud_cost: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_pr_reviewer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TeamsNotificationCooldown(Base):
    __tablename__ = "teams_notification_cooldowns"

    scope_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    last_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserMcpIntegration(Base):
    __tablename__ = "user_mcp_integrations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    server_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    api_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    use_kubernetes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    use_aws: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    use_cloud_cost: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    use_pr_reviewer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class InvestigationSchedule(Base):
    __tablename__ = "investigation_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    agent_type: Mapped[str] = mapped_column(String(32), nullable=False, default="kubernetes")
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    cluster_id: Mapped[str] = mapped_column(String(255), nullable=False)
    namespace: Mapped[str | None] = mapped_column(String(255), nullable=True)
    query: Mapped[str | None] = mapped_column(Text, nullable=True)
    include_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    schedule_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="daily")
    hour: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cron_expression: Mapped[str] = mapped_column(String(64), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_investigation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
