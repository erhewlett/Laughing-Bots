"""Word cloud endpoint tests.

Covers the functional requirements plus the review findings: job-title vs
posting-title matching, the 30-day filter, literal % / _ inputs, slash skills
like CI/CD, deterministic weighting, and word_count limits.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app import models
from app.services.ingest import _rebuild_role_skill


def _seed(
    db,
    *,
    role_name="Data Analyst",
    n_postings=5,
    skills=None,
    days_old=1,
    titles=None,
):
    """Insert one role with n postings, each carrying the given skills."""
    skills = skills or {"Python": 3, "SQL": 2}
    when = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_old)

    role = models.Role(role_name=role_name)
    db.add(role)
    db.flush()

    skill_objs = {}
    for name in skills:
        s = models.Skill(skill_name=name)
        db.add(s)
        skill_objs[name] = s
    db.flush()

    for i in range(n_postings):
        title = titles[i] if titles and i < len(titles) else f"{role_name} {i}"
        p = models.JobPosting(
            external_id=f"{role_name}-{i}",
            role_id=role.role_id,
            title=title,
            date_posted=when,
        )
        db.add(p)
        db.flush()
        for name, freq in skills.items():
            db.add(
                models.JobSkill(
                    job_id=p.job_id, skill_id=skill_objs[name].skill_id, frequency=freq
                )
            )
    db.flush()
    _rebuild_role_skill(db, role.role_id)
    db.commit()
    return role


def test_requires_title_or_industry(client):
    assert client.post("/wordcloud", json={"word_count": 5}).status_code == 422


def test_unknown_role_404(client, db_session):
    _seed(db_session)
    r = client.post("/wordcloud", json={"job_title": "Underwater Basket Weaver"})
    assert r.status_code == 404


def test_happy_path_weights_normalized(client, db_session):
    _seed(db_session, skills={"Python": 4, "SQL": 2, "AWS": 1})
    r = client.post("/wordcloud", json={"job_title": "Data Analyst", "word_count": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "Data Analyst"
    assert body["words"][0]["weight"] == 100  # top skill normalized to 100


def test_word_count_respected(client, db_session):
    # 7 skills available, ask for 5 (the schema minimum); expect exactly 5.
    _seed(
        db_session,
        skills={"Python": 7, "SQL": 6, "AWS": 5, "React": 4, "Java": 3, "Go": 2, "C++": 1},
    )
    r = client.post("/wordcloud", json={"job_title": "Data Analyst", "word_count": 5})
    assert r.status_code == 200
    assert len(r.json()["words"]) == 5


def test_shape_echoed(client, db_session):
    _seed(db_session)
    r = client.post("/wordcloud", json={"job_title": "Data Analyst", "shape": "hexagon"})
    assert r.json()["shape"] == "hexagon"


def test_shape_rejects_markup(client):
    r = client.post("/wordcloud", json={"job_title": "Data Analyst", "shape": "<script>"})
    assert r.status_code == 422


def test_literal_percent_does_not_match_everything(client, db_session):
    _seed(db_session)
    # "%" is escaped, so it must not act as a wildcard matching the role.
    assert client.post("/wordcloud", json={"job_title": "%"}).status_code == 404


def test_30_day_filter_excludes_stale(client, db_session):
    _seed(db_session, days_old=45)  # every posting older than 30 days
    r = client.post("/wordcloud", json={"job_title": "Data Analyst"})
    assert r.status_code == 422  # nothing fresh -> not enough data


def test_job_title_resolves_via_posting_title(client, db_session):
    _seed(
        db_session,
        role_name="Frontend Developer",
        n_postings=3,
        titles=["Front End Software Engineer"] * 3,
        skills={"React": 3, "JavaScript": 2},
    )
    r = client.post("/wordcloud", json={"job_title": "Front End Software Engineer"})
    assert r.status_code == 200
    assert r.json()["role"] == "Frontend Developer"


def test_slash_skill_appears(client, db_session):
    _seed(db_session, skills={"CI/CD": 3, "Python": 1})
    names = [w["skill"] for w in client.post(
        "/wordcloud", json={"job_title": "Data Analyst"}
    ).json()["words"]]
    assert "CI/CD" in names
