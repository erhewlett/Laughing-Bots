"""Post-login history - "most recent game keyword and score" + "most recent
word clouds" (both are explicit functional requirements).

SCAFFOLD - contract is final, bodies are TODO.

Frontend contract (requires auth):
  GET /me/recent -> 200 {
      last_game:   {skill, score, max_score, date_taken} | null,
      recent_searches: [ {search_id, job_title, industry, location,
                          word_count, shape, created_at}, ... up to 5 ]
  }

Depends on: /wordcloud persisting a Search row for logged-in users
(add once auth lands - see wordcloud.py TODO).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import RecentActivity

router = APIRouter(prefix="/me", tags=["history"])


@router.get("/recent", response_model=RecentActivity)
def recent_activity():
    # TODO(history):
    #   1. user = Depends(get_current_user)
    #   2. last_game = GameAttempt for user, order date_taken desc, limit 1
    #   3. recent_searches = Search for user, order created_at desc, limit 5
    #   4. re-running a recent word cloud = frontend POSTs /wordcloud again
    #      with the saved parameters (no need to store the rendered cloud)
    raise HTTPException(501, "Not implemented yet - history milestone")
