"""Tests for the roadmap endpoints."""
from __future__ import annotations

from sqlalchemy import select

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


def test_patch_step_not_owner_403(client, db_session):
    _seed_role(db_session)
    ta = {"Authorization": f"Bearer {_token(client, 'alice')}"}
    step_id = _create(client, ta).json()["steps"][0]["step_id"]
    tb = {"Authorization": f"Bearer {_token(client, 'bobby')}"}
    assert client.patch(f"/roadmap/steps/{step_id}", json={"status": "completed"}, headers=tb).status_code == 403
