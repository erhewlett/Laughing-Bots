"""Startup auto-seeding decides what to reload, and just as importantly what
to leave alone. These cover both directions, since a false positive rewrites
every question id on an otherwise healthy database."""
from __future__ import annotations

from datetime import timedelta

from app import models
from app.autoseed import (
    POSTINGS_SEEDED_AT_KEY,
    QUESTIONS_FINGERPRINT_KEY,
    autoseed,
    postings_need_seeding,
    questions_need_seeding,
    set_meta,
)
from app.utils import utcnow_naive


def _add_question(db) -> None:
    skill = models.Skill(skill_name="Python")
    db.add(skill)
    db.flush()
    db.add(
        models.Question(
            skill_id=skill.skill_id, difficulty="easy", question_text="Q?"
        )
    )
    db.flush()


def _add_posting(db, age_days: int) -> None:
    # role_name is unique, so reuse it when a test adds several postings.
    role = db.query(models.Role).filter_by(role_name="Software Engineer").first()
    if role is None:
        role = models.Role(role_name="Software Engineer")
        db.add(role)
        db.flush()
    db.add(
        models.JobPosting(
            role_id=role.role_id,
            title="Dev",
            date_posted=utcnow_naive() - timedelta(days=age_days),
        )
    )
    db.flush()


def test_questions_need_seeding_when_bank_is_empty(db_session):
    assert questions_need_seeding(db_session, "abc") is True


def test_questions_skipped_when_fingerprint_matches(db_session):
    _add_question(db_session)
    set_meta(db_session, QUESTIONS_FINGERPRINT_KEY, "abc")
    db_session.flush()

    assert questions_need_seeding(db_session, "abc") is False


def test_questions_reload_when_fixture_changed(db_session):
    _add_question(db_session)
    set_meta(db_session, QUESTIONS_FINGERPRINT_KEY, "old-hash")
    db_session.flush()

    assert questions_need_seeding(db_session, "new-hash") is True


def test_questions_reload_when_fingerprint_never_recorded(db_session):
    """A database seeded by the CLI loader has questions but no fingerprint."""
    _add_question(db_session)

    assert questions_need_seeding(db_session, "abc") is True


def test_postings_need_seeding_when_empty(db_session):
    assert postings_need_seeding(db_session) is True


def _mark_seeded(db, age_days: int) -> None:
    """Record when seed() last ran, as autoseed does after loading postings."""
    set_meta(
        db,
        POSTINGS_SEEDED_AT_KEY,
        (utcnow_naive() - timedelta(days=age_days)).isoformat(),
    )
    db.flush()


def test_postings_skipped_while_fresh(db_session):
    # seed() staggers its rows up to 20 days back, so posting age says nothing
    # about freshness; the recorded load time is what counts.
    _add_posting(db_session, age_days=20)
    _mark_seeded(db_session, age_days=1)

    assert postings_need_seeding(db_session, max_age_days=7) is False


def test_postings_refresh_once_stale(db_session):
    _add_posting(db_session, age_days=1)
    _mark_seeded(db_session, age_days=8)

    assert postings_need_seeding(db_session, max_age_days=7) is True


def test_fresh_posting_does_not_suppress_a_stale_refresh(db_session):
    """Regression: staleness used to be read off max(date_posted).

    A single fresh row - one `ingest` run stamps its postings at "now" - pinned
    that check at zero days and suppressed the refresh forever, while the older
    rows silently aged out of the 30-day word-cloud window.
    """
    _add_posting(db_session, age_days=25)
    _add_posting(db_session, age_days=0)  # the row that used to hide the rest
    _mark_seeded(db_session, age_days=9)

    assert postings_need_seeding(db_session, max_age_days=7) is True


def test_postings_refresh_when_load_time_never_recorded(db_session):
    """A database seeded by the CLI loader has postings but no marker."""
    _add_posting(db_session, age_days=1)

    assert postings_need_seeding(db_session, max_age_days=7) is True


def test_autoseed_does_nothing_when_disabled(monkeypatch):
    """AUTO_SEED=false must not open a session or touch the real database."""
    from app import autoseed as autoseed_module

    monkeypatch.setattr(autoseed_module.settings, "auto_seed", False)

    def _fail(*args, **kwargs):  # pragma: no cover - only runs on regression
        raise AssertionError("auto-seed ran while disabled")

    monkeypatch.setattr(autoseed_module, "SessionLocal", _fail)
    monkeypatch.setattr(autoseed_module, "seed", _fail)
    monkeypatch.setattr(autoseed_module, "seed_questions", _fail)

    autoseed()
