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


# --- structured technology fields --------------------------------------------
#
# required_technologies / preferred_technologies name one technology per entry,
# so a bare name there is unambiguous and must count, even where the same bare
# name is unsafe in prose.


@pytest.mark.parametrize("field", ["required_technologies", "preferred_technologies"])
def test_bare_go_in_a_technology_field_counts(field):
    """Previously dropped entirely, which undercounted Go on live ingest."""
    assert extract_skills({field: ["Go"]}).get("Go", 0) == 1


@pytest.mark.parametrize("field", ["required_technologies", "preferred_technologies"])
def test_bare_rest_in_a_technology_field_counts(field):
    """Same shape as Go: the aliases are "restful" and "rest apis", not "rest"."""
    assert extract_skills({field: ["REST"]}).get("REST", 0) == 1


def test_bare_go_in_prose_is_still_not_the_language():
    """The whole reason the bare alias was removed. Must stay fixed."""
    assert extract_skills(
        {
            "job_description": "Ready to go the extra mile",
            "required_technologies": ["Python"],
        }
    ).get("Go", 0) == 0


def test_technology_fields_and_prose_both_count():
    found = extract_skills(
        {
            "job_description": "We use Python and Docker daily",
            "required_technologies": ["Go", "Python"],
        }
    )
    assert found["Go"] == 1
    assert found["Python"] == 2      # one in prose, one in the technology list
    assert found["Docker"] == 1


def test_multi_word_skill_still_matches_in_a_technology_field():
    """Guards the escaping: a naive re.escape breaks the space handling."""
    assert extract_skills(
        {"required_technologies": ["Machine Learning"]}
    ).get("Machine Learning", 0) == 1


def test_versioned_entry_in_a_technology_field_still_matches():
    assert extract_skills({"required_technologies": ["Python 3.11"]}).get("Python", 0) == 1


def test_unknown_technology_entry_is_ignored():
    assert extract_skills({"required_technologies": ["Fortran"]}) == {}
