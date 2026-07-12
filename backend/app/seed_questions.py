"""Load the Q&A question bank into the DB.

Run from the backend/ directory (no API key or network needed):

    python -m app.seed_questions

Reads app/seed_data/questions_seed.json (Angel's content). Idempotent: for each
(skill, difficulty) bank present in the fixture, existing questions for that
bank are deleted and re-inserted, so edits to the fixture take effect and
re-running never duplicates. Skills are matched/created by name.
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import delete, select

from app.database import Base, SessionLocal, engine
from app import models
from app.services.ingest import _get_or_create_skill

FIXTURE = Path(__file__).parent / "seed_data" / "questions_seed.json"


def seed_questions() -> None:
    Base.metadata.create_all(bind=engine)
    items = json.loads(FIXTURE.read_text())["questions"]

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
            if q_ids:
                # delete options first (FK enforcement is on), then questions
                db.execute(
                    delete(models.AnswerOption).where(
                        models.AnswerOption.question_id.in_(q_ids)
                    )
                )
                db.execute(
                    delete(models.Question).where(
                        models.Question.question_id.in_(q_ids)
                    )
                )
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
        print(f"Seeded {len(items)} questions across {len(banks)} banks.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_questions()
