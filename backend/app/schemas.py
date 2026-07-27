"""Pydantic request/response models for the API."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, get_args

from pydantic import BaseModel, Field, field_validator, model_validator

from app.services.security import (
    PASSWORD_MAX,
    PASSWORD_MAX_BYTES,
    PASSWORD_MIN,
    USERNAME_MAX,
    USERNAME_MIN,
)

# Largest value SQLite stores in an INTEGER column. Anything above this reaches
# the driver and raises OverflowError, which surfaces as a 500 rather than a
# validation error, so bound every client-supplied integer by it.
MAX_DB_INT = 2**63 - 1

# Matches the users.email column width; SQLite does not enforce VARCHAR limits,
# so without this a 10,000-character email was accepted and stored.
EMAIL_MAX = 255


class SearchRequest(BaseModel):
    """User's job-search parameters for generating a word cloud."""

    job_title: str | None = Field(default=None, max_length=150)
    industry: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=100)
    # le= keeps oversized values inside SQLite's signed-64-bit range; without
    # it the driver raised OverflowError and FastAPI returned a 500.
    min_salary: int | None = Field(default=None, ge=0, le=MAX_DB_INT)
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
    # True when this skill has quiz questions, i.e. clicking it can start a
    # game. Lets the cloud page decide what is clickable straight from this
    # response instead of making a second call to GET /game/skills.
    playable: bool = False


class WordCloudResponse(BaseModel):
    role: str                 # the matched role the cloud was built from
    shape: str                # echoes the requested shape
    word_count: int           # echoes the requested max word count (drives rendering)
    # Postings matching the search. When min_salary is set this counts only
    # postings whose salary is known to clear it; postings with no salary data
    # still feed the cloud but are not reported as confirmed matches.
    posting_count: int
    words: list[WordCloudWord]
    # The requesting user's username. This route already requires a logged-in
    # user, so echoing it costs nothing and lets the cloud page render its
    # title without separately awaiting GET /auth/me first.
    username: str = ""


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
    email: str | None = Field(default=None, max_length=EMAIL_MAX)
    name: str | None = Field(default=None, max_length=100)

    @field_validator("email")
    @classmethod
    def blank_email_is_none(cls, v: str | None) -> str | None:
        """Treat "" / whitespace as "no email supplied".

        The email column is unique, so an empty string inserted for the first
        user made every later blank-email registration collide with it and
        fail as "already in use".
        """
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("password")
    @classmethod
    def password_within_bcrypt_limit(cls, v: str) -> str:
        # A 20-char password can exceed bcrypt's 72-byte limit in UTF-8; reject
        # rather than truncate (which would collapse distinct passwords).
        if len(v.encode("utf-8")) > PASSWORD_MAX_BYTES:
            raise ValueError("Password is too long.")
        return v


# A sanity bound on login fields. Deliberately far above the real 4-16 and
# 8-20 policies: the point is to stop an unbounded string reaching bcrypt, not
# to enforce the policy here. Anything a real user could type still returns 401
# rather than 422, so the policy stays unleaked.
LOGIN_FIELD_MAX = 1024


class LoginRequest(BaseModel):
    # Login only checks presence (requirement: username/password not empty).
    # The 8-20 policy lives on register, not here, so a wrong-length attempt
    # returns 401, not 422, and does not leak the policy.
    username: str = Field(min_length=1, max_length=LOGIN_FIELD_MAX)
    password: str = Field(min_length=1, max_length=LOGIN_FIELD_MAX)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterResponse(BaseModel):
    """Register returns the new user AND a usable token.

    Registering then immediately logging in was two calls with a failure window
    between them: the account existed but the caller had no token, so the next
    page bounced to sign-in. Returning the token makes the signed-in path a
    single request. All the original UserOut fields are still present, so
    callers that only read user data are unaffected.
    """

    user_id: int
    username: str
    name: str | None = None
    target_role: str | None = None
    target_location: str | None = None
    access_token: str
    token_type: str = "bearer"

    model_config = {"from_attributes": True}


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

# The difficulties a quiz can actually be served at, easiest first. Anything
# else sitting in the questions table is bad data (a seed typo, say) and must
# not be treated as playable. Derived from the Literal so the routes that
# filter on it and the schema that validates it cannot drift apart.
DIFFICULTY_VALUES: tuple[str, ...] = get_args(Difficulty)


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
    # Bounded so oversized ids fail validation instead of overflowing SQLite.
    question_id: int = Field(ge=1, le=MAX_DB_INT)
    option_id: int = Field(ge=1, le=MAX_DB_INT)


