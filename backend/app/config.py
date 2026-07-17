"""Application settings loaded from environment / .env file."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./jobhopper.db"
    secret_key: str = "change-me-to-a-long-random-string"

    _DEFAULT_SECRET = "change-me-to-a-long-random-string"

    @property
    def secret_is_default(self) -> bool:
        """True when tokens should use the per-process development secret."""
        return self.secret_key == self._DEFAULT_SECRET
    frontend_origins: str = "http://localhost:5500,http://127.0.0.1:5500"

    # JSearch (RapidAPI) - used to ingest real job postings into the seed DB.
    rapidapi_key: str = ""
    rapidapi_host: str = "jsearch.p.rapidapi.com"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]


settings = Settings()
