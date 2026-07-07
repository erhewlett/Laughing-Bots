"""Extract tool/skill keywords from job postings and count their frequency.

Strategy: match a curated skill vocabulary against the posting's text
(structured technology fields + qualifications + description). This is more
reliable than raw tokenizing because job descriptions are noisy. Stop words are
removed as required, but the vocabulary match already excludes them.
"""
from __future__ import annotations

import re

# Required by spec: strip common stop words before keyword extraction.
STOP_WORDS = {
    "the", "and", "for", "with", "a", "an", "to", "of", "in", "on", "or",
    "is", "are", "as", "at", "by", "be", "we", "you", "our", "your",
}

# Curated IT skill vocabulary: canonical name -> regex-safe aliases to match.
# Extend this as you add more target roles.
SKILL_ALIASES: dict[str, list[str]] = {
    "Python": ["python"],
    "Java": ["java"],
    "JavaScript": ["javascript"],
    "TypeScript": ["typescript"],
    "C++": [r"c\+\+"],
    "C#": [r"c#"],
    "Go": ["golang"],
    "SQL": ["sql"],
    "PostgreSQL": ["postgresql", "postgres"],
    "MySQL": ["mysql"],
    "MongoDB": ["mongodb", "mongo"],
    "AWS": ["aws", "amazon web services"],
    "Azure": ["azure"],
    "GCP": ["gcp", "google cloud"],
    "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "k8s"],
    "Terraform": ["terraform"],
    "Linux": ["linux"],
    "Git": ["git"],
    "React": ["react", r"react\.js", "reactjs"],
    "Node.js": [r"node\.js", "nodejs"],
    "REST": ["restful", "rest api"],
    "GraphQL": ["graphql"],
    "CI/CD": ["ci/cd", "cicd"],
    "Machine Learning": ["machine learning"],
    # NOTE: no bare "security" - it matched phrases like "security clearance"
    # and made Cybersecurity dominate every cloud (review #7).
    "Cybersecurity": [
        "cybersecurity",
        "cyber security",
        "infosec",
        "information security",
        "cloud security",
        "network security",
        "application security",
    ],
    "Networking": ["networking", "tcp/ip"],
    "Agile": ["agile", "scrum"],
    "HTML": ["html"],
    "CSS": ["css"],
    "FastAPI": ["fastapi"],
    "Flask": ["flask"],
    "Django": ["django"],
}

# Pre-compile one word-boundary pattern per canonical skill.
_PATTERNS: dict[str, re.Pattern] = {
    skill: re.compile(
        r"(?<![\w+#])(?:" + "|".join(aliases) + r")(?![\w+#])", re.IGNORECASE
    )
    for skill, aliases in SKILL_ALIASES.items()
}

_STOP_WORD_RE = re.compile(
    r"\b(?:" + "|".join(sorted(STOP_WORDS)) + r")\b", re.IGNORECASE
)


def remove_stop_words(text: str) -> str:
    """Strip common stop words from job text before keyword extraction
    (explicit functional requirement). Word boundaries keep multi-word skill
    aliases like "machine learning" intact."""
    return _STOP_WORD_RE.sub(" ", text)


def _gather_text(job: dict) -> str:
    """Collect the searchable text from a JSearch job object."""
    parts: list[str] = [
        job.get("job_title") or "",
        job.get("job_description") or "",
    ]
    parts += job.get("required_technologies") or []
    parts += job.get("preferred_technologies") or []
    highlights = job.get("job_highlights") or {}
    for key in ("Qualifications", "Responsibilities"):
        parts += highlights.get(key) or []
    return remove_stop_words("\n".join(parts))


def extract_skills(job: dict) -> dict[str, int]:
    """Return {canonical_skill_name: frequency} for one job posting."""
    text = _gather_text(job)
    counts: dict[str, int] = {}
    for skill, pattern in _PATTERNS.items():
        n = len(pattern.findall(text))
        if n:
            counts[skill] = n
    return counts
