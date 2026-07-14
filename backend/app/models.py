"""SQLAlchemy ORM models for JobHopper.

Mirrors the team ERD (erd_jobhopper.drawio): User, Search, Role, JobPosting,
Skill, JobSkill, RoleSkill, Question, AnswerOption, GameAttempt, Roadmap,
RoadmapStep.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    username: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    target_role: Mapped[str | None] = mapped_column(String(100))
    target_location: Mapped[str | None] = mapped_column(String(100))

    searches: Mapped[list["Search"]] = relationship(back_populates="user")
    roadmaps: Mapped[list["Roadmap"]] = relationship(back_populates="user")
    game_attempts: Mapped[list["GameAttempt"]] = relationship(back_populates="user")


class Search(Base):
    __tablename__ = "searches"

    search_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), index=True)
    job_title: Mapped[str | None] = mapped_column(String(150))
    industry: Mapped[str | None] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(100))
    min_salary: Mapped[int | None] = mapped_column(Integer)
    word_count: Mapped[int | None] = mapped_column(Integer)
    shape: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="searches")


class Role(Base):
    __tablename__ = "roles"

    role_id: Mapped[int] = mapped_column(primary_key=True)
    role_name: Mapped[str] = mapped_column(String(100), unique=True)

    job_postings: Mapped[list["JobPosting"]] = relationship(back_populates="role")
    role_skills: Mapped[list["RoleSkill"]] = relationship(back_populates="role")
    roadmaps: Mapped[list["Roadmap"]] = relationship(back_populates="role")


class JobPosting(Base):
    __tablename__ = "job_postings"

    job_id: Mapped[int] = mapped_column(primary_key=True)
    # Provider's job id (JSearch job_id) - the dedup key that makes ingest
    # idempotent (review #1). Unique index rejects re-inserts.
    external_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.role_id"), index=True)
    title: Mapped[str | None] = mapped_column(String(150))
    company_name: Mapped[str | None] = mapped_column(String(150))
    location: Mapped[str | None] = mapped_column(String(100))
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    date_posted: Mapped[datetime | None] = mapped_column(DateTime)
    source_url: Mapped[str | None] = mapped_column(String(500))

    role: Mapped["Role"] = relationship(back_populates="job_postings")
    job_skills: Mapped[list["JobSkill"]] = relationship(back_populates="job_posting")


class Skill(Base):
    __tablename__ = "skills"

    skill_id: Mapped[int] = mapped_column(primary_key=True)
    skill_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    category: Mapped[str | None] = mapped_column(String(100))

    job_skills: Mapped[list["JobSkill"]] = relationship(back_populates="skill")
    role_skills: Mapped[list["RoleSkill"]] = relationship(back_populates="skill")
    questions: Mapped[list["Question"]] = relationship(back_populates="skill")
    game_attempts: Mapped[list["GameAttempt"]] = relationship(back_populates="skill")
    roadmap_steps: Mapped[list["RoadmapStep"]] = relationship(back_populates="skill")


class JobSkill(Base):
    """Junction: which skills appear in which postings, and how often."""

    __tablename__ = "job_skills"

    job_id: Mapped[int] = mapped_column(ForeignKey("job_postings.job_id"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.skill_id"), primary_key=True)
    frequency: Mapped[int] = mapped_column(Integer, default=1)

    job_posting: Mapped["JobPosting"] = relationship(back_populates="job_skills")
    skill: Mapped["Skill"] = relationship(back_populates="job_skills")


class RoleSkill(Base):
    """Junction: demand for a skill within a role."""

    __tablename__ = "role_skills"

    role_id: Mapped[int] = mapped_column(ForeignKey("roles.role_id"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.skill_id"), primary_key=True)
    demand_score: Mapped[float | None] = mapped_column()

    role: Mapped["Role"] = relationship(back_populates="role_skills")
    skill: Mapped["Skill"] = relationship(back_populates="role_skills")


class Question(Base):
    __tablename__ = "questions"
    # A quiz pulls its questions from one (skill_id, difficulty) bank, so the
    # hot lookup filters on both columns. A composite index serves that query
    # directly (and covers skill_id-only lookups via its leftmost prefix).
    __table_args__ = (Index("ix_questions_skill_difficulty", "skill_id", "difficulty"),)

    question_id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.skill_id"))
    difficulty: Mapped[str] = mapped_column(String(10))  # "easy" | "medium" | "hard"
    question_text: Mapped[str] = mapped_column(Text)

    skill: Mapped["Skill"] = relationship(back_populates="questions")
    options: Mapped[list["AnswerOption"]] = relationship(back_populates="question")


class AnswerOption(Base):
    __tablename__ = "answer_options"

    option_id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.question_id"), index=True)
    option_text: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)

    question: Mapped["Question"] = relationship(back_populates="options")


class GameAttempt(Base):
    __tablename__ = "game_attempts"

    attempt_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.skill_id"), index=True)
    difficulty: Mapped[str | None] = mapped_column(String(10))
    score: Mapped[int] = mapped_column(Integer, default=0)
    max_score: Mapped[int] = mapped_column(Integer, default=0)
    date_taken: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="game_attempts")
    skill: Mapped["Skill"] = relationship(back_populates="game_attempts")


class QuizSession(Base):
    """A served quiz: which questions went out, to whom, at what difficulty.

    Binds a submission to exactly the questions that were served, blocks
    replaying a completed quiz, and lets consecutive quizzes for the same
    user/skill/difficulty avoid repeating questions.
    """

    __tablename__ = "quiz_sessions"

    session_id: Mapped[int] = mapped_column(primary_key=True)
    # Null for anonymous players.
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.skill_id"), index=True)
    difficulty: Mapped[str] = mapped_column(String(10))
    question_ids: Mapped[str] = mapped_column(Text)  # JSON-encoded list of ids
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )


class Roadmap(Base):
    __tablename__ = "roadmaps"
    __table_args__ = (Index("uq_roadmaps_user_id", "user_id", unique=True),)

    roadmap_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.role_id"))
    created_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="roadmaps")
    role: Mapped["Role"] = relationship(back_populates="roadmaps")
    steps: Mapped[list["RoadmapStep"]] = relationship(back_populates="roadmap")


class RoadmapStep(Base):
    __tablename__ = "roadmap_steps"

    step_id: Mapped[int] = mapped_column(primary_key=True)
    roadmap_id: Mapped[int] = mapped_column(ForeignKey("roadmaps.roadmap_id"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.skill_id"))
    step_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="not_started")

    roadmap: Mapped["Roadmap"] = relationship(back_populates="steps")
    skill: Mapped["Skill"] = relationship(back_populates="roadmap_steps")
