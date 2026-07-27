"""Tests for /me/recent and the wordcloud Search-persistence behavior."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app import models


def _token(client, username="hist"):
    client.post("/auth/register", json={"username": username, "password": "password123"})
    return client.post(
        "/auth/login", json={"username": username, "password": "password123"}
    ).json()["access_token"]


def _seed_cloud(db, role_name="Data Analyst"):
    """A role with recent postings so /wordcloud returns 200."""
    when = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
    role = models.Role(role_name=role_name)
    db.add(role)
    db.flush()
    skills = [models.Skill(skill_name="Python"), models.Skill(skill_name="SQL")]
    db.add_all(skills)
    db.flush()
    for i in range(3):
        p = models.JobPosting(
            external_id=f"{role_name}-{i}",
            role_id=role.role_id,
            title=f"{role_name} {i}",
            date_posted=when,
        )
        db.add(p)
        db.flush()
        for s, freq in zip(skills, (3, 2)):
            db.add(models.JobSkill(job_id=p.job_id, skill_id=s.skill_id, frequency=freq))
    db.commit()
    return role


def _seed_easy_questions(db, skill_name="Python", n=3):
    skill = models.Skill(skill_name=skill_name)
    db.add(skill)
    db.flush()
    for i in range(n):
        q = models.Question(skill_id=skill.skill_id, difficulty="easy", question_text=f"Q{i}")
        db.add(q)
        db.flush()
        for j in range(4):
            db.add(
                models.AnswerOption(
                    question_id=q.question_id, option_text=f"o{j}", is_correct=(j == 0)
                )
            )
    db.commit()


def test_recent_requires_auth(client):
    assert client.get("/me/recent").status_code == 401


def test_recent_empty_for_new_user(client, db_session):
    h = {"Authorization": f"Bearer {_token(client)}"}
    body = client.get("/me/recent", headers=h).json()
    assert body["last_game"] is None and body["recent_searches"] == []


def test_wordcloud_saves_search_when_logged_in(client, db_session):
    _seed_cloud(db_session)
    h = {"Authorization": f"Bearer {_token(client)}"}
    assert client.post("/wordcloud", json={"job_title": "Data Analyst"}, headers=h).status_code == 200
    searches = client.get("/me/recent", headers=h).json()["recent_searches"]
    assert len(searches) == 1 and searches[0]["job_title"] == "Data Analyst"


def test_recent_search_includes_min_salary(client, db_session):
    _seed_cloud(db_session)
    h = {"Authorization": f"Bearer {_token(client)}"}
    client.post("/wordcloud", json={"job_title": "Data Analyst", "min_salary": 90000}, headers=h)
    search = client.get("/me/recent", headers=h).json()["recent_searches"][0]
    assert search["min_salary"] == 90000  # salary filter is reproducible from history


def test_anonymous_wordcloud_is_rejected(client, db_session):
    """/wordcloud requires a user so every cloud lands in Recent Word Clouds.

    It used to return 200 anonymously and silently record nothing.
    """
    _seed_cloud(db_session)
    assert client.post("/wordcloud", json={"job_title": "Data Analyst"}).status_code == 401
    assert db_session.scalar(select(func.count()).select_from(models.Search)) == 0


def test_recent_searches_capped_at_five(client, db_session):
    _seed_cloud(db_session)
    h = {"Authorization": f"Bearer {_token(client)}"}
    for i in range(6):
        client.post("/wordcloud", json={"job_title": "Data Analyst", "word_count": 10 + i}, headers=h)
    assert len(client.get("/me/recent", headers=h).json()["recent_searches"]) == 5


def test_last_game_populated_after_play(client, db_session):
    _seed_easy_questions(db_session)
    h = {"Authorization": f"Bearer {_token(client)}"}
    quiz = client.get("/game/Python", params={"difficulty": "easy"}, headers=h).json()
    # options are shuffled; the seeded correct option's text is "o0"
    ans = [
        {
            "question_id": q["question_id"],
            "option_id": next(o for o in q["options"] if o["option_text"] == "o0")["option_id"],
        }
        for q in quiz["questions"]
    ]
    client.post(
        "/game/Python/submit",
        json={"quiz_id": quiz["quiz_id"], "difficulty": "easy", "answers": ans},
        headers=h,
    )
    last = client.get("/me/recent", headers=h).json()["last_game"]
    assert last is not None and last["skill"] == "Python" and last["score"] == 3
    assert last["difficulty"] == "easy"


# --- /me/games ---------------------------------------------------------------


def _play_quiz(
    client, headers, skill="Python", difficulty="easy", elapsed=None, wrong=0
):
    """Play one quiz to completion; make `wrong` of the answers incorrect."""
    quiz = client.get(
        f"/game/{skill}", params={"difficulty": difficulty}, headers=headers
    ).json()
    answers = [
        {
            "question_id": q["question_id"],
            "option_id": next(
                o
                for o in q["options"]
                if (o["option_text"] == "o0") == (i >= wrong)
            )["option_id"],
        }
        for i, q in enumerate(quiz["questions"])
    ]
    body = {
        "quiz_id": quiz["quiz_id"],
        "difficulty": difficulty,
        "answers": answers,
    }
    if elapsed is not None:
        body["elapsed_seconds"] = elapsed
    return client.post(f"/game/{skill}/submit", json=body, headers=headers)


def test_games_requires_auth(client):
    assert client.get("/me/games").status_code == 401


def test_games_empty_for_new_user(client, db_session):
    h = {"Authorization": f"Bearer {_token(client)}"}
    body = client.get("/me/games", headers=h).json()
    assert body["total_attempts"] == 0
    assert body["attempts"] == [] and body["bests"] == []
    assert body["mastered_skills"] == []


def test_games_records_attempt_with_totals(client, db_session):
    _seed_easy_questions(db_session, n=3)
    h = {"Authorization": f"Bearer {_token(client)}"}
    _play_quiz(client, h)

    body = client.get("/me/games", headers=h).json()

    assert body["total_attempts"] == 1
    assert body["total_correct"] == 3 and body["total_questions"] == 3
    item = body["attempts"][0]
    assert item["skill"] == "Python" and item["score"] == 3
    # a perfect 3/3 is 100%, so the normalized display score is the full 10000
    assert item["score_normalized"] == 10_000 and item["percentage"] == 100


def test_percentage_rounds_the_same_way_the_quiz_page_does(client, db_session):
    """Python's round() is banker's rounding, the quiz page uses Math.round.

    A 1-of-8 attempt lands exactly on 12.5, where round() gives 12 and
    Math.round gives 13, so history disagreed with the score the player was
    shown for the same attempt.
    """
    from app.routers.history import _round_half_up

    assert _round_half_up(12.5) == 13      # round(12.5) is 12
    assert _round_half_up(1 / 8 * 100) == 13
    # ordinary cases are unchanged
    assert _round_half_up(12.4) == 12
    assert _round_half_up(60.0) == 60
    assert _round_half_up(0.0) == 0


def test_games_percentage_matches_a_half_landing_attempt(client, db_session):
    """End to end: an 8-question bank puts 1 correct exactly on 12.5%."""
    _seed_easy_questions(db_session, n=8)
    h = {"Authorization": f"Bearer {_token(client)}"}
    _play_quiz(client, h, wrong=7)          # 1 of 8 correct

    item = client.get("/me/games", headers=h).json()["attempts"][0]
    assert item["score"] == 1 and item["max_score"] == 8
    assert item["percentage"] == 13         # not 12


def test_games_persists_elapsed_seconds(client, db_session):
    """The quiz page's timer value survives into history."""
    _seed_easy_questions(db_session, n=3)
    h = {"Authorization": f"Bearer {_token(client)}"}
    r = _play_quiz(client, h, elapsed=42)

    assert r.json()["elapsed_seconds"] == 42
    assert client.get("/me/games", headers=h).json()["attempts"][0][
        "elapsed_seconds"
    ] == 42


