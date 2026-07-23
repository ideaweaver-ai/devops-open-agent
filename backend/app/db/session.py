"""Async SQLAlchemy session for PostgreSQL."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_async_engine(
    settings.postgres_url,
    echo=False,
    pool_pre_ping=True,
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_auth_db() -> None:
    from sqlalchemy import text

    from app.db import models  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
        )
        await connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS llm_daily_budget_usd DOUBLE PRECISION
                """
            )
        )
        await connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS llm_budget_alert_date VARCHAR(16)
                """
            )
        )
        await connection.execute(
            text(
                """
                ALTER TABLE user_pagerduty_integrations
                ADD COLUMN IF NOT EXISTS notification_cooldown_minutes INTEGER NOT NULL DEFAULT 60
                """
            )
        )
        for tbl in (
            "user_slack_integrations",
            "user_pagerduty_integrations",
            "user_teams_integrations",
        ):
            for col in ("notify_performance", "notify_security"):
                await connection.execute(
                    text(
                        f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS {col} BOOLEAN NOT NULL DEFAULT TRUE"
                    )
                )
        for tbl in ("user_mcp_integrations", "user_qdrant_integrations"):
            for col in ("use_performance", "use_security"):
                await connection.execute(
                    text(
                        f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS {col} BOOLEAN NOT NULL DEFAULT TRUE"
                    )
                )


async def check_auth_db() -> bool:
    try:
        from sqlalchemy import text

        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
