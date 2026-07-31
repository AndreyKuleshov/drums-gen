"""Async engine + session factory.

The connection pins `search_path` to the `drumgen` schema so unqualified table
names resolve there, matching the shared-instance convention.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from drumgen.config import get_settings
from drumgen.db.base import SCHEMA

_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    connect_args={"server_settings": {"search_path": SCHEMA}},
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped async session."""
    async with SessionLocal() as session:
        yield session
