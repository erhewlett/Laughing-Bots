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
    SkillQuizzes,
)
from app.services import security

router = APIRouter(prefix="/game", tags=["game"])

QUIZ_SIZE = 10
_DIFFICULTY_RANK = {"easy": 0, "medium": 1, "hard": 2}


def _get_skill(db: Session, skill_name: str) -> models.Skill:
    skill = db.scalar(
        select(models.Skill).where(
            func.lower(models.Skill.skill_name) == skill_name.lower()
        )
    )
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Unknown skill: {skill_name}")
    return skill


@router.get("/skills", response_model=list[SkillQuizzes])
def list_quiz_skills(db: Session = Depends(get_db)) -> list[SkillQuizzes]:
    """Skills that have quiz questions, with the difficulties available for each.

    Declared before the /{skill_name:path} route so "skills" is not captured as
    a skill name. Lets the frontend make only playable word-cloud words clickable.
    """
    rows = db.execute(
        select(models.Skill.skill_name, models.Question.difficulty)
        .join(models.Question, models.Question.skill_id == models.Skill.skill_id)
        .distinct()
        .order_by(models.Skill.skill_name, models.Question.difficulty)
    ).all()
    grouped: dict[str, list[str]] = {}
    for skill_name, difficulty in rows:
        grouped.setdefault(skill_name, []).append(difficulty)
    return [
        SkillQuizzes(
            skill=name,
            difficulties=sorted(diffs, key=lambda d: _DIFFICULTY_RANK[d]),
        )
        for name, diffs in grouped.items()
    ]


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

    # One answer per question; reject duplicates rather than silently dropping.
    chosen: dict[int, int] = {}
    for a in submission.answers:
        if a.question_id in chosen:
            raise HTTPException(
                status_code=422, detail="A question was answered more than once."
            )
        chosen[a.question_id] = a.option_id

    # A submission must cover a full quiz for this bank. Without this, a client
    # could submit one correct hard answer and score a "perfect" 1/1 quiz.
    bank_size = (
        db.scalar(
            select(func.count())
            .select_from(models.Question)
            .where(
                models.Question.skill_id == skill.skill_id,
                models.Question.difficulty == submission.difficulty,
            )
        )
        or 0
    )
    expected = min(QUIZ_SIZE, bank_size)
    if expected == 0:
        raise HTTPException(
            status_code=422,
            detail=f"No {submission.difficulty} questions for {skill.skill_name}.",
        )
    if len(chosen) != expected:
        raise HTTPException(
            status_code=422,
            detail=f"Submit all {expected} questions for this quiz.",
        )

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
        option_ids = {o.option_id for o in q.options}
        if chosen[q.question_id] not in option_ids:
            raise HTTPException(
                status_code=422,
                detail="An answer references an option that is not on its question.",
            )
        correct_ids = {o.option_id for o in q.options if o.is_correct}
        is_correct = chosen[q.question_id] in correct_ids
        score += int(is_correct)
        results.append(QuestionResult(question_id=q.question_id, is_correct=is_correct))

    total = len(questions)
    # Mastery requires a full 10-question hard quiz answered perfectly.
    mastered = (
        submission.difficulty == "hard" and score == total and total == QUIZ_SIZE
    )

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
