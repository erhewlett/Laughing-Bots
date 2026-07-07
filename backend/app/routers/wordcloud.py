"""Search -> word cloud endpoint.

Weighting = document frequency (how many postings mention a skill) + sqrt
scaling for display, so one verbose posting can't dominate the cloud and the
largest word doesn't swamp the rest.
"""
from __future__ import annotations

import math
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.schemas import SearchRequest, WordCloudResponse, WordCloudWord
from app.utils import utcnow_naive

router = APIRouter(tags=["wordcloud"])

MAX_POSTING_AGE_DAYS = 30  # requirement: only postings <= 30 days old


def _escape_like(term: str) -> str:
    """Escape LIKE wildcards in user input so '%'/'_' match literally
    (review #5 - prevents wildcard-injection broadening the match)."""
    return term.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


def _match_role(db: Session, req: SearchRequest) -> models.Role | None:
    """Resolve the search terms to a Role, most specific first.

    For each term (job_title, then industry):
      1. exact role-name match (case-insensitive)
      2. partial role-name match, ordered so the result is deterministic
      3. posting-title match, resolved to the role with the most matching
         postings. This lets a real title like "Front End Software Engineer"
         resolve to the "Frontend Developer" role instead of 404 (review #2).
    """
    for term in (req.job_title, req.industry):
        if not term or not term.strip():
            continue
        t = term.strip()
        like = f"%{_escape_like(t)}%"

        # 1. exact role name
        role = db.scalar(
            select(models.Role).where(func.lower(models.Role.role_name) == t.lower())
        )
        if role:
            return role

        # 2. partial role name (deterministic order for broad inputs)
        role = db.scalar(
            select(models.Role)
            .where(models.Role.role_name.ilike(like, escape="\\"))
            .order_by(models.Role.role_name)
        )
        if role:
            return role

        # 3. posting title -> role with the most matching postings
        row = db.execute(
            select(models.JobPosting.role_id, func.count().label("n"))
            .where(
                models.JobPosting.title.ilike(like, escape="\\"),
                models.JobPosting.role_id.is_not(None),
            )
            .group_by(models.JobPosting.role_id)
            .order_by(func.count().desc(), models.JobPosting.role_id)
        ).first()
        if row is not None:
            return db.get(models.Role, row.role_id)
    return None


def _posting_filters(role_id: int, req: SearchRequest) -> list:
    """WHERE clauses shared by the posting count and the frequency query."""
    cutoff = utcnow_naive() - timedelta(days=MAX_POSTING_AGE_DAYS)
    filters = [
        models.JobPosting.role_id == role_id,
        # review #3: enforce the 30-day rule at query time so the cloud stays
        # compliant as the seeded data ages (dates are stored naive-UTC).
        models.JobPosting.date_posted >= cutoff,
    ]
    if req.location and req.location.strip():
        filters.append(
            models.JobPosting.location.ilike(
                f"%{_escape_like(req.location.strip())}%", escape="\\"
            )
        )
    if req.min_salary:
        # Keep postings paying at least min_salary; JSearch salaries are often
        # null (verified), so unknown-salary postings are kept rather than
        # silently starving the cloud.
        filters.append(
            or_(
                models.JobPosting.salary_max >= req.min_salary,
                models.JobPosting.salary_min >= req.min_salary,
                and_(
                    models.JobPosting.salary_min.is_(None),
                    models.JobPosting.salary_max.is_(None),
                ),
            )
        )
    return filters


@router.post("/wordcloud", response_model=WordCloudResponse)
def generate_wordcloud(
    req: SearchRequest, db: Session = Depends(get_db)
) -> WordCloudResponse:
    # TODO(history): once auth exists, persist a models.Search row here for
    #   logged-in users (get_current_user_optional) to power GET /me/recent.
    role = _match_role(db, req)
    if role is None:
        raise HTTPException(
            status_code=404,
            detail="No matching role found for that job title/industry.",
        )

    filters = _posting_filters(role.role_id, req)

    posting_count = db.scalar(
        select(func.count()).select_from(models.JobPosting).where(*filters)
    )

    # Document frequency per skill: # of distinct postings (matching all the
    # search filters) that mention the skill. JobSkill has one row per
    # (job, skill), so a count works.
    df_rows = db.execute(
        select(
            models.Skill.skill_name,
            func.count(func.distinct(models.JobSkill.job_id)).label("df"),
        )
        .join(models.JobSkill, models.JobSkill.skill_id == models.Skill.skill_id)
        .join(models.JobPosting, models.JobPosting.job_id == models.JobSkill.job_id)
        .where(*filters)
        .group_by(models.Skill.skill_name)
        # secondary sort by name so tied document-frequencies are deterministic
        .order_by(
            func.count(func.distinct(models.JobSkill.job_id)).desc(),
            models.Skill.skill_name,
        )
        .limit(req.word_count)
    ).all()

    if not df_rows:
        # Requirement: error when there isn't enough job information.
        raise HTTPException(
            status_code=422,
            detail="Not enough job information to generate a word cloud.",
        )

    # sqrt-scale document frequencies, normalized so the top skill = 100.
    max_sqrt = math.sqrt(df_rows[0].df)  # rows are ordered by df desc
    words = [
        WordCloudWord(
            skill=name,
            count=df,
            weight=max(1, round(math.sqrt(df) / max_sqrt * 100)),
        )
        for name, df in df_rows
    ]

    return WordCloudResponse(
        role=role.role_name,
        shape=req.shape,
        posting_count=posting_count or 0,
        words=words,
    )
