"""Metadata endpoint tests for frontend dropdown support."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app import models


def _add_role_with_postings(db, role_name: str, days_old: list[int]) -> models.Role:
    role = models.Role(role_name=role_name)
    db.add(role)
    db.flush()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for i, age in enumerate(days_old):
        db.add(
            models.JobPosting(
                external_id=f"{role_name}-{i}",
                role_id=role.role_id,
                title=f"{role_name} posting {i}",
                date_posted=now - timedelta(days=age),
            )
        )
    db.commit()
    return role


def test_roles_returns_only_roles_with_fresh_postings(client, db_session):
    _add_role_with_postings(db_session, "Data Analyst", [1, 2])
    _add_role_with_postings(db_session, "Stale Role", [45])

    r = client.get("/roles")

    assert r.status_code == 200
    assert [role["role_name"] for role in r.json()] == ["Data Analyst"]
    assert r.json()[0]["posting_count"] == 2


def test_roles_are_sorted_and_counts_ignore_stale_postings(client, db_session):
    _add_role_with_postings(db_session, "Software Engineer", [1, 45])
    _add_role_with_postings(db_session, "Cloud Security Engineer", [3, 4, 60])

    r = client.get("/roles")

    assert r.status_code == 200
    assert r.json() == [
        {
            "role_id": 2,
            "role_name": "Cloud Security Engineer",
            "posting_count": 2,
        },
        {
            "role_id": 1,
            "role_name": "Software Engineer",
            "posting_count": 1,
        },
    ]


# --- /locations --------------------------------------------------------------


def _add_posting(db, role, location, days_old, idx):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(
        models.JobPosting(
            external_id=f"{role.role_name}-loc-{idx}",
            role_id=role.role_id,
            title="posting",
            location=location,
            date_posted=now - timedelta(days=days_old),
        )
    )
    db.commit()


def test_locations_lists_only_fresh_postings(client, db_session):
    role = _add_role_with_postings(db_session, "Data Analyst", [])
    _add_posting(db_session, role, "Arlington, Virginia", 1, 1)
    _add_posting(db_session, role, "Stale City", 45, 2)

    r = client.get("/locations")

    assert r.status_code == 200
    assert [row["location"] for row in r.json()] == ["Arlington, Virginia"]


def test_locations_sorted_by_posting_count(client, db_session):
    role = _add_role_with_postings(db_session, "Software Engineer", [])
    _add_posting(db_session, role, "Remote", 1, 1)
    _add_posting(db_session, role, "Remote", 2, 2)
    _add_posting(db_session, role, "Austin, Texas", 1, 3)

    body = client.get("/locations").json()

    assert body[0] == {"location": "Remote", "posting_count": 2}
    assert body[1] == {"location": "Austin, Texas", "posting_count": 1}


def test_locations_skips_null_and_blank(client, db_session):
    role = _add_role_with_postings(db_session, "Cloud Engineer", [])
    _add_posting(db_session, role, None, 1, 1)
    _add_posting(db_session, role, "", 1, 2)
    _add_posting(db_session, role, "Denver, Colorado", 1, 3)

    assert [row["location"] for row in client.get("/locations").json()] == [
        "Denver, Colorado"
    ]


def test_reference_endpoints_are_cacheable(client, db_session):
    """Both dropdown sources are browser-cacheable; saves a request per view."""
    _add_role_with_postings(db_session, "Data Analyst", [1])

    assert "max-age" in client.get("/roles").headers["cache-control"]
    assert "max-age" in client.get("/locations").headers["cache-control"]
