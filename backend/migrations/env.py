"""Alembic environment — async, confined to the `drumgen` schema.

The shared Postgres holds several apps as sibling schemas, so migrations must
never look outside `drumgen`: `include_name` restricts reflection to it and the
version table lives inside it too.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, text
from sqlalchemy.ext.asyncio import create_async_engine

from drumgen.config import get_settings
from drumgen.db import models as _models  # noqa: F401  (register tables on metadata)
from drumgen.db.base import SCHEMA, Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_name(name: str | None, type_: str, _parent_names: object) -> bool:
    # Restrict *schema reflection* to the default anchor + drumgen, so we never
    # try to read another app's schema (the drumgen role has no rights there on
    # the shared prod instance).
    if type_ == "schema":
        return name in (None, SCHEMA)
    return True


def include_object(
    obj: object, _name: str | None, type_: str, _reflected: bool, _compare_to: object
) -> bool:
    # Restrict *DDL* to the drumgen schema, so autogenerate never emits changes
    # against tables that belong to other apps sharing the database.
    if type_ == "table":
        return getattr(obj, "schema", None) == SCHEMA
    # Postgres omits the referred schema for same-schema FKs on reflection, so a
    # reflected FK (`users.id`) never matches the metadata's qualified
    # `drumgen.users.id` — a purely cosmetic diff. Skip standalone FK comparison
    # (FKs are still emitted inside create_table); write any real FK change by hand.
    return type_ != "foreign_key_constraint"


def _configure(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=SCHEMA,
        include_schemas=True,
        include_name=include_name,
        include_object=include_object,
        compare_type=True,
    )


def do_run_migrations(connection: Connection) -> None:
    # Only CREATE the schema if it's actually missing. On the shared prod
    # instance the schema pre-exists and the drumgen role lacks CREATE on the
    # database, so an unconditional `CREATE SCHEMA IF NOT EXISTS` would still
    # raise "permission denied" — the existence check avoids reaching CREATE.
    exists = connection.execute(
        text("SELECT 1 FROM information_schema.schemata WHERE schema_name = :s"),
        {"s": SCHEMA},
    ).scalar()
    if not exists:
        connection.execute(text(f"CREATE SCHEMA {SCHEMA}"))
    _configure(connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    # Use a dedicated engine WITHOUT the app's `search_path=drumgen` setting: the
    # metadata is already schema-qualified, and a forced search_path makes
    # reflection report existing tables under the default schema, which breaks
    # autogenerate (it would see every table as missing).
    migration_engine = create_async_engine(get_settings().database_url)
    async with migration_engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
        await connection.commit()
    await migration_engine.dispose()


def run_migrations_offline() -> None:
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        version_table_schema=SCHEMA,
        include_schemas=True,
        include_name=include_name,
        include_object=include_object,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
