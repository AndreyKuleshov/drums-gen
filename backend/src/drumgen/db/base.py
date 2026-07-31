"""Declarative base pinned to the `drumgen` Postgres schema.

Every app on the shared instance lives in its own schema; setting the schema on
the MetaData keeps all drum-gen tables (and Alembic's version table) inside
`drumgen` and never touches a neighbour's schema.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

SCHEMA = "drumgen"


class Base(DeclarativeBase):
    metadata = MetaData(schema=SCHEMA)
