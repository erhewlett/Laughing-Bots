"""Database initialization and compatibility-upgrade tests."""
from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app import models  # noqa: F401 - registers all tables with Base.metadata
from app.database import initialize_database


def test_initialize_database_upgrades_existing_sqlite_schema(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE game_attempts (
                    attempt_id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    skill_id INTEGER NOT NULL,
                    score INTEGER NOT NULL,
                    max_score INTEGER NOT NULL,
                    date_taken DATETIME
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE roadmaps (
                    roadmap_id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    role_id INTEGER,
                    created_date DATETIME
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE roadmap_steps (
                    step_id INTEGER PRIMARY KEY,
                    roadmap_id INTEGER NOT NULL,
                    skill_id INTEGER NOT NULL,
                    step_order INTEGER NOT NULL,
                    status VARCHAR(20) NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                "INSERT INTO roadmaps VALUES "
                "(1, 7, NULL, '2026-01-01'), (2, 7, NULL, '2026-02-01')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO roadmap_steps VALUES "
                "(1, 1, 10, 1, 'not_started'), "
                "(2, 2, 11, 1, 'not_started')"
            )
        )

    initialize_database(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("game_attempts")}
    assert "difficulty" in columns
    with engine.connect() as connection:
        assert connection.execute(text("SELECT roadmap_id FROM roadmaps")).scalars().all() == [2]
        assert connection.execute(text("SELECT roadmap_id FROM roadmap_steps")).scalars().all() == [2]

    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO roadmaps "
                    "(roadmap_id, user_id, role_id, created_date) "
                    "VALUES (3, 7, NULL, '2026-03-01')"
                )
            )
    except IntegrityError:
        pass
    else:
        raise AssertionError("roadmaps.user_id unique index was not created")
