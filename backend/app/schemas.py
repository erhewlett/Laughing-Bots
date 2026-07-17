"""Pydantic request/response models for the API."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.services.security import (
    PASSWORD_MAX,
    PASSWORD_MAX_BYTES,
    PASSWORD_MIN,
    USERNAME_MAX,
    USERNAME_MIN,
)


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


class RoleOut(BaseModel):
    role_id: int
    role_name: str
    posting_count: int


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    # 4-16 chars, letters and digits only (matches the frontend form and the
    # rule in services/security.py). validate_username re-checks on the server.
    username: str = Field(
        min_length=USERNAME_MIN, max_length=USERNAME_MAX, pattern=r"^[A-Za-z0-9]+$"
    )
    password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)
    email: str | None = None
    name: str | None = Field(default=None, max_length=100)
    target_role: str | None = Field(default=None, max_length=100)
    target_industry: str | None = Field(default=None, max_length=100)
    target_location: str | None = Field(default=None, max_length=100)
    target_min_salary: int | None = Field(

        default=None,
        ge=30000,
        le=500000,
        multiple_of=10000
    )

    target_max_salary: int | None = Field(

        default=None,
        ge=30000,
        le=500000,
        multiple_of=10000

    )
    
    @field_validator("password")
    @classmethod
    def password_within_bcrypt_limit(cls, v: str) -> str:
        # A 20-char password can exceed bcrypt's 72-byte limit in UTF-8; reject
        # rather than truncate (which would collapse distinct passwords).
        if len(v.encode("utf-8")) > PASSWORD_MAX_BYTES:
            raise ValueError("Password is too long.")
        return v
    
    def password_no_spaces(cls, v: str) -> str:
        if any(char.isspace() for char in v):
            raise ValueError("Password cannot contain spaces.")
        return v
    
    @model_validator(mode="after")

    def validate_salary_range(self):

        if (
            self.target_min_salary is not None
            and self.target_max_salary is not None
            and self.target_max_salary < self.target_min_salary
        ):

            raise ValueError(
                "Maximum salary cannot be lower than minimum salary."
            )

        return self


class LoginRequest(BaseModel):
    # Login only checks presence (requirement: username/password not empty).
    # The 8-20 policy lives on register, not here, so a wrong-length attempt
    # returns 401, not 422, and does not leak the policy.
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
# Game
# --------------------------------------------------------------------------

Difficulty = Literal["easy", "medium", "hard"]


class SkillQuizzes(BaseModel):
    """A skill that has quiz questions, and which difficulties are available."""
    skill: str
    difficulties: list[Difficulty]


class AnswerOptionOut(BaseModel):
    """An option as sent to the player - deliberately NO is_correct field."""
    option_id: int
    option_text: str


class QuestionOut(BaseModel):
    question_id: int
    question_text: str
    options: list[AnswerOptionOut]


class GameQuestions(BaseModel):
    quiz_id: int               # echo back on submit; binds the submission
    skill: str
    difficulty: Difficulty
    questions: list[QuestionOut]


class SubmittedAnswer(BaseModel):
    question_id: int
    option_id: int


class GameSubmission(BaseModel):
    quiz_id: int
    difficulty: Difficulty
    answers: list[SubmittedAnswer]


class QuestionResult(BaseModel):
    question_id: int
    is_correct: bool


class GameResult(BaseModel):
    skill: str
    difficulty: Difficulty
    score: int              # number correct
    max_score: int          # number of questions (10 for a full quiz)
    correct_count: int
    total_questions: int
    mastered: bool          # perfect score on a hard quiz
    results: list[QuestionResult]


# --------------------------------------------------------------------------
# Roadmap
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
    created_date: datetime
    steps: list[RoadmapStepOut]


class StepStatusUpdate(BaseModel):
    status: str = Field(pattern="^(not_started|in_progress|completed)$")


# --------------------------------------------------------------------------
# History
# --------------------------------------------------------------------------

class LastGame(BaseModel):
    skill: str
    difficulty: str | None
    score: int
    max_score: int
    date_taken: datetime


class RecentSearch(BaseModel):
    search_id: int
    job_title: str | None
    industry: str | None
    location: str | None
    min_salary: int | None
    word_count: int | None
    shape: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RecentActivity(BaseModel):
    last_game: LastGame | None
    recent_searches: list[RecentSearch]
