"""Seed the database with roles, skills, sample postings, and quiz questions.

Run from the backend/ directory:  python -m app.seed

This is a stub for the skeleton. Fill in real seed data (curated postings per
role, skill lists, and Q&A questions) as those features come online.
"""
from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(models.Role).count() > 0:
            print("Data already present; skipping seed.")
            return

        # TODO: add roles, skills, role_skills, job_postings, job_skills,
        # questions, and answer_options here.
        print("Seed stub ran. No data defined yet.")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
