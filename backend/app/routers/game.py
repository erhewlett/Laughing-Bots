"""Q&A game endpoints - questions by skill, difficulty by salary, scoring.

SCAFFOLD - contract is final, bodies are TODO.

Frontend contract:
  GET  /game/{skill_name}?desired_salary=90000   -> 200 GameQuestions
        questions WITHOUT is_correct flags (never send answers to the client!)
  POST /game/{skill_name}/submit                 -> 200 GameResult
        body: {answers: [{question_id, option_id}], desired_salary?}

skill_name uses a :path converter so skills that contain a slash (e.g. "CI/CD",
which is in the word-cloud vocabulary) route correctly. The exact skill string
from /wordcloud is passed straight through.

NOTE: game scoring is under review with the team (may drop salary difficulty
and weighting for a simple "X of N correct"). Bodies below are still stubs.

Difficulty design (proposed - uses existing schema, no ERD change):
  Question.points doubles as difficulty (1=easy, 2=medium, 3=hard).
  desired_salary buckets:   <70k -> points<=1,  70-110k -> <=2,  >110k -> all.
  Salary source: request param, falling back to the user's most recent
  Search.min_salary, falling back to "medium" - JSearch salaries are often
  null (verified), so never depend on posting salary alone.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import GameQuestions, GameResult, GameSubmission

router = APIRouter(prefix="/game", tags=["game"])


@router.get("/{skill_name:path}", response_model=GameQuestions)
def get_game(skill_name: str, desired_salary: int | None = None):
    # TODO(game):
    #   1. skill = db Skill by name (case-insensitive) -> 404 if missing
    #      (word cloud click sends the exact skill string from /wordcloud)
    #   2. bucket = _difficulty_bucket(desired_salary)  # see module docstring
    #   3. questions = Question where skill_id=... and points<=bucket,
    #      ORDER BY random(), LIMIT ~10, joined with options
    #   4. strip is_correct from options in the response schema
    #   5. 422 if the skill has no questions seeded yet
    raise HTTPException(501, "Not implemented yet - game milestone")


@router.post("/{skill_name:path}/submit", response_model=GameResult)
def submit_game(skill_name: str, submission: GameSubmission):
    # {skill_name:path} handles slash-containing skills like "CI/CD".
    # TODO(game):
    #   1. load submitted question_ids w/ options; validate they belong to skill
    #   2. score = sum(q.points for q where chosen option.is_correct)
    #      max_score = sum(q.points for all submitted questions)
    #   3. if authenticated: save GameAttempt(user, skill, score, max_score)
    #      (auth optional at first - anonymous play allowed, nothing saved)
    #   4. return {score, max_score, correct_count, results per question}
    #      NFR: must respond well within 7s - trivial, it's one DB roundtrip
    raise HTTPException(501, "Not implemented yet - game milestone")
