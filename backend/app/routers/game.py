"""Q&A game endpoints, backed by server-side quiz sessions.

  GET  /game/skills
        -> which skills have quizzes, and at which difficulties.
  GET  /game/{skill_name}?difficulty=easy|medium|hard
        -> a quiz_id plus up to 10 questions from that bank, WITHOUT answers.
  POST /game/{skill_name}/submit
        body: {quiz_id, difficulty, answers:[{question_id, option_id}]}
        -> score, per-question results, and a `mastered` flag.

Each GET creates a QuizSession recording exactly which questions were served.
Submissions must reference their quiz_id and answer exactly those questions,
so a client cannot hand-pick questions, replay a completed quiz, or score a
"perfect" partial quiz. For logged-in players, consecutive quizzes on the same
skill and difficulty avoid repeating the previous quiz's questions as far as
the bank size allows (anonymous players get a random draw; there is no
identity to vary against). The timer is enforced by the frontend by design.

Anyone can play; attempts are saved as GameAttempt rows only when logged in
(the frontend keeps history / high score / mastery in localStorage).
`{skill_name:path}` lets skills with a slash like "CI/CD" route correctly.
"""
from __future__ import annotations

import json
import random
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select, update
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
from app.utils import utcnow_naive

router = APIRouter(prefix="/game", tags=["game"])

QUIZ_SIZE = 10
SESSION_TTL_HOURS = 24  # replay guards are retained for one day
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


def _pick_quiz_ids(
    db: Session,
    user: models.User | None,
    skill: models.Skill,
    difficulty: str,
    bank_ids: list[int],
) -> list[int]:
    """Choose up to QUIZ_SIZE ids, avoiding the user's previous quiz.

    Questions not in the player's most recent quiz for this skill and
    difficulty are preferred, so back-to-back quizzes repeat as little as the
    bank allows (a bank of 20+ yields zero overlap; a bank of exactly 10 can
    only reshuffle order).
    """
    previous: set[int] = set()
    if user is not None:
        last = db.scalar(
            select(models.QuizSession)
            .where(
                models.QuizSession.user_id == user.user_id,
                models.QuizSession.skill_id == skill.skill_id,
                models.QuizSession.difficulty == difficulty,
            )
            .order_by(
                models.QuizSession.created_at.desc(),
                models.QuizSession.session_id.desc(),
            )
            .limit(1)
        )
        if last is not None:
            previous = set(json.loads(last.question_ids))

    fresh = [qid for qid in bank_ids if qid not in previous]
    random.shuffle(fresh)
    quiz = fresh[:QUIZ_SIZE]
    if len(quiz) < QUIZ_SIZE:
        seen = [qid for qid in bank_ids if qid in previous]
        random.shuffle(seen)
        quiz += seen[: QUIZ_SIZE - len(quiz)]
    return quiz


def _claim_quiz(db: Session, session_id: int) -> bool:
    """Atomically mark one uncompleted quiz as completed."""
    claimed = db.execute(
        update(models.QuizSession)
        .where(
            models.QuizSession.session_id == session_id,
            models.QuizSession.completed.is_(False),
        )
        .values(completed=True)
        .execution_options(synchronize_session=False)
    )
    return claimed.rowcount == 1


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
        # Ignore any stray/invalid difficulty so bad data can't 500 this route.
        if difficulty in _DIFFICULTY_RANK:
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
    skill_name: str,
    difficulty: Difficulty,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(security.get_current_user_optional),
) -> GameQuestions:
    skill = _get_skill(db, skill_name)
    bank_ids = list(
        db.scalars(
            select(models.Question.question_id).where(
                models.Question.skill_id == skill.skill_id,
                models.Question.difficulty == difficulty,
            )
        )
    )
    if not bank_ids:
        raise HTTPException(
            status_code=422,
            detail=f"No {difficulty} questions for {skill.skill_name} yet.",
        )

    quiz_ids = _pick_quiz_ids(db, user, skill, difficulty, bank_ids)

    # Quiz sessions are short-lived replay guards, not permanent history.
    cutoff = utcnow_naive() - timedelta(hours=SESSION_TTL_HOURS)
    db.execute(
        delete(models.QuizSession).where(
            models.QuizSession.created_at < cutoff,
        )
    )
    quiz = models.QuizSession(
        user_id=user.user_id if user is not None else None,
        skill_id=skill.skill_id,
        difficulty=difficulty,
        question_ids=json.dumps(quiz_ids),
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    questions = db.scalars(
        select(models.Question)
        .where(models.Question.question_id.in_(quiz_ids))
        .options(selectinload(models.Question.options))
    ).all()
    by_id = {q.question_id: q for q in questions}

    served: list[QuestionOut] = []
    for qid in quiz_ids:  # keep the session's randomized question order
        q = by_id[qid]
        # Shuffle options so the correct answer's position never leaks;
        # fixture authors tend to list the correct option first.
        options = list(q.options)
        random.shuffle(options)
        served.append(
            QuestionOut(
                question_id=q.question_id,
                question_text=q.question_text,
                # is_correct is intentionally never serialized to the player.
                options=[
                    AnswerOptionOut(option_id=o.option_id, option_text=o.option_text)
                    for o in options
                ],
            )
        )
    return GameQuestions(
        quiz_id=quiz.session_id,
        skill=skill.skill_name,
        difficulty=difficulty,
        questions=served,
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

    quiz = db.get(models.QuizSession, submission.quiz_id)
    if quiz is None or quiz.skill_id != skill.skill_id:
        raise HTTPException(status_code=404, detail="Unknown quiz for this skill.")
    if quiz.difficulty != submission.difficulty:
        raise HTTPException(
            status_code=422, detail="Submitted difficulty does not match this quiz."
        )
    if quiz.completed:
        raise HTTPException(
            status_code=409, detail="This quiz has already been submitted."
        )
    # A quiz served to a logged-in player can only be submitted by that player.
    # Anonymous sessions stay open so someone who logs in mid-quiz can submit.
    if quiz.user_id is not None and (user is None or user.user_id != quiz.user_id):
        raise HTTPException(status_code=403, detail="This quiz belongs to another player.")

    # One answer per question; reject duplicates rather than silently dropping.
    chosen: dict[int, int] = {}
    for a in submission.answers:
        if a.question_id in chosen:
            raise HTTPException(
                status_code=422, detail="A question was answered more than once."
            )
        chosen[a.question_id] = a.option_id

    # The submission must answer exactly the questions this quiz served; no
    # hand-picked substitutes, no partial "perfect" quizzes.
    expected = set(json.loads(quiz.question_ids))
    if set(chosen) != expected:
        raise HTTPException(
            status_code=422,
            detail="Submit exactly the questions served for this quiz.",
        )

    questions = db.scalars(
        select(models.Question)
        .where(models.Question.question_id.in_(list(expected)))
        .options(selectinload(models.Question.options))
    ).all()

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

    # Atomically claim this quiz after validation. A second request that raced
    # past the earlier read cannot create another attempt.
    if not _claim_quiz(db, quiz.session_id):
        db.rollback()
        raise HTTPException(
            status_code=409, detail="This quiz has already been submitted."
        )

    # Save only for logged-in players; anonymous play stores no attempt.
    if user is not None:
        db.add(
            models.GameAttempt(
                user_id=user.user_id,
                skill_id=skill.skill_id,
                difficulty=quiz.difficulty,
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
