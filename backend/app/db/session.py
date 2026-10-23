from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import database_url


@lru_cache
def get_engine() -> Engine:
    return create_engine(database_url(), pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a session that is always closed."""
    with sessionmaker(bind=get_engine())() as session:
        yield session
