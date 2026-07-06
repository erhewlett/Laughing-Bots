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
    shape: str = Field(default="circle", max_length=50)

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
