from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context
from app.core.config import get_settings
from app.db.base import Base
from app.models import *  # noqa: F403  (import side effect: registers tables)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Deliberately not set_main_option: that writes the URL into a configparser
# section, where a per-cent sign is read as the start of an interpolation and
# a perfectly good password full of them crashes the migration with an error
# that says nothing about passwords. The URL is handed to the engine directly
# instead, which is the only place it was ever going.
DATABASE_URL = get_settings().alembic_url

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
