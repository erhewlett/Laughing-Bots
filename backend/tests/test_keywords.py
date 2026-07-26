"""Keyword extraction tests.

Covers the "Go" false-positive class: a bare "go" alias matched the ordinary
English verb, which put a phantom top skill in the live-ingest word cloud with
no question bank behind it.
"""
from __future__ import annotations

import pytest

from app.services.keywords import extract_skills


def _go(text: str) -> int:
    return extract_skills({"job_description": text}).get("Go", 0)


@pytest.mark.parametrize(
    "text",
    [
        "Ready to go the extra mile.",
        "Our go-to-market strategy needs a go-getter.",
        "Go above and beyond for our customers",
        "things are going well",
        "a go/no-go decision",
        "Google Cloud and Django experience",
    ],
)
def test_ordinary_english_go_is_not_the_language(text):
    assert _go(text) == 0


@pytest.mark.parametrize(
    "text",
    [
        "Strong Go developer needed",
        "Hiring Go developers",
        "We use Golang in production",
        "Go programming experience required",
        "Senior Go Engineer",
        "Familiar with goroutines and channels",
        "go modules and testing",
        "Go language experience",
    ],
)
def test_real_go_mentions_still_match(text):
    assert _go(text) >= 1


def test_other_skills_are_unaffected():
    found = extract_skills(
        {"job_description": "Python, Java, JavaScript, C++17, PostgreSQL, CI/CD"}
    )
    assert found == {
        "Python": 1,
        "Java": 1,
        "JavaScript": 1,
        "C++": 1,
        "PostgreSQL": 1,
        "CI/CD": 1,
    }
