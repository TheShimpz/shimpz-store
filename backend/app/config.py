from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed config from the project's .env (gitignored). Secrets are NEVER literals in code."""

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    database_url: str
    secret_key: str


settings = Settings()
