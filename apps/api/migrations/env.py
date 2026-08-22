"""Alembic migration environment for Burnt Jacket.

This wires Alembic to the application's own configuration and metadata:

* the database URL comes from ``app.core.config.settings`` (i.e. the
  ``DATABASE_URL`` environment variable), so nothing is hardcoded and every
  environment — local, CI, Railway — runs the same code path;
* ``target_metadata`` is the app's declarative ``Base.metadata`` with every
  model imported, so ``alembic revision --autogenerate`` can diff the models
  against the live database.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import the application's settings and metadata. ``prepend_sys_path = .`` in
# alembic.ini puts the API package root on sys.path, so these resolve when
# Alembic is invoked from apps/api/.
from app.core.config import settings
from app.db.base import Base
import app.models.core  # noqa: F401  (registers every table on Base.metadata)

# Alembic Config object, provides access to values in alembic.ini.
config = context.config

# Inject the runtime database URL. ``sqlalchemy_database_url`` normalizes the
# provider-supplied URL to the psycopg driver form.
config.set_main_option("sqlalchemy.url", settings.sqlalchemy_database_url)

# Configure Python logging from alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout, no DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (against a live DB connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
