"""GET /postings tests.

The endpoint's whole job is to be the evidence behind a word cloud, so most of
what is worth testing is that it agrees with POST /wordcloud: same role
resolution, same 30-day rule, same location and salary filters. Where it is
allowed to differ from the cloud (the reported total) there is a test saying so
on purpose.
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
    locations=None,
    salaries=None,
):
    """Insert one role with n postings, each carrying the given skills."""
    skills = skills or {"Python": 3, "SQL": 2}
    when = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_old)

    role = models.Role(role_name=role_name)
    db.add(role)
    db.flush()

    # skills.skill_name is unique, so reuse any the caller already seeded -
    # the ambiguous-role test seeds two roles that share a skill set.
    skill_objs = {}
    for name in skills:
        existing = db.scalar(
            select(models.Skill).where(models.Skill.skill_name == name)
        )
        if existing is None:
            existing = models.Skill(skill_name=name)
            db.add(existing)
        skill_objs[name] = existing
    db.flush()

    for i in range(n_postings):
        low, high = (salaries[i] if salaries and i < len(salaries) else (None, None))
        p = models.JobPosting(
            external_id=f"{role_name}-{i}",
            role_id=role.role_id,
            title=f"{role_name} {i}",
            company_name=f"Company {i}",
            location=(locations[i] if locations and i < len(locations) else "Remote"),
            salary_min=low,
            salary_max=high,
            source_url=f"https://example.test/jobs/{i}",
            # Stagger the dates so "newest first" has something to order by.
            date_posted=when - timedelta(hours=i),
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


def test_returns_postings_for_a_role(client, db_session, auth_headers):
    _seed(db_session, n_postings=3)

    r = client.get("/postings", params={"job_title": "Data Analyst"}, headers=auth_headers)

    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "Data Analyst"
    assert body["total"] == 3
    assert len(body["postings"]) == 3
    first = body["postings"][0]
    # The fields the page actually renders.
    assert first["title"]
    assert first["company_name"]
    assert first["location"]
    assert first["source_url"].startswith("https://")


def test_requires_authentication(client, db_session):
    _seed(db_session)
    r = client.get("/postings", params={"job_title": "Data Analyst"})
    assert r.status_code == 401


def test_requires_a_search_term(client, db_session, auth_headers):
    _seed(db_session)
    r = client.get("/postings", headers=auth_headers)
    assert r.status_code == 422
    # Flattened to a string like every other error the API returns.
    assert isinstance(r.json()["detail"], str)


def test_unknown_role_is_404(client, db_session, auth_headers):
    _seed(db_session)
    r = client.get(
        "/postings", params={"job_title": "Underwater Basket Weaver"}, headers=auth_headers
    )
    assert r.status_code == 404


def test_ambiguous_role_is_409_like_the_cloud(client, db_session, auth_headers):
    """Same 409 the cloud raises, rather than quietly picking one role."""
    _seed(db_session, role_name="Data Engineer")
    _seed(db_session, role_name="Software Engineer")

    r = client.get("/postings", params={"job_title": "Engineer"}, headers=auth_headers)

    assert r.status_code == 409


def test_newest_first(client, db_session, auth_headers):
    _seed(db_session, n_postings=4)

    body = client.get(
        "/postings", params={"job_title": "Data Analyst"}, headers=auth_headers
    ).json()

    dates = [p["date_posted"] for p in body["postings"]]
    assert dates == sorted(dates, reverse=True)


def test_limit_caps_the_list_but_not_the_total(client, db_session, auth_headers):
    _seed(db_session, n_postings=6)

    body = client.get(
        "/postings", params={"job_title": "Data Analyst", "limit": 2}, headers=auth_headers
    ).json()

    assert len(body["postings"]) == 2
    # total describes the search, so the page can say "showing 2 of 6".
    assert body["total"] == 6


def test_limit_is_bounded(client, db_session, auth_headers):
    _seed(db_session)
    for bad in (0, 51, -1):
        r = client.get(
            "/postings",
            params={"job_title": "Data Analyst", "limit": bad},
            headers=auth_headers,
        )
        assert r.status_code == 422, bad


def test_excludes_postings_older_than_thirty_days(client, db_session, auth_headers):
    """The 30-day rule the cloud enforces, enforced here too.

    Otherwise the list would show postings that contributed nothing to the
    cloud sitting right above it.
    """
    _seed(db_session, n_postings=2, days_old=45)

    r = client.get("/postings", params={"job_title": "Data Analyst"}, headers=auth_headers)

    assert r.status_code == 200
    assert r.json()["total"] == 0
    assert r.json()["postings"] == []


def test_filters_by_location(client, db_session, auth_headers):
    _seed(
        db_session,
        n_postings=3,
        locations=["Arlington, Virginia", "Bethesda, Maryland", "Arlington, Virginia"],
    )

    body = client.get(
        "/postings",
        params={"job_title": "Data Analyst", "location": "Arlington"},
        headers=auth_headers,
    ).json()

    assert body["total"] == 2
    assert all("Arlington" in p["location"] for p in body["postings"])


def test_min_salary_keeps_unknown_salary_postings(client, db_session, auth_headers):
    """Matches the cloud's filter, which keeps unknown salaries rather than
    starving the result - most scraped postings have no salary at all."""
    _seed(
        db_session,
        n_postings=3,
        salaries=[(50_000, 60_000), (120_000, 150_000), (None, None)],
    )

    body = client.get(
        "/postings",
        params={"job_title": "Data Analyst", "min_salary": 100_000},
        headers=auth_headers,
    ).json()

    kept = {p["salary_min"] for p in body["postings"]}
    assert 120_000 in kept       # clears the floor
    assert None in kept          # unknown, kept
    assert 50_000 not in kept    # known to fall short


def test_matches_the_role_the_cloud_resolved(client, db_session, auth_headers):
    """Both endpoints run the same search terms through the same resolver."""
    _seed(db_session, n_postings=3)
    params = {"job_title": "Data Analyst", "location": "Remote"}

    cloud = client.post("/wordcloud", json=params, headers=auth_headers).json()
    postings = client.get("/postings", params=params, headers=auth_headers).json()

    assert postings["role"] == cloud["role"]


def test_literal_percent_in_location_is_not_a_wildcard(client, db_session, auth_headers):
    """Same LIKE-escaping the cloud does; '%' must not match everything."""
    _seed(db_session, n_postings=2, locations=["Arlington, Virginia", "Remote"])

    body = client.get(
        "/postings",
        params={"job_title": "Data Analyst", "location": "%"},
        headers=auth_headers,
    ).json()

    assert body["total"] == 0
