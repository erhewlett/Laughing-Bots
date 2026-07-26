"""Q&A game endpoint tests.

Covers: question serving (10-cap, no answers leaked, difficulty filter, slash
skills), scoring, the mastery flag, validation, and the anonymous-vs-logged-in
save behavior.
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select

from app import models
from app.routers.game import _claim_quiz
from app.utils import utcnow_naive


def _seed_questions(db, *, skill_name="Python", difficulty="easy", n=10, correct_index=0):
    """Seed one skill with n questions of a difficulty; option[0] is correct."""
    skill = db.scalar(select(models.Skill).where(models.Skill.skill_name == skill_name))
    if skill is None:
        skill = models.Skill(skill_name=skill_name)
        db.add(skill)
        db.flush()
    for i in range(n):
        q = models.Question(
            skill_id=skill.skill_id, difficulty=difficulty, question_text=f"Q{i}"
        )
        db.add(q)
        db.flush()
        for j in range(4):
            db.add(
                models.AnswerOption(
                    question_id=q.question_id,
                    option_text=f"opt{j}",
                    is_correct=(j == correct_index),
                )
            )
    db.commit()
    return skill


def _fetch_quiz(client, skill, difficulty, *, headers=None):
    return client.get(
        f"/game/{skill}", params={"difficulty": difficulty}, headers=headers or {}
    ).json()


def _play(client, skill, difficulty, *, headers=None, wrong=0):
    """Fetch a quiz and submit it; make `wrong` of the answers incorrect.

    Options come back shuffled, so the correct one is found by its seeded
    text ("opt0" when correct_index=0), not by position.
    """
    quiz = _fetch_quiz(client, skill, difficulty, headers=headers)
    answers = []
    for i, q in enumerate(quiz["questions"]):
        correct = next(o for o in q["options"] if o["option_text"] == "opt0")
        incorrect = next(o for o in q["options"] if o["option_text"] != "opt0")
        opt = incorrect if i < wrong else correct
        answers.append({"question_id": q["question_id"], "option_id": opt["option_id"]})
    return client.post(
        f"/game/{skill}/submit",
        json={
            "quiz_id": quiz["quiz_id"],
            "difficulty": difficulty,
            "answers": answers,
        },
        headers=headers or {},
    )


def _token(client, username="player"):
    client.post("/auth/register", json={"username": username, "password": "password123"})
    return client.post(
        "/auth/login", json={"username": username, "password": "password123"}
    ).json()["access_token"]


# --- serving questions -------------------------------------------------------

def test_options_are_shuffled(client, db_session):
    # One question, four options: over 20 fetches the first option must vary,
    # otherwise the correct answer's position leaks to the player.
    _seed_questions(db_session, n=1)
    first_option_ids = set()
    for _ in range(20):
        q = client.get("/game/Python", params={"difficulty": "easy"}).json()["questions"][0]
        first_option_ids.add(q["options"][0]["option_id"])
    assert len(first_option_ids) > 1


def test_get_returns_questions_without_answers(client, db_session):
    _seed_questions(db_session, n=10)
    r = client.get("/game/Python", params={"difficulty": "easy"})
    assert r.status_code == 200
    body = r.json()
    assert body["skill"] == "Python" and body["difficulty"] == "easy"
    assert "quiz_id" in body
    assert len(body["questions"]) == 10
    assert "is_correct" not in str(body)  # answers never leak to the client


def test_get_prunes_all_expired_quiz_sessions(client, db_session):
    skill = _seed_questions(db_session, n=1)
    old_time = utcnow_naive() - timedelta(hours=25)
    recent_time = utcnow_naive() - timedelta(hours=1)
    old_open = models.QuizSession(
        skill_id=skill.skill_id,
        difficulty="easy",
        question_ids="[]",
        completed=False,
        created_at=old_time,
    )
    old_completed = models.QuizSession(
        skill_id=skill.skill_id,
        difficulty="easy",
        question_ids="[]",
        completed=True,
        created_at=old_time,
    )
    recent_completed = models.QuizSession(
        skill_id=skill.skill_id,
        difficulty="easy",
        question_ids="[]",
        completed=True,
        created_at=recent_time,
    )
    db_session.add_all([old_open, old_completed, recent_completed])
    db_session.commit()
    old_ids = {old_open.session_id, old_completed.session_id}

    assert client.get("/game/Python", params={"difficulty": "easy"}).status_code == 200
    remaining = set(db_session.scalars(select(models.QuizSession.session_id)))
    assert remaining.isdisjoint(old_ids)
    assert recent_completed.session_id in remaining


def test_get_caps_at_ten(client, db_session):
    _seed_questions(db_session, n=15)
    assert len(client.get("/game/Python", params={"difficulty": "easy"}).json()["questions"]) == 10


def test_get_respects_difficulty(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=4)
    _seed_questions(db_session, difficulty="hard", n=3)
    assert len(client.get("/game/Python", params={"difficulty": "hard"}).json()["questions"]) == 3


def test_get_unknown_skill_404(client, db_session):
    _seed_questions(db_session)
    assert client.get("/game/Nonsense", params={"difficulty": "easy"}).status_code == 404


def test_get_empty_bank_422(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=5)  # skill exists, but no hard
    assert client.get("/game/Python", params={"difficulty": "hard"}).status_code == 422


def test_get_bad_difficulty_422(client, db_session):
    _seed_questions(db_session)
    assert client.get("/game/Python", params={"difficulty": "expert"}).status_code == 422


def test_get_slash_skill_routes(client, db_session):
    _seed_questions(db_session, skill_name="CI/CD", n=3)
    r = client.get("/game/CI/CD", params={"difficulty": "easy"})
    assert r.status_code == 200 and r.json()["skill"] == "CI/CD"


def test_list_quiz_skills(client, db_session):
    _seed_questions(db_session, skill_name="Python", difficulty="easy", n=2)
    _seed_questions(db_session, skill_name="Python", difficulty="hard", n=2)
    _seed_questions(db_session, skill_name="SQL", difficulty="easy", n=1)
    r = client.get("/game/skills")  # must route here, not to /{skill_name}
    assert r.status_code == 200
    by_skill = {row["skill"]: row["difficulties"] for row in r.json()}
    assert by_skill["Python"] == ["easy", "hard"]
    assert by_skill["SQL"] == ["easy"]


def test_list_quiz_skills_empty(client, db_session):
    assert client.get("/game/skills").json() == []


def test_skills_ignores_unknown_difficulty(client, db_session):
    _seed_questions(db_session, skill_name="Python", difficulty="easy", n=2)
    # a stray bad difficulty inserted directly, as if a seed typo slipped in
    bad = models.Skill(skill_name="Rust")
    db_session.add(bad)
    db_session.flush()
    db_session.add(
        models.Question(skill_id=bad.skill_id, difficulty="meduim", question_text="?")
    )
    db_session.commit()
    r = client.get("/game/skills")
    assert r.status_code == 200  # must not 500 on the bad value
    by_skill = {row["skill"]: row["difficulties"] for row in r.json()}
    assert by_skill["Python"] == ["easy"]
    assert "Rust" not in by_skill  # skill with only an invalid difficulty is dropped


# --- scoring + mastery -------------------------------------------------------

def test_submit_scores_all_correct(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=10)
    body = _play(client, "Python", "easy").json()
    assert body["score"] == 10 and body["correct_count"] == 10 and body["max_score"] == 10
    assert len(body["results"]) == 10 and all(r["is_correct"] for r in body["results"])


def test_submit_partial_score(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=10)
    body = _play(client, "Python", "easy", wrong=3).json()
    assert body["score"] == 7


def test_perfect_hard_is_mastered(client, db_session):
    _seed_questions(db_session, difficulty="hard", n=10)
    assert _play(client, "Python", "hard").json()["mastered"] is True


def test_imperfect_hard_not_mastered(client, db_session):
    _seed_questions(db_session, difficulty="hard", n=10)
    assert _play(client, "Python", "hard", wrong=1).json()["mastered"] is False


def test_perfect_easy_not_mastered(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=10)
    assert _play(client, "Python", "easy").json()["mastered"] is False


# --- validation --------------------------------------------------------------

def _quiz_answers(client, skill, difficulty, count=None):
    """Fetch a quiz; return (quiz_id, answers picking each question's first option)."""
    quiz = _fetch_quiz(client, skill, difficulty)
    qs = quiz["questions"] if count is None else quiz["questions"][:count]
    answers = [
        {"question_id": q["question_id"], "option_id": q["options"][0]["option_id"]}
        for q in qs
    ]
    return quiz["quiz_id"], answers


def test_submit_incomplete_quiz_422(client, db_session):
    # quiz served 10 but only 3 answered -> reject (no partial-quiz "mastery")
    _seed_questions(db_session, difficulty="easy", n=10)
    quiz_id, answers = _quiz_answers(client, "Python", "easy", count=3)
    r = client.post(
        "/game/Python/submit",
        json={"quiz_id": quiz_id, "difficulty": "easy", "answers": answers},
    )
    assert r.status_code == 422


def test_submit_duplicate_question_422(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=10)
    quiz_id, answers = _quiz_answers(client, "Python", "easy", count=1)
    r = client.post(
        "/game/Python/submit",
        json={"quiz_id": quiz_id, "difficulty": "easy", "answers": [answers[0], answers[0]]},
    )
    assert r.status_code == 422


def test_submit_option_not_on_question_422(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=10)
    quiz_id, answers = _quiz_answers(client, "Python", "easy")
    answers[0]["option_id"] = 999999  # option that is not on that question
    r = client.post(
        "/game/Python/submit",
        json={"quiz_id": quiz_id, "difficulty": "easy", "answers": answers},
    )
    assert r.status_code == 422


def test_submit_foreign_question_422(client, db_session):
    _seed_questions(db_session, skill_name="Python", difficulty="easy", n=10)
    _seed_questions(db_session, skill_name="SQL", difficulty="easy", n=1)
    quiz_id, answers = _quiz_answers(client, "Python", "easy", count=9)
    _, foreign = _quiz_answers(client, "SQL", "easy", count=1)
    answers += foreign  # 10 total, one from another skill's quiz
    r = client.post(
        "/game/Python/submit",
        json={"quiz_id": quiz_id, "difficulty": "easy", "answers": answers},
    )
    assert r.status_code == 422


def test_submit_difficulty_mismatch_422(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=10)
    quiz_id, answers = _quiz_answers(client, "Python", "easy")
    # claim hard while holding an easy quiz
    r = client.post(
        "/game/Python/submit",
        json={"quiz_id": quiz_id, "difficulty": "hard", "answers": answers},
    )
    assert r.status_code == 422


def test_submit_unknown_quiz_404(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=10)
    _, answers = _quiz_answers(client, "Python", "easy")
    r = client.post(
        "/game/Python/submit",
        json={"quiz_id": 999999, "difficulty": "easy", "answers": answers},
    )
    assert r.status_code == 404


def test_quiz_cannot_be_submitted_twice(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=10)
    quiz_id, answers = _quiz_answers(client, "Python", "easy")
    payload = {"quiz_id": quiz_id, "difficulty": "easy", "answers": answers}
    assert client.post("/game/Python/submit", json=payload).status_code == 200
    assert client.post("/game/Python/submit", json=payload).status_code == 409


def test_quiz_claim_is_atomic(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=1)
    quiz_id, _ = _quiz_answers(client, "Python", "easy")
    assert _claim_quiz(db_session, quiz_id) is True
    assert _claim_quiz(db_session, quiz_id) is False


def test_consecutive_quizzes_avoid_repeats_for_user(client, db_session):
    # bank of 20: a logged-in player's second quiz shares zero questions
    _seed_questions(db_session, difficulty="easy", n=20)
    h = {"Authorization": f"Bearer {_token(client)}"}
    q1 = _fetch_quiz(client, "Python", "easy", headers=h)
    q2 = _fetch_quiz(client, "Python", "easy", headers=h)
    ids1 = {q["question_id"] for q in q1["questions"]}
    ids2 = {q["question_id"] for q in q2["questions"]}
    assert len(ids1) == 10 and len(ids2) == 10
    assert ids1.isdisjoint(ids2)


def test_other_users_quiz_403(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=10)
    ha = {"Authorization": f"Bearer {_token(client, 'alice')}"}
    quiz = _fetch_quiz(client, "Python", "easy", headers=ha)
    answers = [
        {"question_id": q["question_id"], "option_id": q["options"][0]["option_id"]}
        for q in quiz["questions"]
    ]
    hb = {"Authorization": f"Bearer {_token(client, 'bobby')}"}
    r = client.post(
        "/game/Python/submit",
        json={"quiz_id": quiz["quiz_id"], "difficulty": "easy", "answers": answers},
        headers=hb,
    )
    assert r.status_code == 403


# --- save behavior -----------------------------------------------------------

def test_anonymous_submit_saves_nothing(client, db_session):
    _seed_questions(db_session, n=10)
    _play(client, "Python", "easy")
    assert db_session.scalar(select(func.count()).select_from(models.GameAttempt)) == 0


def test_logged_in_submit_saves_attempt(client, db_session):
    _seed_questions(db_session, n=10)
    token = _token(client)
    _play(client, "Python", "easy", headers={"Authorization": f"Bearer {token}"})
    attempts = db_session.scalars(select(models.GameAttempt)).all()
    assert len(attempts) == 1
    assert attempts[0].score == 10 and attempts[0].max_score == 10
    assert attempts[0].difficulty == "easy"


# --- normalized score / elapsed time ----------------------------------------


def test_submit_returns_normalized_score(client, db_session):
    """The 0..10000 display score comes from the server, not just the client.

    Keeps a stored attempt and the number the player saw from disagreeing.
    """
    _seed_questions(db_session, n=10)
    body = _play(client, "Python", "easy").json()

    assert body["score"] == 10
    assert body["score_normalized"] == 10_000


def test_normalized_score_scales_with_partial_score(client, db_session):
    _seed_questions(db_session, n=10)
    body = _play(client, "Python", "easy", wrong=4).json()

    assert body["score"] == 6
    assert body["score_normalized"] == 6_000


def test_submit_rejects_negative_elapsed_seconds(client, db_session):
    _seed_questions(db_session, n=3)
    quiz = _fetch_quiz(client, "Python", "easy")
    answers = [
        {
            "question_id": q["question_id"],
            "option_id": next(
                o for o in q["options"] if o["option_text"] == "opt0"
            )["option_id"],
        }
        for q in quiz["questions"]
    ]
    r = client.post(
        "/game/Python/submit",
        json={
            "quiz_id": quiz["quiz_id"],
            "difficulty": "easy",
            "answers": answers,
            "elapsed_seconds": -5,
        },
    )
    assert r.status_code == 422


def test_quiz_skills_is_cacheable(client, db_session):
    _seed_questions(db_session, n=1)
    assert "max-age" in client.get("/game/skills").headers["cache-control"]


def test_submit_reports_recorded_when_logged_in(client, db_session):
    _seed_questions(db_session, n=3)
    h = {"Authorization": f"Bearer {_token(client)}"}
    assert _play(client, "Python", "easy", headers=h).json()["recorded"] is True


def test_submit_reports_not_recorded_when_anonymous(client, db_session):
    """Anonymous play is graded but not saved, and now says so.

    A caller that forgot its Authorization header used to get a clean 200 and
    silently store nothing.
    """
    _seed_questions(db_session, n=3)
    body = _play(client, "Python", "easy").json()

    assert body["score"] == 3          # still graded
    assert body["recorded"] is False   # but not persisted


def test_submit_rejects_an_oversized_answer_list(client, db_session):
    """Bound the list before the exact-question-set check parses all of it."""
    _seed_questions(db_session, n=3)
    quiz = _fetch_quiz(client, "Python", "easy")
    answers = [{"question_id": 1, "option_id": 1} for _ in range(500)]
    r = client.post(
        "/game/Python/submit",
        json={
            "quiz_id": quiz["quiz_id"],
            "difficulty": "easy",
            "answers": answers,
        },
    )
    assert r.status_code == 422
