"""Q&A game endpoints.

  GET  /game/{skill_name}?difficulty=easy|medium|hard
        -> 10 questions from that (skill, difficulty) bank, WITHOUT the answers.
  POST /game/{skill_name}/submit   body: {difficulty, answers:[{question_id, option_id}]}
        -> score out of the number of questions, per-question results, and a
           `mastered` flag (a perfect score on a hard quiz).

Anyone can play (optional auth). If the player is logged in, the attempt is
saved as a GameAttempt; otherwise nothing is stored (the frontend keeps
history / high score / mastery in localStorage). `{skill_name:path}` so skills
with a slash like "CI/CD" route correctly.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app import models
from app.database import get_db
from app.schemas import (
    AnswerOptionOut,
    Difficulty,
    GameQuestions,
    GameResult,
    GameSubmission,
    QuestionOut,
    QuestionResult,
)
from app.services import security

router = APIRouter(prefix="/game", tags=["game"])

QUIZ_SIZE = 10


def _get_skill(db: Session, skill_name: str) -> models.Skill:
    skill = db.scalar(
        select(models.Skill).where(
            func.lower(models.Skill.skill_name) == skill_name.lower()
        )
    )
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Unknown skill: {skill_name}")
    return skill


@router.get("/{skill_name:path}", response_model=GameQuestions)
def get_game(
    skill_name: str, difficulty: Difficulty, db: Session = Depends(get_db)
) -> GameQuestions:
    skill = _get_skill(db, skill_name)
    questions = db.scalars(
        select(models.Question)
        .where(
            models.Question.skill_id == skill.skill_id,
            models.Question.difficulty == difficulty,
        )
        .order_by(func.random())
        .limit(QUIZ_SIZE)
        .options(selectinload(models.Question.options))
    ).all()
    if not questions:
        raise HTTPException(
            status_code=422,
            detail=f"No {difficulty} questions for {skill.skill_name} yet.",
        )
    return GameQuestions(
        skill=skill.skill_name,
        difficulty=difficulty,
        questions=[
            QuestionOut(
                question_id=q.question_id,
                question_text=q.question_text,
                # is_correct is intentionally never serialized to the player.
                options=[
                    AnswerOptionOut(option_id=o.option_id, option_text=o.option_text)
                    for o in q.options
                ],
            )
            for q in questions
        ],
    )


@router.post("/{skill_name:path}/submit", response_model=GameResult)
def submit_game(
    skill_name: str,
    submission: GameSubmission,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(security.get_current_user_optional),
) -> GameResult:
    skill = _get_skill(db, skill_name)
    if not submission.answers:
        raise HTTPException(status_code=422, detail="No answers submitted.")

    # One chosen option per question (keep the first if a question is repeated).
    chosen: dict[int, int] = {}
    for a in submission.answers:
        chosen.setdefault(a.question_id, a.option_id)

    questions = db.scalars(
        select(models.Question)
        .where(
            models.Question.question_id.in_(list(chosen)),
            models.Question.skill_id == skill.skill_id,
        )
        .options(selectinload(models.Question.options))
    ).all()
    if len(questions) != len(chosen):
        raise HTTPException(
            status_code=422,
            detail="One or more questions do not belong to this skill.",
        )
    if any(q.difficulty != submission.difficulty for q in questions):
        raise HTTPException(
            status_code=422,
            detail="Submitted questions do not match the stated difficulty.",
        )

    results: list[QuestionResult] = []
    score = 0
    for q in questions:
        correct_ids = {o.option_id for o in q.options if o.is_correct}
        is_correct = chosen[q.question_id] in correct_ids
        score += int(is_correct)
        results.append(QuestionResult(question_id=q.question_id, is_correct=is_correct))

    total = len(questions)
    mastered = submission.difficulty == "hard" and score == total and total > 0

    # Save only for logged-in players; anonymous play stores nothing server-side.
    if user is not None:
        db.add(
            models.GameAttempt(
                user_id=user.user_id,
                skill_id=skill.skill_id,
                score=score,
                max_score=total,
            )
        )
        db.commit()

    return GameResult(
        skill=skill.skill_name,
        difficulty=submission.difficulty,
        score=score,
        max_score=total,
        correct_count=score,
        total_questions=total,
        mastered=mastered,
        results=results,
    )
