"""Tests for the roadmap endpoints."""
from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app import models


def _token(client, username="road"):
    client.post("/auth/register", json={"username": username, "password": "password123"})
    return client.post(
        "/auth/login", json={"username": username, "password": "password123"}
    ).json()["access_token"]


def _seed_role(db, role_name="Data Analyst", demands=None):
    demands = demands or {"Python": 10.0, "SQL": 8.0, "AWS": 3.0}
    role = models.Role(role_name=role_name)
    db.add(role)
    db.flush()
    for name, demand in demands.items():
        skill = db.scalar(select(models.Skill).where(models.Skill.skill_name == name))
        if skill is None:
            skill = models.Skill(skill_name=name)
            db.add(skill)
            db.flush()
        db.add(
            models.RoleSkill(
                role_id=role.role_id, skill_id=skill.skill_id, demand_score=demand
            )
        )
    db.commit()
    return role


def _create(client, headers, role_name="Data Analyst"):
    return client.post("/roadmap", json={"role_name": role_name}, headers=headers)


def test_create_requires_auth(client):
    assert client.post("/roadmap", json={"role_name": "Data Analyst"}).status_code == 401


def test_create_roadmap_steps_ordered_by_demand(client, db_session):
    _seed_role(db_session)
    h = {"Authorization": f"Bearer {_token(client)}"}
    r = _create(client, h)
    assert r.status_code == 201
    body = r.json()
    assert body["role"] == "Data Analyst"
    assert [s["skill"] for s in body["steps"]] == ["Python", "SQL", "AWS"]
    assert [s["step_order"] for s in body["steps"]] == [1, 2, 3]
    assert all(s["status"] == "not_started" for s in body["steps"])


def test_create_unknown_role_404(client, db_session):
    h = {"Authorization": f"Bearer {_token(client)}"}
    assert _create(client, h, role_name="Nonsense").status_code == 404


def test_create_role_without_skills_422(client, db_session):
    db_session.add(models.Role(role_name="Empty Role"))
    db_session.commit()
    h = {"Authorization": f"Bearer {_token(client)}"}
    assert _create(client, h, role_name="Empty Role").status_code == 422


def test_create_replaces_previous_roadmap(client, db_session):
    _seed_role(db_session)
    _seed_role(db_session, role_name="Frontend Developer", demands={"React": 9.0})
    h = {"Authorization": f"Bearer {_token(client)}"}
    first = _create(client, h).json()
    assert len(first["steps"]) == 3  # Python, SQL, AWS

    assert _create(client, h, role_name="Frontend Developer").status_code == 201
    # exactly one roadmap remains, and it is the new one
    assert db_session.scalar(select(func.count()).select_from(models.Roadmap)) == 1
    body = client.get("/roadmap", headers=h).json()
    assert body["role"] == "Frontend Developer"
    # the replaced roadmap's steps are gone; only the new single step remains
    # (SQLite reuses ids, so assert on row counts and content, not old ids)
    assert db_session.scalar(select(func.count()).select_from(models.RoadmapStep)) == 1
    assert [s["skill"] for s in body["steps"]] == ["React"]


def test_database_enforces_one_roadmap_per_user(client, db_session):
    _seed_role(db_session)
    h = {"Authorization": f"Bearer {_token(client)}"}
    created = _create(client, h).json()
    roadmap = db_session.get(models.Roadmap, created["roadmap_id"])
    db_session.add(
        models.Roadmap(user_id=roadmap.user_id, role_id=roadmap.role_id)
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_get_returns_latest_roadmap(client, db_session):
    _seed_role(db_session)
    h = {"Authorization": f"Bearer {_token(client)}"}
    _create(client, h)
    r = client.get("/roadmap", headers=h)
    assert r.status_code == 200 and r.json()["role"] == "Data Analyst"


def test_get_no_roadmap_404(client, db_session):
    h = {"Authorization": f"Bearer {_token(client)}"}
    assert client.get("/roadmap", headers=h).status_code == 404


def test_patch_step_status(client, db_session):
    _seed_role(db_session)
    h = {"Authorization": f"Bearer {_token(client)}"}
    step_id = _create(client, h).json()["steps"][0]["step_id"]
    r = client.patch(f"/roadmap/steps/{step_id}", json={"status": "completed"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "completed"


def test_patch_step_bad_status_422(client, db_session):
    _seed_role(db_session)
    h = {"Authorization": f"Bearer {_token(client)}"}
    step_id = _create(client, h).json()["steps"][0]["step_id"]
    assert client.patch(f"/roadmap/steps/{step_id}", json={"status": "done"}, headers=h).status_code == 422


def test_patch_step_not_owner_404(client, db_session):
    """Another user's step must be indistinguishable from a missing one.

    A 403 here and a 404 for an unknown id let anyone walk the sequential step
    ids and learn which ones exist on other people's roadmaps.
    """
    _seed_role(db_session)
    ta = {"Authorization": f"Bearer {_token(client, 'alice')}"}
    step_id = _create(client, ta).json()["steps"][0]["step_id"]
    tb = {"Authorization": f"Bearer {_token(client, 'bobby')}"}

    foreign = client.patch(
        f"/roadmap/steps/{step_id}", json={"status": "completed"}, headers=tb
    )
    missing = client.patch(
        "/roadmap/steps/999999", json={"status": "completed"}, headers=tb
    )

    assert foreign.status_code == 404
    # same status AND same body, so the response itself leaks nothing
    assert foreign.json() == missing.json()
