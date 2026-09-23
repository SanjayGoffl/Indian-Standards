import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def init_db() -> None:
    """
    Create all database tables that do not already exist.

    This is safe to call every time the FastAPI application starts.
    Existing tables are not deleted or recreated.
    """
    # Import models here so SQLAlchemy knows about all registered tables
    # before create_all() is called.
    from app.core import models  # noqa: F401
    from app.analytics import models as analytics_models  # noqa: F401
    from app.knowledge_gaps import models as knowledge_gap_models  # noqa: F401
    

    Base.metadata.create_all(bind=engine)

    # Safe backward-compatible schema migration for newly added columns
    with engine.connect() as conn:
        from sqlalchemy import text
        migrations = [
            "ALTER TABLE indian_standards ADD COLUMN IF NOT EXISTS technical_requirements TEXT;",
            "ALTER TABLE indian_standards ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);",
            "ALTER TABLE indian_standards ADD COLUMN IF NOT EXISTS source VARCHAR(150);",
            "ALTER TABLE indian_standards ADD COLUMN IF NOT EXISTS retrieved_at VARCHAR(100);",
            "ALTER TABLE indian_standards ADD COLUMN IF NOT EXISTS verification_status VARCHAR(100);",
            "ALTER TABLE indian_standards ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP;",
            "ALTER TABLE standard_relationships ADD COLUMN IF NOT EXISTS source_evidence TEXT;",
            "ALTER TABLE standard_relationships ADD COLUMN IF NOT EXISTS source_document VARCHAR(255);",
            "ALTER TABLE standard_relationships ADD COLUMN IF NOT EXISTS page_or_clause_reference VARCHAR(100);",
            "ALTER TABLE standard_relationships ADD COLUMN IF NOT EXISTS verification_status VARCHAR(100);"
        ]
        for m in migrations:
            try:
                conn.execute(text(m))
                conn.commit()
            except Exception:
                pass


def get_db() -> Generator[Session, None, None]:
    """
    Provide a database session.
    """
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()