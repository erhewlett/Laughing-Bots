"""Keep a local database current without anyone remembering to reseed.

The repo used to ship a pre-seeded jobhopper.db so the server ran right after
install. That worked until the fixtures moved on without it: the question bank
grew to 15 skills while the committed database still held the original 8
questions, so /game/skills reported two skills and most word-cloud words came
back unclickable.

Startup now does what initialize_database() already does for the schema, one
level up: look at what is there, load what is missing, stay quiet otherwise.

Two different questions, so two different triggers:

- Questions are content. They only change when someone edits the fixture, so
  we fingerprint the file and reload only when that fingerprint moves. A blind
  reload every boot would renumber every question, and QuizSession stores the
  ids it served as plain JSON with no foreign key - restarting mid-quiz would
  break the submit.
- Postings are content with an expiry. seed() re-stamps date_posted to load
  time, and the word cloud drops anything older than 30 days, so a database
  left alone slowly empties out. Age is the trigger there, not content.

Set AUTO_SEED=false to turn all of this off.
"""
from __future__ import annotations

import hashlib

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.database import SessionLocal
from app.seed import FIXTURE as POSTINGS_FIXTURE, seed
from app.seed_questions import FIXTURE as QUESTIONS_FIXTURE, seed_questions
from app.utils import utcnow_naive

# Refresh postings once they drift this far from load time. Well inside the
# 30-day word-cloud window, so the cloud never thins out while we wait.
POSTING_MAX_AGE_DAYS = 7

QUESTIONS_FINGERPRINT_KEY = "questions_fixture_sha256"


def fixture_fingerprint(path=QUESTIONS_FIXTURE) -> str:
    """Content hash of the question fixture.

    Hashing the bytes rather than counting rows means an edit to a single
    answer option still triggers a reload.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_meta(db: Session, key: str) -> str | None:
    row = db.get(models.AppMeta, key)
    return row.value if row is not None else None


def set_meta(db: Session, key: str, value: str) -> None:
    row = db.get(models.AppMeta, key)
    if row is None:
        db.add(models.AppMeta(key=key, value=value))
    else:
        row.value = value


def questions_need_seeding(db: Session, fingerprint: str) -> bool:
    """True when the bank is empty or the fixture has changed since last load."""
    if db.scalar(select(func.count()).select_from(models.Question)) == 0:
        return True
    return get_meta(db, QUESTIONS_FINGERPRINT_KEY) != fingerprint


def postings_need_seeding(db: Session, max_age_days: int = POSTING_MAX_AGE_DAYS) -> bool:
    """True when there are no postings, or the freshest one has gone stale."""
    newest = db.scalar(select(func.max(models.JobPosting.date_posted)))
    if newest is None:
        return True
    return (utcnow_naive() - newest).days >= max_age_days


def autoseed() -> None:
    """Load whatever the local database is missing. Safe to call every start."""
    if not settings.auto_seed:
        return

    if not POSTINGS_FIXTURE.exists() or not QUESTIONS_FIXTURE.exists():
        # A checkout without fixtures is not something we can fix here, and it
        # should not stop the API from booting.
        print("Auto-seed skipped: seed fixtures not found.")
        return

    fingerprint = fixture_fingerprint()

    db = SessionLocal()
    try:
        needs_postings = postings_need_seeding(db)
        needs_questions = questions_need_seeding(db, fingerprint)
    finally:
        db.close()

    if needs_postings:
        seed()
    if needs_questions:
        # prune=True: startup treats the fixture as the whole truth, so a skill
        # dropped from the file stops being offered instead of lingering in a
        # bank nothing rewrites.
        seed_questions(prune=True)
        db = SessionLocal()
        try:
            set_meta(db, QUESTIONS_FINGERPRINT_KEY, fingerprint)
            db.commit()
        finally:
            db.close()
