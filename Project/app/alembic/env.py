import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

""'make sure project root (where app package is) is on sys.path"""
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

"""this is the Alembic Config object, which provides"""
 """access to the values within the .ini file in use."""
config = context.config

""" Interpret the config file for Python logging.""""
fileConfig(config.config_file_name)

""" Import the Flask app to get SQLALCHEMY_DATABASE_URI and metadata"""
from app import create_app
from app.extensions import db

app, _ = create_app()  
"""override sqlalchemy.url in alembic config"""
config.set_main_option("sqlalchemy.url", app.config["SQLALCHEMY_DATABASE_URI"])

target_metadata = db.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
