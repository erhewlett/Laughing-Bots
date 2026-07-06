"""Roadmap endpoints - personalized prep roadmap from role demand.

SCAFFOLD - contract is final, bodies are TODO.

Frontend contract (all require auth):
  POST  /roadmap                {role_name}     -> 201 RoadmapOut
  GET   /roadmap                                -> 200 latest RoadmapOut for user
  PATCH /roadmap/steps/{step_id} {status}       -> 200 updated step

Generation design:
  Steps = the role's skills ordered by RoleSkill.demand_score desc (top ~8).
  This is where the RoleSkill aggregate actually earns its keep (the word
  cloud computes document frequency live from JobSkill instead).
  status: "not_started" | "in_progress" | "completed" (validated by schema).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import RoadmapCreate, RoadmapOut, StepStatusUpdate

router = APIRouter(prefix="/roadmap", tags=["roadmap"])


@router.post("", response_model=RoadmapOut, status_code=201)
def create_roadmap(req: RoadmapCreate):
    # TODO(roadmap):
    #   1. user = Depends(get_current_user)
    #   2. role by name -> 404 if missing
    #   3. top skills: RoleSkill where role_id, order by demand_score desc, limit 8
    #   4. create Roadmap + RoadmapStep rows (step_order = rank, status default)
    #   5. return with steps joined
    raise HTTPException(501, "Not implemented yet - roadmap milestone")


@router.get("", response_model=RoadmapOut)
def get_my_roadmap():
    # TODO(roadmap): latest Roadmap for current user (order created_date desc),
    #   404 if none yet
    raise HTTPException(501, "Not implemented yet - roadmap milestone")


@router.patch("/steps/{step_id}")
def update_step(step_id: int, req: StepStatusUpdate):
    # TODO(roadmap): verify step belongs to current user's roadmap (403 else),
    #   set status, commit
    raise HTTPException(501, "Not implemented yet - roadmap milestone")
