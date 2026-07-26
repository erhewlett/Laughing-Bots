"""Word cloud endpoint tests.

Covers the functional requirements plus the review findings: job-title vs
posting-title matching, the 30-day filter, literal % / _ inputs, slash skills
like CI/CD, deterministic weighting, and word_count limits.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

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


def test_requires_auth(client, db_session):
    _seed(db_session)
    # The cloud is a per-user feature: it records a search against the caller.
    assert client.post("/wordcloud", json={"job_title": "Data Analyst"}).status_code == 401


def test_requires_title_or_industry(client, auth_headers):
    r = client.post("/wordcloud", json={"word_count": 5}, headers=auth_headers)
    assert r.status_code == 422


def test_unknown_role_404(client, db_session, auth_headers):
    _seed(db_session)
    r = client.post(
        "/wordcloud", json={"job_title": "Underwater Basket Weaver"}, headers=auth_headers
    )
    assert r.status_code == 404


def test_happy_path_weights_normalized(client, db_session, auth_headers):
    _seed(db_session, skills={"Python": 4, "SQL": 2, "AWS": 1})
    r = client.post(
        "/wordcloud",
        json={"job_title": "Data Analyst", "word_count": 5},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "Data Analyst"
    assert body["words"][0]["weight"] == 100  # top skill normalized to 100


def test_word_count_respected(client, db_session, auth_headers):
    # 7 skills available, ask for 5 (the schema minimum); expect exactly 5.
    _seed(
        db_session,
        skills={"Python": 7, "SQL": 6, "AWS": 5, "React": 4, "Java": 3, "Go": 2, "C++": 1},
    )
    r = client.post(
        "/wordcloud",
        json={"job_title": "Data Analyst", "word_count": 5},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert len(r.json()["words"]) == 5
    # the requested word_count is echoed back so the render page can use it
    assert r.json()["word_count"] == 5


def test_shape_echoed(client, db_session, auth_headers):
    _seed(db_session)
    r = client.post(
        "/wordcloud",
        json={"job_title": "Data Analyst", "shape": "hexagon"},
        headers=auth_headers,
    )
    assert r.json()["shape"] == "hexagon"


def test_shape_rejects_markup(client, auth_headers):
    r = client.post(
        "/wordcloud",
        json={"job_title": "Data Analyst", "shape": "<script>"},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_literal_percent_does_not_match_everything(client, db_session, auth_headers):
    _seed(db_session)
    # "%" is escaped, so it must not act as a wildcard matching the role.
    r = client.post("/wordcloud", json={"job_title": "%"}, headers=auth_headers)
    assert r.status_code == 404


def test_30_day_filter_excludes_stale(client, db_session, auth_headers):
    _seed(db_session, days_old=45)  # every posting older than 30 days
    r = client.post("/wordcloud", json={"job_title": "Data Analyst"}, headers=auth_headers)
    assert r.status_code == 422  # nothing fresh -> not enough data


def test_job_title_resolves_via_posting_title(client, db_session, auth_headers):
    _seed(
        db_session,
        role_name="Frontend Developer",
        n_postings=3,
        titles=["Front End Software Engineer"] * 3,
        skills={"React": 3, "JavaScript": 2},
    )
    r = client.post(
        "/wordcloud",
        json={"job_title": "Front End Software Engineer"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["role"] == "Frontend Developer"


def test_incidental_word_does_not_hijack_role(client, db_session, auth_headers):
    """A stray word in a single posting title must not resolve the search.

    "Marketing" appearing once in a Frontend Developer posting used to return
    a full frontend-engineering cloud as though it were a marketing result.
    """
    _seed(
        db_session,
        role_name="Frontend Developer",
        n_postings=3,
        titles=["Front-End Web Developer, B2B, Marketing Technology", "Dev 2", "Dev 3"],
        skills={"React": 3, "JavaScript": 2},
    )
    r = client.post("/wordcloud", json={"industry": "Marketing"}, headers=auth_headers)
    assert r.status_code == 404


def test_ambiguous_role_term_reports_candidates(client, db_session, auth_headers):
    """"Engineer" matches two roles; picking one alphabetically was misleading."""
    _seed(db_session, role_name="Software Engineer", skills={"Python": 2})
    _seed(db_session, role_name="Cloud Security Engineer", skills={"AWS": 2})
    r = client.post("/wordcloud", json={"job_title": "Engineer"}, headers=auth_headers)
    assert r.status_code == 409
    assert "Software Engineer" in r.json()["detail"]
    assert "Cloud Security Engineer" in r.json()["detail"]


def test_posting_count_excludes_unknown_salary(client, db_session, auth_headers):
    """Postings with no salary still feed the cloud but are not counted as matches."""
    _seed(db_session, n_postings=3, skills={"Python": 2})  # salaries left NULL
    r = client.post(
        "/wordcloud",
        json={"job_title": "Data Analyst", "min_salary": 999_999},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["words"]          # cloud still rendered
    assert r.json()["posting_count"] == 0  # but nothing verifiably matched


def test_oversized_min_salary_is_rejected_not_500(client, db_session, auth_headers):
    _seed(db_session)
    r = client.post(
        "/wordcloud",
        json={"job_title": "Data Analyst", "min_salary": 2**63},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_slash_skill_appears(client, db_session, auth_headers):
    _seed(db_session, skills={"CI/CD": 3, "Python": 1})
    names = [w["skill"] for w in client.post(
        "/wordcloud", json={"job_title": "Data Analyst"}, headers=auth_headers
    ).json()["words"]]
    assert "CI/CD" in names

# CI trigger for scenario 3 and 4 evidence


def test_words_flag_playable_skills(client, db_session, auth_headers):
    """Each word says whether it can start a quiz.

    Lets the cloud page decide what is clickable from this one response instead
    of also calling GET /game/skills.
    """
    _seed(db_session)  # Python + SQL on recent Data Analyst postings
    skill = db_session.scalar(
        select(models.Skill).where(models.Skill.skill_name == "Python")
    )
    q = models.Question(
        skill_id=skill.skill_id, difficulty="easy", question_text="Q"
    )
    db_session.add(q)
    db_session.flush()
    db_session.add(
        models.AnswerOption(question_id=q.question_id, option_text="a", is_correct=True)
    )
    db_session.commit()

    words = client.post(
        "/wordcloud", json={"job_title": "Data Analyst"}, headers=auth_headers
    ).json()["words"]
    by_skill = {w["skill"]: w["playable"] for w in words}

    assert by_skill["Python"] is True    # has a question
    assert by_skill["SQL"] is False      # no questions seeded


def test_response_includes_username(client, db_session, auth_headers):
    """Saves the cloud page a blocking GET /auth/me before it can render."""
    _seed(db_session)
    body = client.post(
        "/wordcloud", json={"job_title": "Data Analyst"}, headers=auth_headers
    ).json()

    assert body["username"] == "tester1"
