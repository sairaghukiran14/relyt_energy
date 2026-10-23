import os
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import database_url
from app.db.models import Base

TEST_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://localhost/relyt_test"
)


@pytest.fixture(scope="session")
def engine():
    os.environ["DATABASE_URL"] = TEST_URL
    eng = create_engine(database_url())
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    with sessionmaker(bind=engine)() as s:
        yield s
        s.rollback()


@pytest.fixture(autouse=True)
def clean_tables(engine):
    with engine.begin() as conn:
        for table in ("wind_forecast", "actual_generation"):
            conn.exec_driver_sql(f"TRUNCATE {table}")
    yield


def utc(y, mo, d, h=0, mi=0) -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=UTC)
