"""Pydantic request/response models for the API."""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class SearchRequest(BaseModel):
    """User's job-search parameters for generating a word cloud."""

    job_title: str | None = Field(default=None, max_length=150)
    industry: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=100)
    min_salary: int | None = Field(default=None, ge=0)
    word_count: int = Field(default=30, ge=5, le=100)
    # Alphanumeric-only (review #9): shape comes from a frontend dropdown, so
    # junk/markup can't flow through and get echoed back. Convert to a
    # Literal[...] once the frontend finalizes its dropdown options.
    shape: str = Field(default="circle", max_length=50, pattern=r"^[A-Za-z0-9_-]+$")

    @model_validator(mode="after")
    def require_title_or_industry(self) -> "SearchRequest":
        # Requirement: at least one of job_title or industry must be provided.
        if not (self.job_title and self.job_title.strip()) and not (
            self.industry and self.industry.strip()
        ):
            raise ValueError("Provide at least one of 'job_title' or 'industry'.")
        return self


class WordCloudWord(BaseModel):
    skill: str
    count: int      # document frequency: how many postings mention this skill
    weight: int     # sqrt-scaled 1..100, drives font size in the cloud


class WordCloudResponse(BaseModel):
    role: str                 # the matched role the cloud was built from
    shape: str                # echoes the requested shape
    posting_count: int        # postings the cloud was computed over
    words: list[WordCloudWord]


# --------------------------------------------------------------------------
# Auth (scaffold - endpoints return 501 until the auth milestone)
# --------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=16)  # full rules in services/security.py
    password: str = Field(min_length=1)                 # never allow empty (requirement)
    email: str | None = None
    name: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    user_id: int
    username: str
    name: str | None = None
    target_role: str | None = None
    target_location: str | None = None

    model_config = {"from_attributes": True}  # lets us return ORM User directly


# --------------------------------------------------------------------------
# Game (scaffold)
# --------------------------------------------------------------------------

class AnswerOptionOut(BaseModel):
    """An option as sent to the player - deliberately NO is_correct field."""
    option_id: int
    option_text: str


class QuestionOut(BaseModel):
    question_id: int
    question_text: str
    points: int
    options: list[AnswerOptionOut]


class GameQuestions(BaseModel):
    skill: str
    difficulty: str            # "easy" | "medium" | "hard" (derived from salary)
    questions: list[QuestionOut]


class SubmittedAnswer(BaseModel):
    question_id: int
    option_id: int


class GameSubmission(BaseModel):
    answers: list[SubmittedAnswer]
    desired_salary: int | None = Field(default=None, ge=0)


class GameResult(BaseModel):
    skill: str
    score: int
    max_score: int
    correct_count: int
    total_questions: int


# --------------------------------------------------------------------------
# Roadmap (scaffold)
# --------------------------------------------------------------------------

class RoadmapCreate(BaseModel):
    role_name: str = Field(min_length=1, max_length=100)


class RoadmapStepOut(BaseModel):
    step_id: int
    skill: str
    step_order: int
    status: str

    model_config = {"from_attributes": True}


class RoadmapOut(BaseModel):
    roadmap_id: int
    role: str
    created_date: object  # datetime; keep loose until implementation
    steps: list[RoadmapStepOut]


class StepStatusUpdate(BaseModel):
    status: str = Field(pattern="^(not_started|in_progress|completed)$")


# --------------------------------------------------------------------------
# History (scaffold)
# --------------------------------------------------------------------------

class LastGame(BaseModel):
    skill: str
    score: int
    max_score: int
    date_taken: object  # datetime


class RecentSearch(BaseModel):
    search_id: int
    job_title: str | None
    industry: str | None
    location: str | None
    word_count: int | None
    shape: str | None
    created_at: object  # datetime

    model_config = {"from_attributes": True}


class RecentActivity(BaseModel):
    last_game: LastGame | None
    recent_searches: list[RecentSearch]
