"""Test fixtures: an isolated test database + an ASGI client + a mail outbox.

Auth flows commit inside their unit of work, so per-test isolation is done by
truncating tables (not transaction rollback). The app's `get_session` dependency
is overridden to point at the throwaway `drumgen_test` database.
"""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from drumgen.api import app
from drumgen.config import Settings
from drumgen.db.base import SCHEMA, Base
from drumgen.db.engine import get_session

# Importing `app` above pulls in the routers → ORM models, registering every
# table on Base.metadata before create_all runs below.

_DEV_URL = "postgresql+asyncpg://drumgen:drumgen@localhost:55432/drumgen"
_TEST_DB = "drumgen_test"
_TEST_URL = f"postgresql+asyncpg://drumgen:drumgen@localhost:55432/{_TEST_DB}"


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    admin = create_async_engine(_DEV_URL, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        found = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": _TEST_DB}
        )
        if not found:
            await conn.execute(text(f'CREATE DATABASE "{_TEST_DB}"'))
    await admin.dispose()

    engine = create_async_engine(
        _TEST_URL, connect_args={"server_settings": {"search_path": SCHEMA}}
    )
    async with engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
        await conn.run_sync(Base.metadata.create_all)
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f'TRUNCATE TABLE {SCHEMA}."{table.name}" CASCADE'))

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, str]]:
    """Capture outbound emails instead of sending them; returns the message list."""
    box: list[dict[str, str]] = []

    async def fake_send(
        _settings: Settings, *, to: str, subject: str, text: str, html: str | None = None
    ) -> None:
        box.append({"to": to, "subject": subject, "text": text})

    from drumgen.mailer import client as mail_client

    monkeypatch.setattr(mail_client, "send_email", fake_send)
    return box
