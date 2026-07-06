"""Ingest real job postings from JSearch into the local SQLite DB.

Pipeline:  JSearch /search  ->  map to JobPosting  ->  extract skills
           ->  upsert Skill + JobSkill (frequency)  ->  aggregate RoleSkill.

Run from the backend/ directory (requires RAPIDAPI_KEY in .env):

    python -m app.services.ingest

Target roles are defined in ROLE_QUERIES below.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app import models
from app.services import jsearch
from app.services.keywords import extract_skills

# Role display name -> JSearch search query. Keep the list short on the free tier.
ROLE_QUERIES: dict[str, str] = {
    "Software Engineer": "software engineer",
    "Cloud Security Engineer": "cloud security engineer",
    "Frontend Developer": "frontend developer",
    "Data Analyst": "data analyst",
}


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
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


def ingest_role(db: Session, role_name: str, query: str, *, num_pages: int = 1) -> int:
    """Fetch postings for one role and persist them. Returns # postings stored."""
    jobs = jsearch.search_jobs(query, num_pages=num_pages)
    role = _get_or_create_role(db, role_name)
    skill_cache: dict[str, models.Skill] = {}
    role_demand: dict[int, int] = {}
    stored = 0

    for job in jobs:
        posting = models.JobPosting(
            role_id=role.role_id,
            title=job.get("job_title"),
            company_name=job.get("employer_name"),
            location=_location(job),
            salary_min=job.get("job_min_salary"),
            salary_max=job.get("job_max_salary"),
            date_posted=_parse_dt(job.get("job_posted_at_datetime_utc")),
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
            role_demand[skill.skill_id] = role_demand.get(skill.skill_id, 0) + freq
        stored += 1

    # Aggregate role-level demand (upsert RoleSkill).
    for skill_id, score in role_demand.items():
        rs = db.get(models.RoleSkill, {"role_id": role.role_id, "skill_id": skill_id})
        if rs is None:
            db.add(
                models.RoleSkill(
                    role_id=role.role_id, skill_id=skill_id, demand_score=float(score)
                )
            )
        else:
            rs.demand_score = (rs.demand_score or 0) + score

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
