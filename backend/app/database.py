"""Database engine, session factory, and declarative base."""
from collections.abc import Generator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# check_same_thread is a SQLite-specific flag needed for FastAPI's threaded server.
connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args)

if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _record):
        """Harden SQLite per-connection.

        - foreign_keys=ON: SQLite does NOT enforce FK constraints by default;
          without this, orphaned rows (e.g. JobSkill pointing at a deleted
          posting) are silently allowed.
        - journal_mode=WAL: readers don't block the writer - better behavior
          for concurrent API requests.
        """
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def initialize_database(bind=engine) -> None:
    """Create tables and apply the small SQLite compatibility upgrades.

    The capstone intentionally does not use Alembic, but existing teammate
    databases still need to survive additive schema changes.
    """
    Base.metadata.create_all(bind=bind)
    if bind.dialect.name != "sqlite":
        return

    with bind.begin() as connection:
        inspector = inspect(connection)
        attempt_columns = {
            column["name"] for column in inspector.get_columns("game_attempts")
        }
        if "difficulty" not in attempt_columns:
            connection.execute(
                text("ALTER TABLE game_attempts ADD COLUMN difficulty VARCHAR(10)")
            )

        # Older builds allowed multiple roadmaps per user. Keep the newest row
        # before adding the one-roadmap-per-user database invariant.
        roadmap_rows = connection.execute(
            text(
                """
                SELECT roadmap_id, user_id
                FROM roadmaps
                ORDER BY user_id, created_date DESC, roadmap_id DESC
                """
            )
        ).all()
        seen_users: set[int] = set()
        for roadmap_id, user_id in roadmap_rows:
            if user_id not in seen_users:
                seen_users.add(user_id)
                continue
            connection.execute(
                text("DELETE FROM roadmap_steps WHERE roadmap_id = :roadmap_id"),
                {"roadmap_id": roadmap_id},
            )
            connection.execute(
                text("DELETE FROM roadmaps WHERE roadmap_id = :roadmap_id"),
                {"roadmap_id": roadmap_id},
            )

        connection.execute(text("DROP INDEX IF EXISTS ix_roadmaps_user_id"))
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_roadmaps_user_id "
                "ON roadmaps (user_id)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_quiz_sessions_created_at "
                "ON quiz_sessions (created_at)"
            )
        )
        # Replace the standalone difficulty index with the composite bank index
        # (skill_id, difficulty) that the game's question lookup filters on.
        connection.execute(text("DROP INDEX IF EXISTS ix_questions_difficulty"))
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_questions_skill_difficulty "
                "ON questions (skill_id, difficulty)"
            )
        )


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
