"""Alembic environment — async, confined to the `drumgen` schema.

The shared Postgres holds several apps as sibling schemas, so migrations must
never look outside `drumgen`: `include_name` restricts reflection to it and the
version table lives inside it too.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, text

from drumgen.config import get_settings
from drumgen.db import models as _models  # noqa: F401  (register tables on metadata)
from drumgen.db.base import SCHEMA, Base
from drumgen.db.engine import engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_name(name: str | None, type_: str, _parent_names: object) -> bool:
    if type_ == "schema":
        return name == SCHEMA
    return True


def _configure(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=SCHEMA,
        include_schemas=True,
        include_name=include_name,
        compare_type=True,
    )


def do_run_migrations(connection: Connection) -> None:
    connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
    _configure(connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
        await connection.commit()
    await engine.dispose()


def run_migrations_offline() -> None:
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        version_table_schema=SCHEMA,
        include_schemas=True,
        include_name=include_name,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
