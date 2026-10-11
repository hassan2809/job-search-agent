from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.base import Base

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _add_missing_columns() -> None:
    """Add nullable columns that create_all cannot.

    create_all adds missing TABLES but never missing COLUMNS, and this project has no migration
    tool. A single nullable column doesn't justify pulling one in, so add it here: idempotent, a
    no-op on a fresh database, and it lets an existing leads.db gain the column on next start.
    Anything more involved than a nullable add should be a real migration.
    """
    if engine.dialect.name != "sqlite":
        return
    additions = {
        "matches": {"lead_type": "VARCHAR(20)"},
        # DEFAULT 'linkedin' backfills every message that existed before this column did -- they
        # were all LinkedIn messages, since email didn't exist as a channel yet.
        "outreach_messages": {"channel": "VARCHAR(10) DEFAULT 'linkedin'"},
    }
    with engine.begin() as conn:
        for table, columns in additions.items():
            existing = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
            if not existing:  # table not created yet; create_all will build it with the column
                continue
            for name, ddl in columns.items():
                if name not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
