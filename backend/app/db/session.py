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
                ALTER TABLE user_pagerduty_integrations
                ADD COLUMN IF NOT EXISTS notification_cooldown_minutes INTEGER NOT NULL DEFAULT 60
                """
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
