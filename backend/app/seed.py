"""Load the shared job dataset into the local SQLite DB.

Run from the backend/ directory (no API key or network needed):

    python -m app.seed

This reads app/seed_data/jobhopper_seed.json (checked into the repo) so every
teammate develops against the exact same postings and skill frequencies. To
pull fresh live data instead, run:  python -m app.services.ingest

date_posted is re-stamped to load time (staggered over the last few weeks) so
the 30-day word-cloud filter always includes the seeded postings.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app import models
from app.services.ingest import (
    _get_or_create_role,
    _get_or_create_skill,
    _rebuild_role_skill,
)

FIXTURE = Path(__file__).parent / "seed_data" / "jobhopper_seed.json"


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    data = json.loads(FIXTURE.read_text())
    postings = data["postings"]

    db = SessionLocal()
    try:
        existing = set(
            db.scalars(
                select(models.JobPosting.external_id).where(
                    models.JobPosting.external_id.is_not(None)
                )
            )
        )
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        skill_cache: dict[str, models.Skill] = {}
        touched_roles: set[int] = set()
        added = 0

        for i, p in enumerate(postings):
            if p["external_id"] and p["external_id"] in existing:
                continue
            role = _get_or_create_role(db, p["role"])
            touched_roles.add(role.role_id)

            posting = models.JobPosting(
                external_id=p["external_id"],
                role_id=role.role_id,
                title=p["title"],
                company_name=p["company_name"],
                location=p["location"],
                salary_min=p["salary_min"],
                salary_max=p["salary_max"],
                # Stagger over the last ~3 weeks so all rows stay inside the
                # 30-day window regardless of when this is run.
                date_posted=now - timedelta(days=i % 21),
                source_url=p["source_url"],
            )
            db.add(posting)
            db.flush()

            for skill_name, freq in p["skills"].items():
                skill = _get_or_create_skill(db, skill_name, skill_cache)
                db.add(
                    models.JobSkill(
                        job_id=posting.job_id, skill_id=skill.skill_id, frequency=freq
                    )
                )
            added += 1

        db.flush()
        for role_id in touched_roles:
            _rebuild_role_skill(db, role_id)
        db.commit()

        total = db.scalar(select(models.JobPosting.job_id).limit(1))
        print(f"Seed complete. Added {added} postings ({len(postings) - added} already present).")
        if total is None:
            print("Warning: no postings in DB after seed.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
