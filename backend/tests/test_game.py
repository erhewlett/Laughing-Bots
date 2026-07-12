"""Q&A game endpoint tests.

Covers: question serving (10-cap, no answers leaked, difficulty filter, slash
skills), scoring, the mastery flag, validation, and the anonymous-vs-logged-in
save behavior.
"""
from __future__ import annotations

from sqlalchemy import func, select

from app import models


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


def _play(client, skill, difficulty, *, headers=None, wrong=0):
    """Fetch a quiz and submit; make `wrong` of the answers incorrect."""
    qs = client.get(f"/game/{skill}", params={"difficulty": difficulty}).json()["questions"]
    answers = []
    for i, q in enumerate(qs):
        opt = q["options"][1] if i < wrong else q["options"][0]  # option[0] is correct
        answers.append({"question_id": q["question_id"], "option_id": opt["option_id"]})
    return client.post(
        f"/game/{skill}/submit",
        json={"difficulty": difficulty, "answers": answers},
        headers=headers or {},
    )


def _token(client, username="player"):
    client.post("/auth/register", json={"username": username, "password": "password123"})
    return client.post(
        "/auth/login", json={"username": username, "password": "password123"}
    ).json()["access_token"]


# --- serving questions -------------------------------------------------------

def test_get_returns_questions_without_answers(client, db_session):
    _seed_questions(db_session, n=10)
    r = client.get("/game/Python", params={"difficulty": "easy"})
    assert r.status_code == 200
    body = r.json()
    assert body["skill"] == "Python" and body["difficulty"] == "easy"
    assert len(body["questions"]) == 10
    assert "is_correct" not in str(body)  # answers never leak to the client


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

def test_submit_foreign_question_422(client, db_session):
    _seed_questions(db_session)
    r = client.post(
        "/game/Python/submit",
        json={"difficulty": "easy", "answers": [{"question_id": 99999, "option_id": 1}]},
    )
    assert r.status_code == 422


def test_submit_difficulty_mismatch_422(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=5)
    # claim "hard" while submitting easy questions
    assert _play(client, "Python", "easy", wrong=0).status_code == 200
    r = client.get("/game/Python", params={"difficulty": "easy"}).json()
    answers = [{"question_id": q["question_id"], "option_id": q["options"][0]["option_id"]} for q in r["questions"]]
    mismatch = client.post("/game/Python/submit", json={"difficulty": "hard", "answers": answers})
    assert mismatch.status_code == 422


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
