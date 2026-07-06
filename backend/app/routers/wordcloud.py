"""Search -> word cloud endpoint.

Weighting = document frequency (how many postings mention a skill) + sqrt
scaling for display, so one verbose posting can't dominate the cloud and the
largest word doesn't swamp the rest.
"""
from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.schemas import SearchRequest, WordCloudResponse, WordCloudWord

router = APIRouter(tags=["wordcloud"])


def _match_role(db: Session, req: SearchRequest) -> models.Role | None:
    """Find the best Role for the search, trying job_title then industry."""
    for term in (req.job_title, req.industry):
        if not term or not term.strip():
            continue
        role = db.scalar(
            select(models.Role).where(models.Role.role_name.ilike(f"%{term.strip()}%"))
        )
        if role:
            return role
    return None


@router.post("/wordcloud", response_model=WordCloudResponse)
def generate_wordcloud(
    req: SearchRequest, db: Session = Depends(get_db)
) -> WordCloudResponse:
    role = _match_role(db, req)
    if role is None:
        raise HTTPException(
            status_code=404,
            detail="No matching role found for that job title/industry.",
        )

    posting_count = db.scalar(
        select(func.count())
        .select_from(models.JobPosting)
        .where(models.JobPosting.role_id == role.role_id)
    )

    # Document frequency per skill: # of distinct postings (for this role) that
    # mention the skill. JobSkill has one row per (job, skill), so a count works.
    df_rows = db.execute(
        select(
            models.Skill.skill_name,
            func.count(func.distinct(models.JobSkill.job_id)).label("df"),
        )
        .join(models.JobSkill, models.JobSkill.skill_id == models.Skill.skill_id)
        .join(models.JobPosting, models.JobPosting.job_id == models.JobSkill.job_id)
        .where(models.JobPosting.role_id == role.role_id)
        .group_by(models.Skill.skill_name)
        .order_by(func.count(func.distinct(models.JobSkill.job_id)).desc())
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
