"""Application settings loaded from environment / .env file."""
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Anchor .env to the backend package instead of the process CWD. A relative
# ".env" is resolved against wherever uvicorn was launched from, so starting
# the app from the repo root silently fell back to the placeholder secret and
# re-resolved the sqlite path to a brand new empty database.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    database_url: str = f"sqlite:///{_BACKEND_DIR / 'jobhopper.db'}"
    secret_key: str = "change-me-to-a-long-random-string"

    @field_validator("database_url")
    @classmethod
    def _anchor_relative_sqlite_path(cls, value: str) -> str:
        """Resolve a relative sqlite path against backend/ rather than the CWD.

        `.env` ships `sqlite:///./jobhopper.db`, which otherwise points at a
        different (empty) file depending on where the server was started from.
        """
        prefix = "sqlite:///"
        if not value.startswith(prefix):
            return value
        path = value[len(prefix):]
        # ":memory:" and absolute paths are already unambiguous.
        if not path or path.startswith(("/", ":")):
            return value
        return f"{prefix}{(_BACKEND_DIR / path).resolve()}"

    _DEFAULT_SECRET = "change-me-to-a-long-random-string"

    @property
    def secret_is_default(self) -> bool:
        """True when tokens should use the per-process development secret."""
        return self.secret_key == self._DEFAULT_SECRET
    frontend_origins: str = "http://localhost:5500,http://127.0.0.1:5500"

    # Load missing seed data on startup so a fresh clone (or a database left
    # behind by a fixture change) comes up usable. See app/autoseed.py.
    auto_seed: bool = True

    # JSearch (RapidAPI) - used to ingest real job postings into the seed DB.
    rapidapi_key: str = ""
    rapidapi_host: str = "jsearch.p.rapidapi.com"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]


settings = Settings()
