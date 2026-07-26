"""Post-login history: the most recent game result and recent searches.

  GET /me/recent (Bearer token) -> {last_game | null, recent_searches: [<=5]}

Searches are persisted by /wordcloud for logged-in users. Game history /
high-score / mastery otherwise live in the frontend's localStorage; last_game
here is a convenience from the saved GameAttempt.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Float, cast, func, select
from sqlalchemy.orm import Session, joinedload

from app import models
from app.database import get_db
from app.schemas import (
    GameHistory,
    GameHistoryItem,
    LastGame,
    RecentActivity,
    RecentSearch,
    SkillBest,
)
from app.services import security

router = APIRouter(prefix="/me", tags=["history"])


@router.get("/recent", response_model=RecentActivity)
def recent_activity(
    user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
) -> RecentActivity:
    attempt = db.scalar(
        select(models.GameAttempt)
        # Eager-load the skill; reading attempt.skill.skill_name below would
        # otherwise fire a second query after this one.
        .options(joinedload(models.GameAttempt.skill))
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
            difficulty=attempt.difficulty,
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
        username=user.username,
        name=user.name,
        email=user.email,
    )


# Mastery is a perfect score on a full-length hard quiz, matching the rule
# submit_game applies when it grades one.
FULL_QUIZ = 10


@router.get("/games", response_model=GameHistory)
def game_history(
    limit: int = Query(default=20, ge=1, le=100),
    user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
) -> GameHistory:
    """Full game history plus per-skill bests, for a results/history page.

    Three queries regardless of how many attempts come back: the page of
    attempts, the lifetime totals, and the per-skill bests. Nothing here is
    computed per row in Python beyond formatting.
    """
    rows = db.scalars(
        select(models.GameAttempt)
        .options(joinedload(models.GameAttempt.skill))
        .where(models.GameAttempt.user_id == user.user_id)
        .order_by(
            models.GameAttempt.date_taken.desc(),
            models.GameAttempt.attempt_id.desc(),
        )
        .limit(limit)
    ).all()

    attempts = [
        GameHistoryItem(
            attempt_id=a.attempt_id,
            skill=a.skill.skill_name,
            difficulty=a.difficulty,
            score=a.score,
            max_score=a.max_score,
            score_normalized=(
                round(a.score / a.max_score * 10_000) if a.max_score else 0
            ),
            percentage=round(a.score / a.max_score * 100) if a.max_score else 0,
            mastered=(
                a.difficulty == "hard"
                and a.max_score == FULL_QUIZ
                and a.score == a.max_score
            ),
            elapsed_seconds=a.time_taken_seconds,
            date_taken=a.date_taken,
        )
        for a in rows
    ]

    # Lifetime totals over every attempt, not just the returned page.
    totals = db.execute(
        select(
            func.count(models.GameAttempt.attempt_id),
            func.coalesce(func.sum(models.GameAttempt.score), 0),
            func.coalesce(func.sum(models.GameAttempt.max_score), 0),
        ).where(models.GameAttempt.user_id == user.user_id)
    ).one()

    # Rank each attempt within its skill+difficulty and keep the genuine best.
    #
    # A plain GROUP BY with MAX(score), MAX(max_score) takes the two maxima
    # independently, so they can come from different attempts: 3/3 and 5/10
    # reported as "5/10", a ratio nobody actually scored. Ranking by ratio and
    # taking row 1 keeps the pair from one real attempt. nullif guards a 0
    # max_score, which sorts last rather than raising.
    ranked = (
        select(
            models.GameAttempt.skill_id.label("skill_id"),
            models.GameAttempt.difficulty.label("difficulty"),
            models.GameAttempt.score.label("score"),
            models.GameAttempt.max_score.label("max_score"),
            func.row_number()
            .over(
                partition_by=(
                    models.GameAttempt.skill_id,
                    models.GameAttempt.difficulty,
                ),
                order_by=(
                    (
                        cast(models.GameAttempt.score, Float)
                        / func.nullif(models.GameAttempt.max_score, 0)
                    ).desc(),
                    # Tie-break toward the longer quiz so a perfect full-length
                    # run outranks a perfect short one, which keeps mastery
                    # detectable below.
                    models.GameAttempt.score.desc(),
                    models.GameAttempt.attempt_id.desc(),
                ),
            )
            .label("rn"),
            func.count()
            .over(
                partition_by=(
                    models.GameAttempt.skill_id,
                    models.GameAttempt.difficulty,
                )
            )
            .label("attempts"),
        )
        .where(models.GameAttempt.user_id == user.user_id)
        .subquery()
    )

    best_rows = db.execute(
        select(
            models.Skill.skill_name,
            ranked.c.difficulty,
            ranked.c.score,
            ranked.c.max_score,
            ranked.c.attempts,
        )
        .join(models.Skill, models.Skill.skill_id == ranked.c.skill_id)
        .where(ranked.c.rn == 1)
        .order_by(models.Skill.skill_name, ranked.c.difficulty)
    ).all()

    bests = [
        SkillBest(
            skill=skill_name,
            difficulty=difficulty,
            best_score=best_score,
            max_score=max_score,
            attempts=n,
        )
        for skill_name, difficulty, best_score, max_score, n in best_rows
    ]

    mastered_skills = sorted(
        {
            b.skill
            for b in bests
            if b.difficulty == "hard"
            and b.max_score == FULL_QUIZ
            and b.best_score == b.max_score
        }
    )

    return GameHistory(
        total_attempts=totals[0],
        total_correct=totals[1],
        total_questions=totals[2],
        mastered_skills=mastered_skills,
        bests=bests,
        attempts=attempts,
    )
