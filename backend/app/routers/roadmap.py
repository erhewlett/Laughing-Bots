"""Roadmap endpoints: build and track a prep roadmap from a role's skill demand.

  POST  /roadmap                {role_name}  -> 201 RoadmapOut (top-8 skills as steps)
  GET   /roadmap                             -> 200 the user's latest roadmap
  PATCH /roadmap/steps/{step_id} {status}    -> 200 the updated step

All require a Bearer token. Steps come from RoleSkill.demand_score (built from
the word-cloud data), so the roadmap is "learn the most in-demand skills first".
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.schemas import RoadmapCreate, RoadmapOut, RoadmapStepOut, StepStatusUpdate
from app.services import security

router = APIRouter(prefix="/roadmap", tags=["roadmap"])

ROADMAP_STEPS = 8


def _step_out(step: models.RoadmapStep) -> RoadmapStepOut:
    return RoadmapStepOut(
        step_id=step.step_id,
        skill=step.skill.skill_name,
        step_order=step.step_order,
        status=step.status,
    )


def _roadmap_out(roadmap: models.Roadmap) -> RoadmapOut:
    steps = sorted(roadmap.steps, key=lambda s: s.step_order)
    return RoadmapOut(
        roadmap_id=roadmap.roadmap_id,
        role=roadmap.role.role_name if roadmap.role else "",
        created_date=roadmap.created_date,
        steps=[_step_out(s) for s in steps],
    )


@router.post("", response_model=RoadmapOut, status_code=status.HTTP_201_CREATED)
def create_roadmap(
    req: RoadmapCreate,
    user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
) -> RoadmapOut:
    role = db.scalar(
        select(models.Role).where(
            func.lower(models.Role.role_name) == req.role_name.lower()
        )
    )
    if role is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Unknown role: {req.role_name}"
        )

    top = db.scalars(
        select(models.RoleSkill.skill_id)
        .where(models.RoleSkill.role_id == role.role_id)
        .order_by(
            models.RoleSkill.demand_score.desc(), models.RoleSkill.skill_id
        )
        .limit(ROADMAP_STEPS)
    ).all()
    if not top:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "That role has no skills to build a roadmap from.",
        )

    roadmap = models.Roadmap(user_id=user.user_id, role_id=role.role_id)
    db.add(roadmap)
    db.flush()
    for order, skill_id in enumerate(top, start=1):
        db.add(
            models.RoadmapStep(
                roadmap_id=roadmap.roadmap_id, skill_id=skill_id, step_order=order
            )
        )
    db.commit()
    db.refresh(roadmap)
    return _roadmap_out(roadmap)


@router.get("", response_model=RoadmapOut)
def get_my_roadmap(
    user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
) -> RoadmapOut:
    roadmap = db.scalar(
        select(models.Roadmap)
        .where(models.Roadmap.user_id == user.user_id)
        .order_by(
            models.Roadmap.created_date.desc(), models.Roadmap.roadmap_id.desc()
        )
        .limit(1)
    )
    if roadmap is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No roadmap yet.")
    return _roadmap_out(roadmap)


@router.patch("/steps/{step_id}", response_model=RoadmapStepOut)
def update_step(
    step_id: int,
    req: StepStatusUpdate,
    user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
) -> RoadmapStepOut:
    step = db.get(models.RoadmapStep, step_id)
    if step is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Step not found.")
    if step.roadmap.user_id != user.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your roadmap.")
    step.status = req.status
    db.commit()
    db.refresh(step)
    return _step_out(step)
