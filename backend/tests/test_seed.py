"""Seed loader tests: re-running must refresh dates and never duplicate rows."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app import models


def _count(Session):
    with Session() as s:
        total = s.scalar(select(func.count()).select_from(models.JobPosting))
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
        fresh = s.scalar(
            select(func.count())
            .select_from(models.JobPosting)
            .where(models.JobPosting.date_posted >= cutoff)
        )
    return total, fresh


def test_seed_rerun_refreshes_without_duplicating(tmp_path, monkeypatch):
    import app.seed as seedmod

    engine = create_engine(
        f"sqlite:///{tmp_path / 'seed.db'}",
        connect_args={"check_same_thread": False},
    )
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr(seedmod, "engine", engine)
    monkeypatch.setattr(seedmod, "SessionLocal", Session)

    seedmod.seed()
    total1, fresh1 = _count(Session)
    assert total1 > 0
    assert fresh1 == total1  # first load: everything fresh

    seedmod.seed()  # re-run
    total2, fresh2 = _count(Session)
    assert total2 == total1  # no duplication (dedup on external_id)
    assert fresh2 == total2  # re-run re-stamped every posting inside 30 days
