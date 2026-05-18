from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/marketing_content"
    database_url_sync: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/marketing_content"

    # GCS
    gcs_project_id: str = "your-gcp-project-id"
    gcs_bucket_name: str = "marketing-content-media"
    gcs_presigned_url_expiry_seconds: int = 3600
    # Set to http://localhost:4443 when using fake-gcs-server locally.
    # docker-compose sets this automatically inside the backend container.
    storage_emulator_host: str = ""

    # Pub/Sub
    pubsub_topic: str = "media-uploaded"
    # Shared secret added as ?token= to the Pub/Sub push subscription URL
    pubsub_webhook_token: str = "change-me-in-production"

    # LLM provider — "claude" | "gemini"
    llm_provider: str = "gemini"

    # Anthropic (used when llm_provider=claude)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-7"

    # Google Gemini (used when llm_provider=gemini)
    # Get a free key at https://aistudio.google.com/apikey
    # On Cloud Run with llm_provider=gemini you can leave this empty and
    # use Application Default Credentials instead (no key file needed).
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # Whisper
    whisper_model_size: str = "base"  # tiny | base | small | medium | large

    # App
    app_env: str = "development"
    secret_key: str = "change-me-in-production"
    allowed_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
