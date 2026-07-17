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


def test_anonymous_wordcloud_saves_no_search(client, db_session):
    _seed_cloud(db_session)
    assert client.post("/wordcloud", json={"job_title": "Data Analyst"}).status_code == 200
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