def test_games_elapsed_seconds_optional(client, db_session):
    """A client that omits the timer still submits and still records."""
    _seed_easy_questions(db_session, n=3)
    h = {"Authorization": f"Bearer {_token(client)}"}
    r = _play_quiz(client, h)

    assert r.status_code == 200 and r.json()["elapsed_seconds"] is None
    assert client.get("/me/games", headers=h).json()["attempts"][0][
        "elapsed_seconds"
    ] is None


def test_games_bests_group_by_skill_and_difficulty(client, db_session):
    _seed_easy_questions(db_session, n=3)
    h = {"Authorization": f"Bearer {_token(client)}"}
    _play_quiz(client, h)
    _play_quiz(client, h)

    bests = client.get("/me/games", headers=h).json()["bests"]

    assert len(bests) == 1
    assert bests[0]["skill"] == "Python" and bests[0]["attempts"] == 2
    assert bests[0]["best_score"] == 3


def test_games_only_returns_own_attempts(client, db_session):
    _seed_easy_questions(db_session, n=3)
    # usernames are alphanumeric-only per the register schema
    mine = {"Authorization": f"Bearer {_token(client, 'playerA')}"}
    theirs = {"Authorization": f"Bearer {_token(client, 'playerB')}"}
    _play_quiz(client, mine)

    assert client.get("/me/games", headers=theirs).json()["total_attempts"] == 0
    assert client.get("/me/games", headers=mine).json()["total_attempts"] == 1


