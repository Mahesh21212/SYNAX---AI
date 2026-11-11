"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Every value comes from the environment (or .env)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- OpenRouter -------------------------------------------------------
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_site_url: str = "http://localhost:3000"
    openrouter_site_name: str = "SYNAX AI"

    # --- Agent council models --------------------------------------------
    synax_planner_model: str = "anthropic/claude-3.5-sonnet"
    synax_researcher_model: str = "perplexity/llama-3.1-sonar-large-128k-online"
    synax_analyst_model: str = "anthropic/claude-3.5-sonnet"
    synax_writer_model: str = "anthropic/claude-3.5-sonnet"
    synax_critic_model: str = "openai/gpt-4o-mini"
    synax_default_model: str = "anthropic/claude-3.5-sonnet"

    # --- Database ---------------------------------------------------------
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "synax"

    # --- Server -----------------------------------------------------------
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- Uploads ----------------------------------------------------------
    max_upload_mb: int = 20
    upload_dir: str = "./uploads"

    # --- Auth (optional) --------------------------------------------------
    synax_api_token: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def openrouter_configured(self) -> bool:
        key = self.openrouter_api_key.strip()
        return bool(key) and not key.startswith("sk-or-v1-your-key")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