class GameSubmission(BaseModel):
    quiz_id: int = Field(ge=1, le=MAX_DB_INT)
    difficulty: Difficulty
    # A quiz is 10 questions. submit_game already rejects any answer set that
    # is not exactly the questions it served, but that check runs after the
    # whole list is parsed, so bound it here too. Generous on purpose.
    answers: list[SubmittedAnswer] = Field(max_length=100)
    # How long the player took, sent by the quiz page's timer. Optional so an
    # older client that omits it still submits successfully; when present it is
    # persisted so the history and rank pages can show finish times.
    elapsed_seconds: int | None = Field(default=None, ge=0, le=86_400)
    # Set when the clock ran out mid-quiz. Relaxes the "answer exactly the
    # questions served" rule to "answer some of them", and everything left
    # unanswered is graded wrong. max_score stays the full quiz either way, so
    # running out of time can never score better than answering every question,
    # and a partial quiz can never reach mastery.
    timed_out: bool = False


class LiveAnswer(BaseModel):
    """One answer graded the moment the player commits to it."""

    quiz_id: int = Field(ge=1, le=MAX_DB_INT)
    question_id: int = Field(ge=1, le=MAX_DB_INT)
    option_id: int = Field(ge=1, le=MAX_DB_INT)


class LiveAnswerResult(BaseModel):
    """Grade for one answer, plus the score so far.

    Returned by POST /game/{skill}/answer so the quiz page can mark the pick
    right or wrong and move its points counter as the player goes, instead of
    waiting for the whole quiz to be submitted.
    """

    question_id: int
    is_correct: bool
    # Which option was the right one. Safe to send only because the player's
    # pick is already recorded and cannot be changed, so this cannot be used to
    # answer the question they just answered.
    correct_option_id: int | None = None
    # True when this question had already been graded and the stored result is
    # being replayed. The pick does not change; a second try on the same
    # question cannot be used to hunt for the right option.
    already_answered: bool = False
    answered_count: int
    total_questions: int
    correct_count: int
    # Running 0..10000 score, same formula the final result uses, so the number
    # the player watches climbs to exactly the score they finish with.
    score_normalized: int
    # True once every question in the quiz has been answered, meaning the page
    # can go straight to submitting.
    quiz_complete: bool


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
    # The 0..10000 display score. The quiz page computes this same number
    # client-side; returning it from the server means a history or rank page
    # reading stored attempts shows the same figure the player saw.
    score_normalized: int = 0
    elapsed_seconds: int | None = None
    # False when the quiz was played without a token, meaning it was graded but
    # NOT saved to history. Anonymous play is supported on purpose, so this is
    # not an error - but a caller that forgot its Authorization header used to
    # get a clean 200 and silently record nothing. This makes that visible.
    recorded: bool = False


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
    # Identity of the requesting user. This route already requires a token, so
    # including it lets the user info page skip its separate GET /auth/me.
    username: str = ""
    name: str | None = None
    email: str | None = None


# --------------------------------------------------------------------------
# Game history (powers a results/history page and a rank system)
# --------------------------------------------------------------------------
class GameHistoryItem(BaseModel):
    attempt_id: int
    skill: str
    difficulty: str | None
    score: int
    max_score: int
    score_normalized: int       # 0..10000, matches what the player saw
    percentage: int             # 0..100, convenience for display
    mastered: bool              # perfect score on a full hard quiz
    elapsed_seconds: int | None
    date_taken: datetime


class SkillBest(BaseModel):
    """Best result a player has recorded for one skill/difficulty pair."""

    skill: str
    difficulty: str | None
    best_score: int
    max_score: int
    attempts: int


class GameHistory(BaseModel):
    total_attempts: int
    # Sum of correct answers over all attempts, and of questions asked. Enough
    # to drive an overall accuracy figure or a rank threshold.
    total_correct: int
    total_questions: int
    mastered_skills: list[str]  # skills with a perfect full hard quiz
    bests: list[SkillBest]
    attempts: list[GameHistoryItem]


class LocationOut(BaseModel):
    """A location that actually has fresh postings, for search dropdowns."""

    location: str
    posting_count: int
