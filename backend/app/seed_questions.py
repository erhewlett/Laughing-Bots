"""Load the Q&A question bank into the DB.

Run from the backend/ directory (no API key or network needed):

    python -m app.seed_questions

Reads app/seed_data/questions_seed.json (Angel's content). Idempotent: for each
(skill, difficulty) bank present in the fixture, existing questions for that
bank are deleted and re-inserted, so edits to the fixture take effect and
re-running never duplicates. Skills are matched/created by name.

Banks missing from the fixture are left alone by default, so you can load a
trimmed fixture without wiping the rest of the bank. Pass prune=True to make
the database match the fixture exactly instead, deleting banks the fixture no
longer contains. Startup auto-seeding uses that, because it treats the fixture
as the whole truth (see app/autoseed.py).
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import delete, select

from app.database import SessionLocal, engine, initialize_database
from app import models
from app.services.ingest import _get_or_create_skill

FIXTURE = Path(__file__).parent / "seed_data" / "questions_seed.json"

VALID_DIFFICULTIES = {"easy", "medium", "hard"}


def _where(item: dict, i: int) -> str:
    """A human-locatable label for an entry, for validation errors.

    In a bank of hundreds, "question 487" is useless; the skill, difficulty,
    and a snippet of the text let the author find the row at a glance.
    """
    skill = item.get("skill", "?")
    difficulty = item.get("difficulty", "?")
    text = (item.get("question_text") or "").strip()
    snippet = text[:60] + "..." if len(text) > 60 else text
    return f"question {i} [{skill} / {difficulty}] {snippet!r}"


def validate_questions(items: list[dict]) -> None:
    """Reject a broken bank before touching the DB, naming the exact entry.

    Catches invalid difficulty, empty text, too few options, blank or
    duplicate option text, an answer set without exactly one correct option,
    and the same question repeated within a (skill, difficulty) bank.
    """
    seen: dict[tuple[str, str, str], int] = {}
    for i, item in enumerate(items):
        where = _where(item, i)
        if item.get("difficulty") not in VALID_DIFFICULTIES:
            raise ValueError(
                f"{where} has invalid difficulty {item.get('difficulty')!r}; "
                f"use one of {sorted(VALID_DIFFICULTIES)}."
            )
        text = (item.get("question_text") or "").strip()
        if not text:
            raise ValueError(f"{where} has empty question_text.")

        options = item.get("options") or []
        if len(options) < 2:
            raise ValueError(f"{where} needs at least 2 options.")
        option_texts = [(o.get("text") or "").strip() for o in options]
        if any(not t for t in option_texts):
            raise ValueError(f"{where} has an option with empty text.")
        if len({t.lower() for t in option_texts}) != len(option_texts):
            raise ValueError(f"{where} has duplicate option text.")
        correct_count = sum(1 for o in options if o.get("correct"))
        if correct_count != 1:
            raise ValueError(
                f"{where} must have exactly one correct option, "
                f"found {correct_count}."
            )

        key = (item["skill"].strip().lower(), item["difficulty"], text.lower())
        if key in seen:
            raise ValueError(f"{where} duplicates question {seen[key]} in the same bank.")
        seen[key] = i


def _delete_questions(db, q_ids) -> None:
    """Remove questions and their options (FK enforcement is on, options first)."""
    if not q_ids:
        return
    db.execute(
        delete(models.AnswerOption).where(models.AnswerOption.question_id.in_(q_ids))
    )
    db.execute(delete(models.Question).where(models.Question.question_id.in_(q_ids)))


def _prune_missing_banks(db, banks: set[tuple[int, str]]) -> int:
    """Delete questions whose bank is no longer in the fixture.

    Without this, dropping a skill from the fixture leaves its questions
    behind forever: the reload only clears banks it is about to rewrite, so
    /game/skills keeps advertising a quiz the fixture no longer defines.
    """
    stale = [
        q_id
        for q_id, skill_id, difficulty in db.execute(
            select(
                models.Question.question_id,
                models.Question.skill_id,
                models.Question.difficulty,
            )
        )
        if (skill_id, difficulty) not in banks
    ]
    _delete_questions(db, stale)
    return len(stale)


def seed_questions(prune: bool = False) -> None:
    initialize_database(engine)
    items = json.loads(FIXTURE.read_text())["questions"]

    # Preflight the whole fixture before touching the DB, so a bad entry is
    # fixed in the fixture rather than seeding a broken or ambiguous quiz.
    validate_questions(items)

    db = SessionLocal()
    try:
        skill_cache: dict[str, models.Skill] = {}
        banks: set[tuple[int, str]] = set()

        # Pass 1: resolve skills and clear each touched (skill, difficulty) bank.
        for item in items:
            skill = _get_or_create_skill(db, item["skill"], skill_cache)
            bank = (skill.skill_id, item["difficulty"])
            if bank in banks:
                continue
            banks.add(bank)
            q_ids = db.scalars(
                select(models.Question.question_id).where(
                    models.Question.skill_id == skill.skill_id,
                    models.Question.difficulty == item["difficulty"],
                )
            ).all()
            _delete_questions(db, q_ids)

        pruned = _prune_missing_banks(db, banks) if prune else 0
        db.flush()

        # Pass 2: insert the questions and their options.
        for item in items:
            skill = _get_or_create_skill(db, item["skill"], skill_cache)
            question = models.Question(
                skill_id=skill.skill_id,
                difficulty=item["difficulty"],
                question_text=item["question_text"],
            )
            db.add(question)
            db.flush()
            for opt in item["options"]:
                db.add(
                    models.AnswerOption(
                        question_id=question.question_id,
                        option_text=opt["text"],
                        is_correct=opt["correct"],
                    )
                )

        db.commit()
        pruned_note = f", pruned {pruned} from removed banks" if pruned else ""
        print(f"Seeded {len(items)} questions across {len(banks)} banks{pruned_note}.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_questions()
