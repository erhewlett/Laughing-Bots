"""Metadata endpoints for frontend dropdowns and app setup."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.routers.wordcloud import MAX_POSTING_AGE_DAYS
from app.schemas import RoleOut
from app.utils import utcnow_naive

router = APIRouter(tags=["meta"])


@router.get("/roles", response_model=list[RoleOut])
def list_roles(db: Session = Depends(get_db)) -> list[RoleOut]:
    """Return roles that currently have fresh postings for word clouds."""
    cutoff = utcnow_naive() - timedelta(days=MAX_POSTING_AGE_DAYS)
    rows = db.execute(
        select(
            models.Role.role_id,
            models.Role.role_name,
            func.count(models.JobPosting.job_id).label("posting_count"),
        )
        .join(models.JobPosting, models.JobPosting.role_id == models.Role.role_id)
        .where(models.JobPosting.date_posted >= cutoff)
        # inner join + the date filter already guarantee >= 1 fresh posting
        # per returned role, so no HAVING is needed.
        .group_by(models.Role.role_id, models.Role.role_name)
        .order_by(models.Role.role_name)
    ).all()

    return [
        RoleOut(role_id=role_id, role_name=role_name, posting_count=posting_count)
        for role_id, role_name, posting_count in rows
    ]
