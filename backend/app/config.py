"""Runtime configuration, read from environment variables."""

import os
from datetime import date

LOCAL_TZ = "Europe/London"

# Delivery days covered by the data (decisions made 1 to 31 January 2026).
FIRST_DELIVERY_DAY = date(2026, 1, 2)
LAST_DELIVERY_DAY = date(2026, 2, 1)

# Day-ahead gate closure: 11:00 UK time on the day before delivery.
DAYAHEAD_CUTOFF_HOUR = 11


def database_url() -> str:
    """Return the SQLAlchemy URL, forcing the psycopg 3 driver."""
    url = os.environ.get("DATABASE_URL", "postgresql+psycopg://localhost/relyt")
    if url.startswith("postgres://"):
        url = "postgresql://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url
