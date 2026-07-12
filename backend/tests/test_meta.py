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
