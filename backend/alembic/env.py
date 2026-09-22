from logging.config import fileConfig
from pathlib import Path
import os

from alembic import context
from sqlalchemy import engine_from_config, pool
from dotenv import load_dotenv

from app.core.database import Base
from app.core import models  # noqa: F401
from app.analytics import models as analytics_models  # noqa: F401
from app.knowledge_gaps import models as knowledge_gap_models  # noqa: F401



# ------------------------------------------------------------
# Alembic configuration
# ------------------------------------------------------------
config = context.config


# ------------------------------------------------------------
# Load backend/.env
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)


# ------------------------------------------------------------
# Configure Python logging
# ------------------------------------------------------------
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ------------------------------------------------------------
# SQLAlchemy metadata
# ------------------------------------------------------------
target_metadata = Base.metadata


# ------------------------------------------------------------
# Database URL
# ------------------------------------------------------------
database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError(
        f"DATABASE_URL is not set. Expected it in: {ENV_FILE}"
    )


# ------------------------------------------------------------
# Offline migrations
# ------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations without creating a DB connection."""

    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ------------------------------------------------------------
# Online migrations
# ------------------------------------------------------------
def run_migrations_online() -> None:
    """Run migrations against the live database."""

    configuration = config.get_section(
        config.config_ini_section
    ) or {}

    configuration["sqlalchemy.url"] = database_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=False,
        )

        with context.begin_transaction():
            context.run_migrations()


# ------------------------------------------------------------
# Run the appropriate migration mode
# ------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()