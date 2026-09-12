"""
Async SQLAlchemy database engine and session factory.
Uses asyncpg for PostgreSQL — required for async FastAPI.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


# Async engine — asyncpg driver
engine = create_async_engine(
    settings.database_url,
    echo=(settings.app_env == "development"),
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,      # Verify connections before use
    pool_recycle=3600,       # Recycle connections every hour
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables (used in tests; production uses Alembic)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized")
