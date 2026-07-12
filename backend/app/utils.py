"""Small shared helpers."""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow_naive() -> datetime:
    """Current UTC time as a naive datetime.

    Everything in the DB is stored naive-UTC, so all "now" values and date
    cutoffs go through this to stay comparable.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