def test_games_limit_is_bounded(client, db_session):
    h = {"Authorization": f"Bearer {_token(client)}"}
    assert client.get("/me/games", params={"limit": 0}, headers=h).status_code == 422
    assert client.get("/me/games", params={"limit": 500}, headers=h).status_code == 422


def test_recent_includes_identity(client, db_session):
    """Lets the user info page drop its separate GET /auth/me call."""
    h = {"Authorization": f"Bearer {_token(client, 'identity')}"}
    body = client.get("/me/recent", headers=h).json()

    assert body["username"] == "identity"


def test_games_best_pair_comes_from_one_attempt(client, db_session):
    """best_score/max_score must describe a single real attempt.

    Taking MAX(score) and MAX(max_score) independently reported "5/10" for a
    player whose attempts were 3/3 and 5/10, a ratio nobody scored.
    """
    h = {"Authorization": f"Bearer {_token(client, 'pairs')}"}
    uid = client.get("/auth/me", headers=h).json()["user_id"]
    skill = models.Skill(skill_name="Python")
    db_session.add(skill)
    db_session.flush()
    for score, max_score in ((3, 3), (5, 10)):
        db_session.add(
            models.GameAttempt(
                user_id=uid,
                skill_id=skill.skill_id,
                difficulty="hard",
                score=score,
                max_score=max_score,
            )
        )
    db_session.commit()

    best = client.get("/me/games", headers=h).json()["bests"][0]

    # 3/3 is the better ratio, so that is the pair reported
    assert (best["best_score"], best["max_score"]) == (3, 3)
    assert best["attempts"] == 2


def test_games_mastery_survives_a_later_short_quiz(client, db_session):
    """A perfect full hard quiz still counts as mastered.

    Ratio ties are broken toward the longer quiz so a later perfect 3/3 cannot
    hide an earlier perfect 10/10.
    """
    h = {"Authorization": f"Bearer {_token(client, 'master')}"}
    uid = client.get("/auth/me", headers=h).json()["user_id"]
    skill = models.Skill(skill_name="Python")
    db_session.add(skill)
    db_session.flush()
    for score, max_score in ((10, 10), (3, 3)):
        db_session.add(
            models.GameAttempt(
                user_id=uid,
                skill_id=skill.skill_id,
                difficulty="hard",
                score=score,
                max_score=max_score,
            )
        )
    db_session.commit()

    body = client.get("/me/games", headers=h).json()

    assert body["mastered_skills"] == ["Python"]
