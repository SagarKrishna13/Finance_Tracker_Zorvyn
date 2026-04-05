"""
Database setup.

engine     - single SQLAlchemy engine shared by the whole app
SessionLocal - factory that produces per-request DB sessions
Base       - declarative base that all ORM models inherit from

The get_db dependency yields a session and guarantees it is
closed after the request completes, even on errors.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from src.core.config import settings

# connect_args is only needed for SQLite (disables same-thread check)
connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency - yields a DB session, always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
