"""Ingest real job postings from JSearch into the local SQLite DB.

Pipeline:  JSearch /search  ->  map to JobPosting  ->  extract skills
           ->  upsert Skill + JobSkill (frequency)  ->  aggregate RoleSkill.

Run from the backend/ directory (requires RAPIDAPI_KEY in .env):

    python -m app.services.ingest

Target roles are defined in ROLE_QUERIES below.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app import models
from app.services import jsearch
from app.services.keywords import extract_skills
from app.utils import utcnow_naive

# Role display name -> JSearch search query. Keep the list short on the free tier.
ROLE_QUERIES: dict[str, str] = {
    "Software Engineer": "software engineer",
    "Cloud Security Engineer": "cloud security engineer",
    "Frontend Developer": "frontend developer",
    "Data Analyst": "data analyst",
}


def _parse_dt(value: str | None) -> datetime | None:
    """Parse JSearch's ISO timestamp to a NAIVE UTC datetime.

    Everything in the DB is stored naive-UTC so date comparisons (e.g. the
    30-day word-cloud filter) are apples-to-apples in SQLite.
    """
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError:
        return None


def _location(job: dict) -> str | None:
    parts = [job.get("job_city"), job.get("job_state")]
    joined = ", ".join(p for p in parts if p)
    return joined or job.get("job_country")


def _get_or_create_role(db: Session, name: str) -> models.Role:
    role = db.scalar(select(models.Role).where(models.Role.role_name == name))
    if role is None:
        role = models.Role(role_name=name)
        db.add(role)
        db.flush()
    return role


def _get_or_create_skill(db: Session, name: str, cache: dict[str, models.Skill]) -> models.Skill:
    if name in cache:
        return cache[name]
    skill = db.scalar(select(models.Skill).where(models.Skill.skill_name == name))
    if skill is None:
        skill = models.Skill(skill_name=name)
        db.add(skill)
        db.flush()
    cache[name] = skill
    return skill


def _rebuild_role_skill(db: Session, role_id: int) -> None:
    """Recompute RoleSkill.demand_score for a role from JobSkill ground truth.

    Delete-and-rebuild is idempotent: however many times ingest runs, the
    aggregate always reflects exactly what's in job_skills (review #1 fix -
    the old `+=` accumulation compounded on every run).
    """
    db.execute(delete(models.RoleSkill).where(models.RoleSkill.role_id == role_id))
    rows = db.execute(
        select(models.JobSkill.skill_id, func.sum(models.JobSkill.frequency))
        .join(models.JobPosting, models.JobPosting.job_id == models.JobSkill.job_id)
        .where(models.JobPosting.role_id == role_id)
        .group_by(models.JobSkill.skill_id)
    ).all()
    for skill_id, total in rows:
        db.add(
            models.RoleSkill(
                role_id=role_id, skill_id=skill_id, demand_score=float(total)
            )
        )


def ingest_role(db: Session, role_name: str, query: str, *, num_pages: int = 1) -> int:
    """Fetch postings for one role and persist them. Returns # NEW postings.

    Idempotent (review #1 fix): postings are deduped on JSearch's job_id via
    JobPosting.external_id, both within a run and against the existing DB, and
    RoleSkill is rebuilt from scratch rather than accumulated.
    """
    jobs = jsearch.search_jobs(query, num_pages=num_pages)
    role = _get_or_create_role(db, role_name)
    skill_cache: dict[str, models.Skill] = {}
    stored = 0

    # Dedup: ids already in the DB (any role) + ids seen earlier in this run.
    seen: set[str] = set(
        db.scalars(
            select(models.JobPosting.external_id).where(
                models.JobPosting.external_id.is_not(None)
            )
        )
    )

    for job in jobs:
        external_id = job.get("job_id")
        if external_id and external_id in seen:
            continue
        if external_id:
            seen.add(external_id)

        posting = models.JobPosting(
            external_id=external_id,
            role_id=role.role_id,
            title=job.get("job_title"),
            company_name=job.get("employer_name"),
            location=_location(job),
            salary_min=job.get("job_min_salary"),
            salary_max=job.get("job_max_salary"),
            # Missing dates fall back to ingest time: we requested
            # date_posted="month", so "now" is the most conservative bound and
            # keeps the 30-day query filter meaningful for every row.
            date_posted=_parse_dt(job.get("job_posted_at_datetime_utc"))
            or utcnow_naive(),
            source_url=job.get("job_apply_link"),
        )
        db.add(posting)
        db.flush()

        for skill_name, freq in extract_skills(job).items():
            skill = _get_or_create_skill(db, skill_name, skill_cache)
            db.add(
                models.JobSkill(
                    job_id=posting.job_id, skill_id=skill.skill_id, frequency=freq
                )
            )
        stored += 1

    # Flush pending JobSkill rows so the rebuild query (session has
    # autoflush=False) sees every row just added.
    db.flush()
    _rebuild_role_skill(db, role.role_id)
    db.commit()
    return stored


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for role_name, query in ROLE_QUERIES.items():
            try:
                n = ingest_role(db, role_name, query)
                print(f"  {role_name}: stored {n} postings")
            except jsearch.JSearchError as exc:
                print(f"  {role_name}: SKIPPED ({exc})")
    finally:
        db.close()
    print("Ingest complete.")


if __name__ == "__main__":
    main()
