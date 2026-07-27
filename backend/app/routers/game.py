"""Q&A game endpoints, backed by server-side quiz sessions.

  GET  /game/skills
        -> which skills have quizzes, and at which difficulties.
  GET  /game/{skill_name}?difficulty=easy|medium|hard
        -> a quiz_id plus up to 10 questions from that bank, WITHOUT answers.
  POST /game/{skill_name}/answer
        body: {quiz_id, question_id, option_id}
        -> whether that one pick was right, which option was, and the score so
           far, so the quiz page can grade and add points per question instead
           of only at the end. The pick is recorded before the grade is sent,
           so knowing the answer afterwards cannot change it, and re-sending a
           question replays the stored result rather than grading a new option.
           Optional: a page that skips it still submits normally.
  POST /game/{skill_name}/submit
        body: {quiz_id, difficulty, answers:[{question_id, option_id}],
               timed_out?}
        -> score, per-question results, and a `mastered` flag. Answers already
           graded above are the ones that count; a submission cannot swap them.
           `timed_out` accepts a partial quiz when the clock ran out, grading
           the unanswered questions wrong against the full max score.

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

from fastapi import APIRouter, Depends, HTTPException, Response
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
    LiveAnswer,
    LiveAnswerResult,
    QuestionOut,
    QuestionResult,
    SkillQuizzes,
)
from app.services import security
from app.utils import utcnow_naive

router = APIRouter(prefix="/game", tags=["game"])

QUIZ_SIZE = 10
SESSION_TTL_HOURS = 24  # replay guards are retained for one day
# Attempts to write one answer before giving up, see answer_question.
_ANSWER_WRITE_RETRIES = 3
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


def _locked_answers(quiz: models.QuizSession) -> dict[int, int]:
    """Answers already graded for this quiz, as {question_id: option_id}.

    JSON object keys are always strings, so they come back as ints here to
    match how question ids are handled everywhere else. The column is nullable
    on databases created before it existed, hence the empty-value guard.
    """
    if not quiz.answers:
        return {}
    return {int(qid): opt for qid, opt in json.loads(quiz.answers).items()}


def _dump_answers(answers: dict[int, int]) -> str:
    # sort_keys so the same set of answers always serializes identically, which
    # is what lets _record_answer compare against the stored value.
    return json.dumps({str(qid): opt for qid, opt in answers.items()}, sort_keys=True)


def _record_answer(db: Session, session_id: int, before: str | None, after: str) -> bool:
    """Atomically add one answer, but only if nothing else has written first.

    A compare-and-set on the whole answers blob, in the same spirit as
    _claim_quiz. Two concurrent grades of the same question cannot both land,
    so a player cannot fire off several options at once and keep the one that
    turns out to be right.
    """
    written = db.execute(
        update(models.QuizSession)
        .where(
            models.QuizSession.session_id == session_id,
            models.QuizSession.answers == before,
        )
        .values(answers=after)
        .execution_options(synchronize_session=False)
    )
    return written.rowcount == 1


def _load_quiz_for_play(
    db: Session,
    skill: models.Skill,
    quiz_id: int,
    user: models.User | None,
) -> models.QuizSession:
    """Fetch a quiz that is open for play, or raise the right error.

    Shared by the per-answer and submit routes so both enforce the same rules:
    the quiz belongs to this skill, has not been submitted, and was not served
    to a different player.
    """
    quiz = db.get(models.QuizSession, quiz_id)
    if quiz is None or quiz.skill_id != skill.skill_id:
        raise HTTPException(status_code=404, detail="Unknown quiz for this skill.")
    if quiz.completed:
        raise HTTPException(
            status_code=409, detail="This quiz has already been submitted."
        )
    # A quiz served to a logged-in player can only be played by that player.
    # Anonymous sessions stay open so someone who logs in mid-quiz can submit.
    if quiz.user_id is not None and (user is None or user.user_id != quiz.user_id):
        raise HTTPException(
            status_code=403, detail="This quiz belongs to another player."
        )
    return quiz


def _grade(chosen: dict[int, int], questions: list[models.Question]) -> int:
    """Count how many of the chosen options are correct."""
    correct = 0
    for q in questions:
        picked = chosen.get(q.question_id)
        if picked is None:
            continue
        correct += int(any(o.option_id == picked and o.is_correct for o in q.options))
    return correct


def _normalize(correct: int, total: int) -> int:
    """The 0..10000 display score. One question is worth 1000 on a full quiz."""
    return round(correct / total * 10_000) if total else 0


@router.get("/skills", response_model=list[SkillQuizzes])
def list_quiz_skills(
    response: Response, db: Session = Depends(get_db)
) -> list[SkillQuizzes]:
    """Skills that have quiz questions, with the difficulties available for each.

    Declared before the /{skill_name:path} route so "skills" is not captured as
    a skill name. Lets the frontend make only playable word-cloud words clickable.

    Changes only when the question bank changes, so it is browser-cacheable.
    The word cloud response now also carries a `playable` flag per word, which
    removes the need to call this at all just to decide what is clickable.
    """
    response.headers["Cache-Control"] = "public, max-age=300"
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


@router.post("/{skill_name:path}/answer", response_model=LiveAnswerResult)
def answer_question(
    skill_name: str,
    answer: LiveAnswer,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(security.get_current_user_optional),
) -> LiveAnswerResult:
    """Grade one answer as soon as the player commits to it.

    Lets the quiz page mark the pick right or wrong and move its points counter
    per question rather than only at the end. The pick is recorded before the
    grade goes out, so a player who now knows the right answer cannot go back
    and change the one they gave. Re-sending the same question replays the
    stored result instead of grading a second option, which is what stops
    "guess until it says correct".

    Calling this is optional. A page that never does still submits normally,
    and a grade lost to a dropped connection is filled in from the submission.
    """
    skill = _get_skill(db, skill_name)
    quiz = _load_quiz_for_play(db, skill, answer.quiz_id, user)

    quiz_ids = json.loads(quiz.question_ids)
    if answer.question_id not in set(quiz_ids):
        raise HTTPException(
            status_code=422, detail="That question is not part of this quiz."
        )

    questions = db.scalars(
        select(models.Question)
        .where(models.Question.question_id.in_(quiz_ids))
        .options(selectinload(models.Question.options))
    ).all()
    by_id = {q.question_id: q for q in questions}
    question = by_id[answer.question_id]

    if not any(o.option_id == answer.option_id for o in question.options):
        raise HTTPException(
            status_code=422,
            detail="An answer references an option that is not on its question.",
        )

    stored = quiz.answers
    locked = _locked_answers(quiz)
    already_answered = answer.question_id in locked

    # Lock the pick in before grading it. The retries cover another answer for
    # a different question landing at the same moment, which loses the
    # compare-and-set without meaning this question was answered twice. Bounded
    # because the only writer is one player's own quiz page: if the attempts
    # run out, the answer still grades correctly here and is filled in from the
    # submission at the end, it just does not get locked.
    for _ in range(_ANSWER_WRITE_RETRIES):
        if already_answered:
            break
        locked[answer.question_id] = answer.option_id
        if _record_answer(db, quiz.session_id, stored, _dump_answers(locked)):
            db.commit()
            break
        # Someone else wrote first. Re-read and build on what they recorded
        # rather than overwriting it.
        db.rollback()
        db.refresh(quiz)
        stored = quiz.answers
        locked = _locked_answers(quiz)
        already_answered = answer.question_id in locked

    graded_option = locked.get(answer.question_id, answer.option_id)
    correct_ids = [o.option_id for o in question.options if o.is_correct]
    correct_count = _grade(locked, list(questions))
    total = len(quiz_ids)

    return LiveAnswerResult(
        question_id=answer.question_id,
        is_correct=graded_option in correct_ids,
        correct_option_id=correct_ids[0] if correct_ids else None,
        already_answered=already_answered,
        answered_count=len(locked),
        total_questions=total,
        correct_count=correct_count,
        score_normalized=_normalize(correct_count, total),
        quiz_complete=len(locked) >= total,
    )


@router.post("/{skill_name:path}/submit", response_model=GameResult)
def submit_game(
    skill_name: str,
    submission: GameSubmission,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(security.get_current_user_optional),
) -> GameResult:
    skill = _get_skill(db, skill_name)
    # A quiz the clock ran out on may legitimately carry no answers at all.
    if not submission.answers and not submission.timed_out:
        raise HTTPException(status_code=422, detail="No answers submitted.")

    quiz = _load_quiz_for_play(db, skill, submission.quiz_id, user)
    if quiz.difficulty != submission.difficulty:
        raise HTTPException(
            status_code=422, detail="Submitted difficulty does not match this quiz."
        )

    # One answer per question; reject duplicates rather than silently dropping.
    chosen: dict[int, int] = {}
    for a in submission.answers:
        if a.question_id in chosen:
            raise HTTPException(
                status_code=422, detail="A question was answered more than once."
            )
        chosen[a.question_id] = a.option_id

    expected = set(json.loads(quiz.question_ids))
    if submission.timed_out:
        # The clock ran out part way through. Score the questions that were
        # answered and count the rest wrong, rather than binning the attempt.
        # max_score is still the whole quiz (see `total` below), so this can
        # never beat answering everything.
        if not set(chosen) <= expected:
            raise HTTPException(
                status_code=422,
                detail="An answer is not part of this quiz.",
            )
    # Otherwise the submission must answer exactly the questions this quiz
    # served; no hand-picked substitutes, no partial "perfect" quizzes.
    elif set(chosen) != expected:
        raise HTTPException(
            status_code=422,
            detail="Submit exactly the questions served for this quiz.",
        )

    # Anything already graded by /answer is the pick that counts. The player was
    # told at the time whether it was right, so a submission that quietly swaps
    # it would let the final score disagree with the one they watched climb.
    # Questions never graded live are simply taken from the submission, which is
    # what keeps a dropped grading call from costing anyone their answer.
    for qid, locked_option in _locked_answers(quiz).items():
        if qid in chosen and chosen[qid] != locked_option:
            raise HTTPException(
                status_code=409,
                detail="An answer was already graded and cannot be changed.",
            )
        # A timed-out submission is allowed to leave out answers the server
        # already graded. They were still given, so they still count.
        chosen[qid] = locked_option

    questions = db.scalars(
        select(models.Question)
        .where(models.Question.question_id.in_(list(expected)))
        .options(selectinload(models.Question.options))
    ).all()

    results: list[QuestionResult] = []
    score = 0
    for q in questions:
        picked = chosen.get(q.question_id)
        if picked is None:
            # Only reachable on a timed-out quiz: never answered, so wrong.
            results.append(QuestionResult(question_id=q.question_id, is_correct=False))
            continue
        option_ids = {o.option_id for o in q.options}
        if picked not in option_ids:
            raise HTTPException(
                status_code=422,
                detail="An answer references an option that is not on its question.",
            )
        correct_ids = {o.option_id for o in q.options if o.is_correct}
        is_correct = picked in correct_ids
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

    # The 0..10000 display score, computed server-side so a stored attempt and
    # the number the player saw can never disagree.
    score_normalized = _normalize(score, total)

    # Save only for logged-in players; anonymous play stores no attempt.
    if user is not None:
        db.add(
            models.GameAttempt(
                user_id=user.user_id,
                skill_id=skill.skill_id,
                difficulty=quiz.difficulty,
                score=score,
                max_score=total,
                time_taken_seconds=submission.elapsed_seconds,
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
        score_normalized=score_normalized,
        elapsed_seconds=submission.elapsed_seconds,
        recorded=user is not None,
    )
