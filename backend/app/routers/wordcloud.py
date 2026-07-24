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
from app.services import security
from app.utils import utcnow_naive

router = APIRouter(tags=["wordcloud"])

MAX_POSTING_AGE_DAYS = 30  # requirement: only postings <= 30 days old


def _escape_like(term: str) -> str:
    """Escape LIKE wildcards in user input so '%'/'_' match literally
    (review #5 - prevents wildcard-injection broadening the match)."""
    return term.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


# A posting-title match only resolves a role when the term actually looks like
# a job title. A single incidental word ("Marketing", "Radar", "Salesforce")
# used to hijack the whole search because it appeared in one of 40 titles.
MIN_TITLE_MATCH_POSTINGS = 2


def _match_role(db: Session, req: SearchRequest) -> models.Role | None:
    """Resolve the search terms to a Role, most specific first.

    For each term (job_title, then industry):
      1. exact role-name match (case-insensitive)
      2. partial role-name match; ambiguous matches are reported rather than
         silently resolved to whichever name sorts first
      3. posting-title match, but only for job_title and only when the term is
         specific enough to be a real title. This still lets "Front End
         Software Engineer" resolve to the "Frontend Developer" role.

    Raises HTTPException(409) when a term matches several roles equally well.
    """
    for term, is_job_title in ((req.job_title, True), (req.industry, False)):
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

        # 2. partial role name
        candidates = db.scalars(
            select(models.Role)
            .where(models.Role.role_name.ilike(like, escape="\\"))
            .order_by(models.Role.role_name)
        ).all()
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            # "Engineer" matches several roles; picking the alphabetically
            # first one silently answered a different question than was asked.
            names = ", ".join(r.role_name for r in candidates)
            raise HTTPException(
                status_code=409,
                detail=f"'{t}' matches several roles ({names}). Please be more specific.",
            )

        # 3. posting title -> role with the most matching postings.
        # Industries are not job titles, so they never resolve this way.
        if not is_job_title:
            continue
        # Multi-word terms are specific enough on their own; single words must
        # show up in several postings before we trust them.
        min_postings = 1 if len(t.split()) > 1 else MIN_TITLE_MATCH_POSTINGS
        row = db.execute(
            select(models.JobPosting.role_id, func.count().label("n"))
            .where(
                models.JobPosting.title.ilike(like, escape="\\"),
                models.JobPosting.role_id.is_not(None),
            )
            .group_by(models.JobPosting.role_id)
            .order_by(func.count().desc(), models.JobPosting.role_id)
        ).first()
        if row is not None and row.n >= min_postings:
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
    if req.min_salary is not None:
        # Keep postings paying at least min_salary; JSearch salaries are often
        # null (verified), so unknown-salary postings are kept rather than
        # silently starving the cloud. They are excluded from the reported
        # posting_count though - see _salary_verified_filter.
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


def _salary_verified_filter(req: SearchRequest):
    """Clause matching only postings whose salary is known to clear min_salary.

    The cloud is still built from unknown-salary postings, but reporting them
    as matches overstated the evidence: min_salary=99999999 used to come back
    claiming 5 matching postings.
    """
    if req.min_salary is None:
        return None
    return or_(
        models.JobPosting.salary_max >= req.min_salary,
        models.JobPosting.salary_min >= req.min_salary,
    )


@router.post("/wordcloud", response_model=WordCloudResponse)
def generate_wordcloud(
    req: SearchRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
) -> WordCloudResponse:
    role = _match_role(db, req)
    if role is None:
        raise HTTPException(
            status_code=404,
            detail="No matching role found for that job title/industry.",
        )

    filters = _posting_filters(role.role_id, req)

    # Count only postings we can actually vouch for against the search terms.
    count_filters = list(filters)
    verified = _salary_verified_filter(req)
    if verified is not None:
        count_filters.append(verified)
    posting_count = db.scalar(
        select(func.count()).select_from(models.JobPosting).where(*count_filters)
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

    # Remember this search (powers GET /me/recent).
    db.add(
        models.Search(
            user_id=user.user_id,
            job_title=req.job_title,
            industry=req.industry,
            location=req.location,
            min_salary=req.min_salary,
            word_count=req.word_count,
            shape=req.shape,
        )
    )
    db.commit()

    return WordCloudResponse(
        role=role.role_name,
        shape=req.shape,
        word_count=req.word_count,
        posting_count=posting_count or 0,
        words=words,
    )
