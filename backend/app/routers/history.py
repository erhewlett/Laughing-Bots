"""Post-login history: the most recent game result and recent searches.

  GET /me/recent (Bearer token) -> {last_game | null, recent_searches: [<=5]}

Searches are persisted by /wordcloud for logged-in users. Game history /
high-score / mastery otherwise live in the frontend's localStorage; last_game
here is a convenience from the saved GameAttempt.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.schemas import LastGame, RecentActivity, RecentSearch
from app.services import security

router = APIRouter(prefix="/me", tags=["history"])


@router.get("/recent", response_model=RecentActivity)
def recent_activity(
    user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
) -> RecentActivity:
    attempt = db.scalar(
        select(models.GameAttempt)
        .where(models.GameAttempt.user_id == user.user_id)
        .order_by(
            models.GameAttempt.date_taken.desc(),
            models.GameAttempt.attempt_id.desc(),
        )
        .limit(1)
    )
    last_game = (
        LastGame(
            skill=attempt.skill.skill_name,
            score=attempt.score,
            max_score=attempt.max_score,
            date_taken=attempt.date_taken,
        )
        if attempt is not None
        else None
    )

    searches = db.scalars(
        select(models.Search)
        .where(models.Search.user_id == user.user_id)
        .order_by(
            models.Search.created_at.desc(), models.Search.search_id.desc()
        )
        .limit(5)
    ).all()

    return RecentActivity(
        last_game=last_game,
        recent_searches=[RecentSearch.model_validate(s) for s in searches],
    )
