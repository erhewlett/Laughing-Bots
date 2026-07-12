"""Load the shared job dataset into the local SQLite DB.

Run from the backend/ directory (no API key or network needed):

    python -m app.seed

This reads app/seed_data/jobhopper_seed.json (checked into the repo) so every
teammate develops against the exact same postings and skill frequencies. To
pull fresh live data instead, run:  python -m app.services.ingest

This is a real UPSERT, not skip-if-present: re-running it re-stamps every
posting's date_posted to load time and re-syncs its skills. So re-seeding an
aged database refreshes it (keeps postings inside the 30-day word-cloud
window) and picks up edits to the committed fixture, without ever duplicating
rows (dedup is on external_id).
"""
from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from sqlalchemy import delete, select

from app.database import Base, SessionLocal, engine
from app import models
from app.services.ingest import (
    _get_or_create_role,
    _get_or_create_skill,
    _rebuild_role_skill,
)
from app.utils import utcnow_naive

FIXTURE = Path(__file__).parent / "seed_data" / "jobhopper_seed.json"


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    data = json.loads(FIXTURE.read_text())
    postings = data["postings"]

    db = SessionLocal()
    try:
        now = utcnow_naive()
        # Preload existing postings by external_id in one query, so the loop is
        # dict lookups instead of one SELECT per fixture row.
        existing: dict[str, models.JobPosting] = {
            p.external_id: p
            for p in db.scalars(
                select(models.JobPosting).where(
                    models.JobPosting.external_id.is_not(None)
                )
            )
        }
        skill_cache: dict[str, models.Skill] = {}
        touched_roles: set[int] = set()
        added = updated = 0

        for i, p in enumerate(postings):
            role = _get_or_create_role(db, p["role"])
            touched_roles.add(role.role_id)

            posting = existing.get(p["external_id"]) if p["external_id"] else None
            if posting is None:
                posting = models.JobPosting(external_id=p["external_id"])
                db.add(posting)
                if p["external_id"]:
                    existing[p["external_id"]] = posting
                added += 1
            else:
                updated += 1

            posting.role_id = role.role_id
            posting.title = p["title"]
            posting.company_name = p["company_name"]
            posting.location = p["location"]
            posting.salary_min = p["salary_min"]
            posting.salary_max = p["salary_max"]
            # Stagger over the last ~3 weeks so every row stays inside the
            # 30-day window no matter when this runs. Re-stamped every run.
            posting.date_posted = now - timedelta(days=i % 21)
            posting.source_url = p["source_url"]
            db.flush()

            # Replace this posting's skill rows so fixture edits take effect.
            db.execute(
                delete(models.JobSkill).where(models.JobSkill.job_id == posting.job_id)
            )
            for skill_name, freq in p["skills"].items():
                skill = _get_or_create_skill(db, skill_name, skill_cache)
                db.add(
                    models.JobSkill(
                        job_id=posting.job_id, skill_id=skill.skill_id, frequency=freq
                    )
                )

        db.flush()
        for role_id in touched_roles:
            _rebuild_role_skill(db, role_id)
        db.commit()
        print(f"Seed complete. {added} added, {updated} refreshed.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
