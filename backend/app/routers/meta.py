"""Metadata endpoints for frontend dropdowns and app setup."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.routers.wordcloud import MAX_POSTING_AGE_DAYS
from app.schemas import LocationOut, RoleOut
from app.utils import utcnow_naive

router = APIRouter(tags=["meta"])

# Reference data that only changes when postings are re-ingested. Letting the
# browser reuse it for five minutes removes a request per page view without any
# frontend change.
_REFERENCE_CACHE_CONTROL = "public, max-age=300"


@router.get("/roles", response_model=list[RoleOut])
def list_roles(response: Response, db: Session = Depends(get_db)) -> list[RoleOut]:
    """Return roles that currently have fresh postings for word clouds."""
    response.headers["Cache-Control"] = _REFERENCE_CACHE_CONTROL
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


@router.get("/locations", response_model=list[LocationOut])
def list_locations(
    response: Response, db: Session = Depends(get_db)
) -> list[LocationOut]:
    """Locations that actually have fresh postings, most postings first.

    Exists so the search forms can offer real choices instead of a hardcoded
    example. A location typed from a placeholder that has no seeded postings
    makes /wordcloud return 422, which reads as a broken app rather than an
    empty search.
    """
    response.headers["Cache-Control"] = _REFERENCE_CACHE_CONTROL
    cutoff = utcnow_naive() - timedelta(days=MAX_POSTING_AGE_DAYS)
    rows = db.execute(
        select(
            models.JobPosting.location,
            func.count(models.JobPosting.job_id).label("posting_count"),
        )
        .where(
            models.JobPosting.date_posted >= cutoff,
            models.JobPosting.location.is_not(None),
            models.JobPosting.location != "",
        )
        .group_by(models.JobPosting.location)
        .order_by(
            func.count(models.JobPosting.job_id).desc(), models.JobPosting.location
        )
    ).all()

    return [
        LocationOut(location=location, posting_count=posting_count)
        for location, posting_count in rows
    ]
